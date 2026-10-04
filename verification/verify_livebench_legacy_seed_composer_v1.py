#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
INPUT_ROOT = ROOT / "verification_inputs"
UPSTREAM = pathlib.Path("/tmp/LiveBench/livebench/if_runner")
sys.path.insert(0, str(INPUT_ROOT))
sys.path.insert(0, str(UPSTREAM))

EXPECTED = {
    INPUT_ROOT / "canonical/runtime/livebench_legacy_ifeval_prompt_inverter_v1.py":
        "74904d2a00ed3f0bb2e8ab7787c59c0a8f828f7a",
    INPUT_ROOT / "canonical/runtime/livebench_legacy_seed_composer_v1.py":
        "f8c7622e42f98edb153c99ecb09a3a66c89fc096",
}

def git_blob(path: pathlib.Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

for path, expected in EXPECTED.items():
    got = git_blob(path)
    assert got == expected, (path, got, expected)

from canonical.runtime import livebench_legacy_seed_composer_v1 as composer
from instruction_following_eval import instructions_registry

BASE = "Explain the topic clearly."
DEFAULT_SEED = "The semantic answer remains intact and useful."

cases = [
    ("keywords:existence", {"keywords":["alpha","beta"]}, DEFAULT_SEED),
    ("keywords:frequency", {"keyword":"alpha","frequency":3,"relation":"at least"}, DEFAULT_SEED),
    ("keywords:forbidden_words", {"forbidden_words":["alpha","beta"]}, DEFAULT_SEED),
    ("keywords:letter_frequency", {"letter":"q","let_frequency":4,"let_relation":"at least"}, DEFAULT_SEED),
    ("length_constraints:number_words", {"num_words":6,"relation":"at least"},
        "one two three four five six semantic words remain"),
    ("detectable_content:number_placeholders", {"num_placeholders":3}, DEFAULT_SEED),
    ("detectable_content:postscript", {"postscript_marker":"P.S."}, DEFAULT_SEED),
    ("detectable_format:number_bullet_lists", {"num_bullets":3}, DEFAULT_SEED),
    ("detectable_format:constrained_response", {}, "My answer is yes."),
    ("detectable_format:number_highlighted_sections", {"num_highlights":3}, DEFAULT_SEED),
    ("detectable_format:multiple_sections", {"section_spliter":"Section","num_sections":3}, DEFAULT_SEED),
    ("detectable_format:title", {}, DEFAULT_SEED),
    ("combination:two_responses", {}, "semantic alpha******semantic beta"),
    ("combination:repeat_prompt", {"prompt_to_repeat":BASE}, DEFAULT_SEED),
    ("startend:end_checker", {"end_phrase":"Any other questions?"}, DEFAULT_SEED),
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
        "kind":"single_family",
        "instruction_id":iid,
        "status":out.get("status"),
        "exact_checker_pass":exact_pass,
        "seed_preserved":seed in response,
        "ok":ok,
        "error":exact_error,
    })

# Interaction: highlighted spans must not accidentally become bullet lines.
inst_h = instructions_registry.INSTRUCTION_DICT["detectable_format:number_highlighted_sections"](
    "detectable_format:number_highlighted_sections"
)
inst_b = instructions_registry.INSTRUCTION_DICT["detectable_format:number_bullet_lists"](
    "detectable_format:number_bullet_lists"
)
desc_h = inst_h.build_description(num_highlights=2)
desc_b = inst_b.build_description(num_bullets=2)
seed = DEFAULT_SEED
out = composer.compose(seed, f"{BASE} {desc_h} {desc_b}")
resp = out.get("response") or ""
ok = (
    out.get("status") == "PASS_CANDIDATE_SEED_PRESERVED"
    and seed in resp
    and inst_h.check_following(resp)
    and inst_b.check_following(resp)
)
results.append({
    "kind":"interaction",
    "name":"highlight_plus_bullet_no_alias",
    "status":out.get("status"),
    "seed_preserved":seed in resp,
    "exact_checker_pass":bool(inst_h.check_following(resp) and inst_b.check_following(resp)),
    "ok":bool(ok),
})

# Interaction: suffix phrase followed by outer quotation must satisfy both exact checkers.
inst_e = instructions_registry.INSTRUCTION_DICT["startend:end_checker"]("startend:end_checker")
inst_q = instructions_registry.INSTRUCTION_DICT["startend:quotation"]("startend:quotation")
desc_e = inst_e.build_description(end_phrase="Any other questions?")
desc_q = inst_q.build_description()
seed = DEFAULT_SEED
out = composer.compose(seed, f"{BASE} {desc_e} {desc_q}")
resp = out.get("response") or ""
ok = (
    out.get("status") == "PASS_CANDIDATE_SEED_PRESERVED"
    and seed in resp
    and inst_e.check_following(resp)
    and inst_q.check_following(resp)
)
results.append({
    "kind":"interaction",
    "name":"end_then_outer_quote",
    "status":out.get("status"),
    "seed_preserved":seed in resp,
    "exact_checker_pass":bool(inst_e.check_following(resp) and inst_q.check_following(resp)),
    "ok":bool(ok),
})

