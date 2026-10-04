#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import hashlib
import inspect
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as arch
from canonical.runtime import livebench_legacy15_contract_composer_v2 as comp
from canonical.runtime import livebench_legacy15_visible_prompt_compiler_v1 as visible

EXPECTED = {
    "canonical/runtime/livebench_legacy15_composition_archetypes_v1.py":
        "0dbef76a6189a3cdc21ce3dae97ef6921e333b34",
    "canonical/runtime/livebench_legacy15_slot_feasibility_v1.py":
        "7477f5ea5bdeac3595ee2784a38d078fe2f385b0",
    "canonical/runtime/livebench_legacy15_contract_composer_v2.py":
        "d73ec366b32252996258eae6d10d67d4d6a5e042",
    "canonical/runtime/livebench_legacy15_visible_prompt_compiler_v1.py":
        "6e4ae278c4ba81cf0fb589d4e948384d1bd61ae2",
    "canonical/runtime/livebench_legacy15_repeat_prompt_totality_v1.py":
        "90df8bd3a73fe9907e95ed50888d23ceeb11c35e",
}
PINNED_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
PINNED_INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
WORDS = ["harbor", "violet", "canyon", "meadow", "signal"]

EXPECTED_REPEAT_SETS = frozenset({
    frozenset({comp.REPEAT}),
    frozenset({comp.REPEAT, comp.EXIST}),
    frozenset({comp.REPEAT, comp.TITLE}),
    frozenset({comp.REPEAT, comp.EXIST, comp.TITLE}),
})


def blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def norm(text: str) -> str:
    return re.sub(r"\s+", "", text)


def class_source(source: str, class_name: str) -> str:
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            segment = ast.get_source_segment(source, node)
            assert segment is not None
            return segment
    raise AssertionError("CLASS_NOT_FOUND:" + class_name)


def contracts(ids: frozenset[str], prompt: str):
    out = []
    for iid in arch.ACTIVE_IDS:
        if iid not in ids:
            continue
        if iid == comp.REPEAT:
            slots = {"prompt_to_repeat": prompt}
        elif iid == comp.EXIST:
            slots = {"keywords": list(WORDS)}
        elif iid == comp.TITLE:
            slots = {}
        else:
            raise AssertionError("UNEXPECTED_REPEAT_ID:" + iid)
        out.append({"instruction_id": iid, "slots": slots, "parameter_complete": True})
    return out


def exact_repeat(response: str, prompt: str) -> bool:
    return response.strip().lower().startswith(prompt.strip().lower())


def exact_existence(response: str) -> bool:
    return all(re.search(word, response, flags=re.IGNORECASE) is not None for word in WORDS)


def exact_title(response: str) -> bool:
    titles = re.findall(re.compile(r"<<[^\n]+>>"), response)
    return any(title.lstrip("<").rstrip(">").strip() for title in titles)


def verify_public_checker_source(livebench_root: Path):
    path = (
        livebench_root
        / "livebench"
        / "if_runner"
        / "instruction_following_eval"
        / "instructions.py"
    )
    assert path.is_file(), path
    assert blob(path) == PINNED_INSTRUCTIONS_BLOB
    src = path.read_text(encoding="utf-8")

    repeat_src = norm(class_source(src, "RepeatPromptThenAnswer"))
    assert (
        "ifvalue.strip().lower().startswith("
        "self._prompt_to_repeat.strip().lower()):returnTruereturnFalse"
        in repeat_src
    )

    keyword_src = norm(class_source(src, "KeywordChecker"))
    assert (
        "ifnotre.search(keyword,value,flags=re.IGNORECASE):returnFalsereturnTrue"
        in keyword_src
    )

    title_src = norm(class_source(src, "TitleChecker"))
    assert 'pattern=r"<<[^\\n]+>>"' in title_src
    assert "ifre.search" not in title_src  # guard against silently different semantics
    assert "titles=re.findall(re_pattern,value)" in title_src
    assert "iftitle.lstrip("<").rstrip(">").strip():returnTrue" in title_src

    return {
        "instructions_blob": PINNED_INSTRUCTIONS_BLOB,
        "repeat_checker_source_bound": True,
        "existence_checker_source_bound": True,
        "title_checker_source_bound": True,
    }


def verify_visible_repeat_binding():
    marker = visible.REPEAT_MARKER
    article = "prefix " + marker + " collision inside visible article"
    task = visible.TASK_PROMPTS[0]
    repeat_desc = (
        "First repeat the request word for word without change, then give your "
        "answer (1. do not say any words or characters before repeating the "
        "request; 2. the request you need to repeat does not include this sentence)"
    )
    exist_desc = "Include keywords ['canyon', 'harbor', 'meadow', 'signal', 'violet'] in the response."
    title_desc = (
        "Your answer must contain a title, wrapped in double angular brackets, "
        "such as <<poem of joy>>."
    )
    prompt = (
        "The following are the beginning sentences of a news article from the Guardian.\n"
        "-------\n" + article + "\n-------\n" + task + " "
        + " " + exist_desc + " " + repeat_desc + " " + title_desc
    )
    out = visible.compile_visible_prompt(prompt)
    row = next(x for x in out["contracts"] if x["instruction_id"] == comp.REPEAT)
    assert row["parameter_complete"] is True
    assert row["slots"]["prompt_to_repeat"] == prompt.split(marker, 1)[0]
    assert out["terminal_rows_used"] is False
    assert out["hidden_kwargs_used"] is False
    return True


