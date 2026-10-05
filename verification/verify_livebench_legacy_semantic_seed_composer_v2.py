#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
INPUT_ROOT = ROOT / "verification_inputs"
UPSTREAM = pathlib.Path("/tmp/LiveBench/livebench/if_runner")
sys.path.insert(0, str(INPUT_ROOT))
sys.path.insert(0, str(UPSTREAM))

EXPECTED_BLOBS = {
    INPUT_ROOT / "canonical/runtime/livebench_legacy_visible_constraint_compiler_v1.py":
        "e986035ff68b53c0dc7a7eb478f6e3d8882214aa",
    INPUT_ROOT / "canonical/runtime/livebench_legacy_visible_constraint_compiler_v2.py":
        "0e7519f4f2b7d40084effc83a5bef814ee7fd487",
    INPUT_ROOT / "canonical/runtime/livebench_legacy_semantic_seed_composer_v2.py":
        "e5207007305c26e712d2608019988d409a63f2c9",
}


def git_blob(path: pathlib.Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


for path, expected in EXPECTED_BLOBS.items():
    got = git_blob(path)
    assert got == expected, (str(path), got, expected)

from canonical.runtime import livebench_legacy_semantic_seed_composer_v2 as composer
from instruction_following_eval import instructions_registry

BASE = "Explain the topic clearly."
DEFAULT_SEED = "The semantic answer remains intact and useful."

cases = [
    ("keywords:existence", {"keywords": ["alpha", "beta"]}, DEFAULT_SEED),
    ("keywords:frequency", {"keyword": "alpha", "frequency": 3, "relation": "at least"}, DEFAULT_SEED),
    ("keywords:forbidden_words", {"forbidden_words": ["alpha", "beta"]}, DEFAULT_SEED),
    ("keywords:letter_frequency", {"letter": "q", "let_frequency": 4, "let_relation": "at least"}, DEFAULT_SEED),
    ("length_constraints:number_paragraphs", {"num_paragraphs": 3}, "alpha\n***\nbeta\n***\ngamma"),
    ("length_constraints:number_words", {"num_words": 7, "relation": "at least"}, "one two three four five six seven"),
    (
        "length_constraints:nth_paragraph_first_word",
        {"num_paragraphs": 3, "nth_paragraph": 2, "first_word": "cedar"},
        "alpha content\n\ncedar content\n\nomega content",
    ),
    ("detectable_content:number_placeholders", {"num_placeholders": 3}, DEFAULT_SEED),
    ("detectable_content:postscript", {"postscript_marker": "P.S."}, DEFAULT_SEED),
    ("detectable_format:number_bullet_lists", {"num_bullets": 3}, DEFAULT_SEED),
    ("detectable_format:constrained_response", {}, "My answer is yes."),
    ("detectable_format:number_highlighted_sections", {"num_highlights": 3}, DEFAULT_SEED),
    ("detectable_format:multiple_sections", {"section_spliter": "Section", "num_sections": 3}, DEFAULT_SEED),
    ("detectable_format:json_format", {}, '{"answer":"cedar"}'),
    ("detectable_format:title", {}, DEFAULT_SEED),
    ("combination:two_responses", {}, "semantic alpha******semantic beta"),
    ("combination:repeat_prompt", {"prompt_to_repeat": BASE}, DEFAULT_SEED),
    ("startend:end_checker", {"end_phrase": "Any other questions?"}, DEFAULT_SEED),
    ("punctuation:no_comma", {}, DEFAULT_SEED),
    ("startend:quotation", {}, DEFAULT_SEED),
]

results = []
for iid, kwargs, seed in cases:
    cls = instructions_registry.INSTRUCTION_DICT[iid]
    inst = cls(iid)
    desc = inst.build_description(**kwargs)
    prompt = (BASE + " " + desc).strip()
    out = composer.compose(seed, prompt)
    response = out.get("response") or ""
    try:
        exact_pass = bool(inst.check_following(response))
        exact_error = None
    except Exception as exc:
        exact_pass = False
        exact_error = repr(exc)
    ok = (
        out.get("status") == "PASS_CANDIDATE_SEED_PRESERVED"
        and out.get("seed_verbatim_preserved") is True
        and seed in response
        and exact_pass
    )
    results.append({
        "kind": "single_family",
        "instruction_id": iid,
        "status": out.get("status"),
        "exact_checker_pass": exact_pass,
        "seed_preserved": seed in response,
        "ok": ok,
        "error": exact_error,
    })

# Joint constructive composition: exact upstream checkers must all pass together.
multi_specs = [
    ("keywords:existence", {"keywords": ["cedar", "basalt"]}),
    ("detectable_content:number_placeholders", {"num_placeholders": 2}),
    ("detectable_format:number_highlighted_sections", {"num_highlights": 2}),
    ("detectable_format:number_bullet_lists", {"num_bullets": 2}),
    ("detectable_format:title", {}),
    ("startend:end_checker", {"end_phrase": "Any other questions?"}),
    ("punctuation:no_comma", {}),
    ("startend:quotation", {}),
]
instances = []
descs = []
for iid, kwargs in multi_specs:
    inst = instructions_registry.INSTRUCTION_DICT[iid](iid)
    descs.append(inst.build_description(**kwargs))
    instances.append((iid, inst))
seed = "Cedar forests store carbon safely."
out = composer.compose(seed, BASE + " " + " ".join(descs))
response = out.get("response") or ""
joint_checks = {}
for iid, inst in instances:
    try:
        joint_checks[iid] = bool(inst.check_following(response))
    except Exception:
        joint_checks[iid] = False
joint_ok = (
    out.get("status") == "PASS_CANDIDATE_SEED_PRESERVED"
    and seed in response
    and all(joint_checks.values())
)
results.append({
    "kind": "interaction",
    "name": "eight_family_joint_constructive_composition",
    "status": out.get("status"),
    "seed_preserved": seed in response,
    "checker_results": joint_checks,
    "ok": joint_ok,
})

# The lineage-backed repeat recovery must match the exact checker target.
repeat = instructions_registry.INSTRUCTION_DICT["combination:repeat_prompt"]("combination:repeat_prompt")
repeat_desc = repeat.build_description(prompt_to_repeat=BASE)
out = composer.compose(DEFAULT_SEED, BASE + " " + repeat_desc)
resp = out.get("response") or ""
results.append({
    "kind": "interaction",
    "name": "lineage_repeat_prefix_recovery",
    "status": out.get("status"),
    "seed_preserved": DEFAULT_SEED in resp,
    "exact_checker_pass": bool(repeat.check_following(resp)),
    "ok": bool(
        out.get("status") == "PASS_CANDIDATE_SEED_PRESERVED"
        and DEFAULT_SEED in resp
        and repeat.check_following(resp)
    ),
})

# V2-specific postscript bound must survive a following visible constraint.
post = instructions_registry.INSTRUCTION_DICT["detectable_content:postscript"]("detectable_content:postscript")
kw = instructions_registry.INSTRUCTION_DICT["keywords:existence"]("keywords:existence")
post_desc = post.build_description(postscript_marker="P.P.S")
kw_desc = kw.build_description(keywords=["cedar"])
out = composer.compose(DEFAULT_SEED, BASE + " " + post_desc + " " + kw_desc)
resp = out.get("response") or ""
post_ok = bool(post.check_following(resp))
kw_ok = bool(kw.check_following(resp))
results.append({
    "kind": "interaction",
    "name": "postscript_parameter_does_not_swallow_following_constraint",
    "status": out.get("status"),
    "seed_preserved": DEFAULT_SEED in resp,
    "checker_results": {"postscript": post_ok, "keyword": kw_ok},
    "ok": bool(
        out.get("status") == "PASS_CANDIDATE_SEED_PRESERVED"
        and DEFAULT_SEED in resp
        and post_ok
        and kw_ok
    ),
})

# Contradiction must fail rather than delete or replace seed semantics.
exist = instructions_registry.INSTRUCTION_DICT["keywords:existence"]("keywords:existence")
forbid = instructions_registry.INSTRUCTION_DICT["keywords:forbidden_words"]("keywords:forbidden_words")
prompt = (
    BASE + " "
    + exist.build_description(keywords=["cedar"]) + " "
    + forbid.build_description(forbidden_words=["cedar"])
)
out = composer.compose(DEFAULT_SEED, prompt)
results.append({
    "kind": "negative",
    "name": "required_and_forbidden_same_keyword",
    "status": out.get("status"),
    "ok": out.get("status") == "FAIL_CLOSED",
})

# A less-than violation cannot be repaired by deleting seed bytes.
freq = instructions_registry.INSTRUCTION_DICT["keywords:frequency"]("keywords:frequency")
out = composer.compose(
    "cedar cedar",
    BASE + " " + freq.build_description(keyword="cedar", frequency=2, relation="less than"),
)
results.append({
    "kind": "negative",
    "name": "less_than_violation_does_not_delete_seed",
    "status": out.get("status"),
    "ok": out.get("status") == "FAIL_CLOSED",
})

# All five intentionally unadmitted families must be recognized and fail closed.
unsupported_prompts = [
    "Your ENTIRE response should be in English language, no other language is allowed.",
    "Your response should contain at least 1 sentences.",
    "In your response, words with all capital letters should appear at least 1 times.",
    "Your entire response should be in English, and in all capital letters.",
    "Your entire response should be in English, and in all lowercase letters. No capital letters are allowed.",
]
for prompt in unsupported_prompts:
    out = composer.compose(DEFAULT_SEED, BASE + " " + prompt)
    results.append({
        "kind": "negative",
        "name": "unadmitted_family_fails_closed",
        "prompt": prompt,
        "status": out.get("status"),
        "unsupported": out.get("unsupported_constraint_ids"),
        "ok": out.get("status") == "FAIL_CLOSED" and bool(out.get("unsupported_constraint_ids")),
    })

# Duplicate same-family descriptions violate the generator conflict contract.
out = composer.compose(
    DEFAULT_SEED,
    BASE + " Include keywords ['a'] in the response. Include keywords ['b'] in the response.",
)
results.append({
    "kind": "negative",
    "name": "duplicate_family_fails_at_compiler_boundary",
    "status": out.get("status"),
    "ok": out.get("status") == "FAIL_CLOSED"
        and out.get("error") == "VISIBLE_CONSTRAINT_COMPILER_FAILED",
})

assert len(composer.SUPPORTED_IDS) == 20
assert len(composer.UNADMITTED_IDS) == 5
assert composer.SUPPORTED_IDS.isdisjoint(composer.UNADMITTED_IDS)

failed = [x for x in results if not x["ok"]]
summary = {
    "schema": "LIVEBENCH_LEGACY_SEMANTIC_SEED_COMPOSER_V2_EXACT_UPSTREAM_VERIFICATION",
    "brain_subject_blobs": {
        "compiler_v1": "e986035ff68b53c0dc7a7eb478f6e3d8882214aa",
        "compiler_v2": "0e7519f4f2b7d40084effc83a5bef814ee7fd487",
        "composer_v2": "e5207007305c26e712d2608019988d409a63f2c9",
    },
    "livebench_commit": "8f8e5c381a16e3f24257776edd53471fe86f8091",
    "supported_family_count": len(composer.SUPPORTED_IDS),
    "legacy_registry_family_count": len(instructions_registry.INSTRUCTION_DICT),
    "single_family_exact_checks": len(cases),
    "test_instances": len(results),
    "passed": len(results) - len(failed),
    "failed": len(failed),
    "all_pass": not failed,
    "failed_rows": failed,
    "terminal_case_content_read": False,
    "terminal_case_ids_read": False,
    "hidden_terminal_kwargs_read": False,
    "model_dependency_count": 0,
    "acceptance_credit_delta": 0,
    "hard_nonclaim": (
        "EXACT_CHECKER_VERIFICATION_ON_SYNTHETIC_NONTERMINAL_INPUTS_DOES_NOT_PROVE_"
        "TERMINAL_SCORE_MASS_OR_SEMANTIC_NEUTRALITY_OF_ADDED_FORMATTING"
    ),
}
receipt = ROOT / "livebench_legacy_semantic_seed_composer_v2_receipt.json"
receipt.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
print(json.dumps(summary, indent=2, sort_keys=True))
if failed:
    raise SystemExit(1)
