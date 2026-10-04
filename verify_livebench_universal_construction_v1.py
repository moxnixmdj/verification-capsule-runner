#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import subprocess
import sys

LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
UTIL_BLOB = "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b"

SUBJECT_BLOBS = {
    "canonical/runtime/livebench_legacy15_composition_archetypes_v1.py":
        "0dbef76a6189a3cdc21ce3dae97ef6921e333b34",
    "canonical/runtime/livebench_legacy15_contract_composer_v2.py":
        "d73ec366b32252996258eae6d10d67d4d6a5e042",
    "canonical/runtime/livebench_legacy15_lexical_slot_quotient_v1.py":
        "5803c31e3972c6d40415f319e808c48420bc0388",
    "canonical/runtime/livebench_legacy15_numeric_quotient_v1.py":
        "72189bb8adb12ad36a52ee666a1f79fbb201b06b",
    "canonical/runtime/livebench_legacy15_universal_construction_reduction_v1.py":
        "81f04ed3d21f37be7dc3469a22df739461558b69",
}

ROOT = pathlib.Path(__file__).resolve().parent
SUBJECT = ROOT / "subject/livebench_universal_construction_20261005"
OUT = ROOT / "livebench_universal_construction_verification.json"


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, text=True, **kw)


def blob(path: pathlib.Path) -> str:
    return run(["git", "hash-object", str(path)], capture_output=True).stdout.strip()


def exact_source_blob(repo: pathlib.Path, path: str) -> str:
    return run(
        ["git", "-C", str(repo), "rev-parse", f"HEAD:{path}"],
        capture_output=True,
    ).stdout.strip()


def main() -> int:
    observed = {}
    for rel, expected in SUBJECT_BLOBS.items():
        got = blob(SUBJECT / rel)
        assert got == expected, (rel, got, expected)
        observed[rel] = got

    # Require the independent exact-checker envelope pass in this same workflow.
    envelope_path = ROOT / "livebench_composer_v2_verification.json"
    envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
    assert envelope["status"] == (
        "PASS__POINTWISE_EXACT_MAX_MATCH__EXACT_PINNED_CHECKERS__ZERO_TERMINAL_ROWS"
    )
    cov = envelope["coverage"]
    assert cov["pointwise_cases"] == 12489
    assert cov["pointwise_exact_optimum_match"] == 12489
    assert cov["structural_id_sets"] == 928
    assert cov["lexical_words_exhausted"] == 1525
    assert cov["word_threshold_cases"] == 802
    assert cov["paragraph_bullet_section_cross_cases"] == 250
    assert cov["nth_cross_cases"] == 60

    live = pathlib.Path("/tmp/LiveBench")
    assert run(
        ["git", "-C", str(live), "rev-parse", "HEAD"], capture_output=True
    ).stdout.strip() == LIVEBENCH_COMMIT
    assert exact_source_blob(
        live, "livebench/if_runner/instruction_following_eval/instructions.py"
    ) == INSTRUCTIONS_BLOB
    assert exact_source_blob(
        live, "livebench/if_runner/instruction_following_eval/instructions_registry.py"
    ) == REGISTRY_BLOB
    assert exact_source_blob(
        live, "livebench/if_runner/instruction_following_eval/instructions_util.py"
    ) == UTIL_BLOB

    sys.path.insert(0, str(SUBJECT))
    sys.path.insert(0, str(live / "livebench/if_runner"))

    from canonical.runtime import livebench_legacy15_universal_construction_reduction_v1 as proof
    from instruction_following_eval import instructions_util

    theorem = proof.verify()
    assert theorem["status"].startswith(
        "PASS__UNIVERSAL_POST_SACRIFICE_CONSTRUCTION"
    )
    assert theorem["acceptance_credit"] is False

    # Independently bind the lexical source facts used by the proof.
    words = list(instructions_util.WORD_LIST)
    assert len(words) == 1525
    assert len(set(words)) == 1525
    assert all(w.isascii() and w.isalpha() for w in words)
    assert [w.lower() for w in words if len(w) == 1] == ["a"]
    lower = {w.lower() for w in words}

    phrases = (
        "Any other questions?",
        "Is there anything else I can help with?",
    )
    intersections = []
    for phrase in phrases:
        phrase_words = re.findall(r"[A-Za-z]+", phrase.lower())
        intersections.append([w for w in phrase_words if w in lower])
    assert intersections == [["other"], ["anything", "can", "help"]]

    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_UNIVERSAL_CONSTRUCTION_INDEPENDENT_VERIFICATION_V1",
        "status": (
            "PASS__SOURCE_BOUND_UNIVERSAL_REDUCTION__"
            "INDEPENDENT_12489_EXACT_CHECKER_ENVELOPE__ZERO_TERMINAL_ROWS"
        ),
        "subject_blobs": observed,
        "pinned_livebench": {
            "commit": LIVEBENCH_COMMIT,
            "instructions_blob": INSTRUCTIONS_BLOB,
            "registry_blob": REGISTRY_BLOB,
            "instructions_util_blob": UTIL_BLOB,
        },
        "universal_reduction": {
            "structural_id_sets": theorem["structural_id_sets"],
            "lexical_signatures": theorem["lexical_signatures"],
            "numeric_reduction_status": theorem["numeric_reduction_status"],
            "proof_lemmas": theorem["proof_lemmas"],
        },
        "independent_exact_checker_envelope": {
            "cases": cov["pointwise_cases"],
            "exact_pointwise_optimum_matches": cov["pointwise_exact_optimum_match"],
            "word_threshold_cases": cov["word_threshold_cases"],
            "paragraph_bullet_section_cross_cases":
                cov["paragraph_bullet_section_cross_cases"],
            "nth_cross_cases": cov["nth_cross_cases"],
        },
        "independent_public_word_facts": {
            "count": len(words),
            "unique": len(set(words)),
            "all_ascii_alpha": True,
            "single_letter_words": ["a"],
            "end_phrase_word_intersections": intersections,
        },
        "terminal_rows_read": 0,
        "hidden_terminal_kwargs_read": 0,
        "terminal_instruction_id_lists_read": 0,
        "target_scores_read": 0,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "hard_nonclaims": [
            "THIS_VERIFIES_THE_UNIVERSAL_POST_SACRIFICE_CONSTRUCTION_REDUCTION",
            "LIVEBENCH_ACCEPTANCE_STILL_REQUIRES_SEPARATE_DOMINANCE_AND_LEDGER_BINDING",
            "NO_TERMINAL_GOAL_COMPLETION_CREDIT_FROM_THIS_RECEIPT_ALONE",
        ],
    }
    OUT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