def verify_composer_source_shape():
    src = norm(inspect.getsource(comp._special_repeat))
    required = (
        'base=str(_slots(repeat).get("prompt_to_repeat")or"").strip()',
        "ifnotbase:raiseComposeError",
        "ifFORBIDDENinby_id:raiseComposeError",
        "pieces=[base]",
        'pieces.append("<<"+_SAFE+">>")',
        "packed=_packed_required(_required_words(by_id))",
        "pieces.append(packed)",
        "pieces.append(_SAFE)",
        'return"\\n".join(pieces)',
    )
    for item in required:
        assert item in src, ("COMPOSER_REPEAT_SOURCE_DRIFT", item)
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("livebench_root")
    args = ap.parse_args()

    got = {rel: blob(ROOT / rel) for rel in EXPECTED}
    assert got == EXPECTED, {"expected": EXPECTED, "got": got}

    public = verify_public_checker_source(Path(args.livebench_root).resolve())
    assert verify_composer_source_shape()
    assert verify_visible_repeat_binding()

    observed = frozenset(
        frozenset(ids)
        for ids in arch.enumerate_compatible_sets()
        if comp.REPEAT in ids
    )
    assert observed == EXPECTED_REPEAT_SETS
    assert len(observed) == 4

    # Supporting falsification. The load-bearing result is the exact-source
    # symbolic prefix argument above, not finite sampling.
    prompts = [
        "Article text.",
        "  leading and trailing whitespace  ",
        "Line one\nLine two\nLine three",
        "MiXeD CaSe + punctuation?!",
        "Ω λ 😀 日本語 العربية",
        visible.REPEAT_MARKER + " collision.",
        "<<already-title-shaped>>",
        "******",
        "\x00embedded-null-after-visible-prefix",
        "İ I ı i Σ σ ς",
    ]
    # Exhaust lone-surrogate seam and a deterministic spread over the full
    # Python Unicode code-point range without pretending this finite sweep is
    # the universal proof.
    prompts.extend("prefix-" + chr(cp) + "-suffix" for cp in range(0xD800, 0xE000))
    prompts.extend(
        "spread-" + chr(cp) + "-value"
        for cp in range(0, 0x110000, 257)
    )

    cases = 0
    for prompt in prompts:
        assert prompt.strip()
        for ids in EXPECTED_REPEAT_SETS:
            built = comp.compose_contracts(contracts(ids, prompt))
            assert built["status"] == "CANDIDATE_WITNESS", (ids, built)
            response = str(built["response"])
            assert exact_repeat(response, prompt)
            if comp.EXIST in ids:
                assert exact_existence(response)
            if comp.TITLE in ids:
                assert exact_title(response)
            cases += 1

    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_REPEAT_PROMPT_TOTALITY_INDEPENDENT_VERIFICATION_V1",
        "status": (
            "PASS__INDEPENDENT_EXACT_SOURCE_BOUND_REPEAT_TEXT_IDENTITY_REDUCTION__"
            "ZERO_TERMINAL_DATA__ZERO_CREDIT"
        ),
        "brain_subject_blobs": EXPECTED,
        "pinned_livebench_commit": PINNED_LIVEBENCH_COMMIT,
        "public_checker_binding": public,
        "repeat_compatible_set_count": 4,
        "symbolic_proof": {
            "composer_base_is_prompt_strip_and_first": True,
            "only_suffix_co_contracts": ["keywords:existence", "detectable_format:title"],
            "repeat_checker_is_strip_lower_startswith": True,
            "arbitrary_prompt_identity_can_change_repeat_verdict": False,
            "prompt_identity_enumeration_required": False,
        },
        "visible_historical_repeat_binding_verified": True,
        "supporting_falsification": {
            "prompt_representatives": len(prompts),
            "composer_checker_cases": cases,
            "lone_surrogate_codepoints": 0x800,
            "unicode_spread_step": 257,
            "all_pass": True,
        },
        "terminal_rows_read": 0,
        "hidden_terminal_kwargs_read": 0,
        "terminal_frequencies_read": 0,
        "target_scores_read": 0,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "hard_nonclaims": [
            "NO_FULL_LIVEBENCH_POINTWISE_COMPLETENESS_CLAIM_FROM_THIS_LEMMA_ALONE",
            "NO_LIVEBENCH_ACCEPTANCE_PROMOTION",
            "NO_TERMINAL_CASE_EXECUTION_OR_EXPOSURE",
        ],
    }
    out = ROOT / "livebench_repeat_prompt_totality_receipt.json"
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=True) + "\n")
    print(json.dumps(receipt, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