# Multi-constraint constructive path on five non-lossy families.
multi_specs = [
    ("keywords:existence", {"keywords":["cedar"]}),
    ("detectable_content:number_placeholders", {"num_placeholders":2}),
    ("detectable_format:title", {}),
    ("startend:end_checker", {"end_phrase":"Any other questions?"}),
    ("punctuation:no_comma", {}),
]
instances=[]
descs=[]
for iid, kwargs in multi_specs:
    inst=instructions_registry.INSTRUCTION_DICT[iid](iid)
    descs.append(inst.build_description(**kwargs))
    instances.append(inst)
seed="Cedar forests store carbon safely."
out=composer.compose(seed, BASE+" "+" ".join(descs))
resp=out.get("response") or ""
exact_all=all(inst.check_following(resp) for inst in instances)
results.append({
    "kind":"interaction",
    "name":"five_family_semantic_seed_composition",
    "status":out.get("status"),
    "seed_preserved":seed in resp,
    "exact_checker_pass":bool(exact_all),
    "ok":bool(out.get("status")=="PASS_CANDIDATE_SEED_PRESERVED" and seed in resp and exact_all),
})

# Contradictory visible constraints must fail rather than invent a fake success.
exist = instructions_registry.INSTRUCTION_DICT["keywords:existence"]("keywords:existence")
forbid = instructions_registry.INSTRUCTION_DICT["keywords:forbidden_words"]("keywords:forbidden_words")
contradict_prompt = BASE+" "+exist.build_description(keywords=["cedar"])+" "+forbid.build_description(forbidden_words=["cedar"])
out=composer.compose(DEFAULT_SEED, contradict_prompt)
results.append({
    "kind":"negative",
    "name":"contradictory_required_and_forbidden_keyword",
    "status":out.get("status"),
    "ok":out.get("status")=="FAIL_CLOSED",
})

# Unsupported lossy case rewrite must fail closed.
lower = instructions_registry.INSTRUCTION_DICT["change_case:english_lowercase"]("change_case:english_lowercase")
out=composer.compose("Mixed Case Semantic Seed", BASE+" "+lower.build_description())
results.append({
    "kind":"negative",
    "name":"unsupported_lossy_lowercase_transform",
    "status":out.get("status"),
    "ok":out.get("status")=="FAIL_CLOSED" and "change_case:english_lowercase" in out.get("unsupported_constraint_ids",[]),
})

# Less-than frequency cannot be repaired by deleting seed bytes.
freq = instructions_registry.INSTRUCTION_DICT["keywords:frequency"]("keywords:frequency")
out=composer.compose("cedar cedar", BASE+" "+freq.build_description(keyword="cedar",frequency=2,relation="less than"))
results.append({
    "kind":"negative",
    "name":"less_than_violation_does_not_delete_seed",
    "status":out.get("status"),
    "ok":out.get("status")=="FAIL_CLOSED",
})

failed=[x for x in results if not x["ok"]]
summary={
    "schema":"LIVEBENCH_LEGACY_SEED_COMPOSER_EXACT_UPSTREAM_VERIFICATION_V1",
    "brain_subject_blobs":{
        "inverter":"74904d2a00ed3f0bb2e8ab7787c59c0a8f828f7a",
        "composer":"f8c7622e42f98edb153c99ecb09a3a66c89fc096",
    },
    "livebench_commit":"8f8e5c381a16e3f24257776edd53471fe86f8091",
    "supported_family_count":len(composer.SUPPORTED_IDS),
    "legacy_registry_family_count":len(instructions_registry.INSTRUCTION_DICT),
    "single_family_exact_checks":len(cases),
    "test_instances":len(results),
    "passed":len(results)-len(failed),
    "failed":len(failed),
    "all_pass":not failed,
    "failed_rows":failed,
    "terminal_case_content_read":False,
    "terminal_case_ids_read":False,
    "hidden_terminal_kwargs_read":False,
    "model_dependency_count":0,
    "acceptance_credit_delta":0,
    "hard_nonclaim":"SYNTHETIC_EXACT_CHECKER_VERIFICATION_DOES_NOT_PROVE_TERMINAL_POPULATION_SCORE_OR_SEMANTIC_EQUIVALENCE_OF_ADDED_MATERIAL",
}
print(json.dumps(summary,indent=2,sort_keys=True))
if failed:
    raise SystemExit(1)
