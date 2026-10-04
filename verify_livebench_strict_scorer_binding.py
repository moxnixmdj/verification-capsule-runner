#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
SUBJECT = ROOT / "subject/livebench_strict_scorer_binding_20261005"
LIVEBENCH = ROOT / "upstream/LiveBench"
NLTK_DATA_REPO = ROOT / "upstream/nltk_data"

EXPECTED_SUBJECT_BLOBS = {
    "canonical/runtime/livebench_legacy15_exact_postvalidator_v1.py":
        "a20b2b4d81735b203d25430fec031f5dff33822a",
    "canonical/runtime/livebench_legacy15_slot_feasibility_v1.py":
        "312285a1b500a6fe538dfc4fe88fa888bb702147",
    "canonical/runtime/livebench_legacy15_composition_archetypes_v1.py":
        "0dbef76a6189a3cdc21ce3dae97ef6921e333b34",
}
LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
NLTK_DATA_COMMIT = "550b6625bcef1f2abff2ff770a5a0d272c9c6b2a"
PUNKT_TAB_ZIP_BLOB = "5e5ff6137d5ee6025e400d1c3a7b21914c48b635"
STRICT_REASON = "STRICT_NONEMPTY_RESPONSE_IMPLIES_AT_LEAST_ONE_PUNKT_SENTENCE"


def sh(*args: str) -> str:
    return subprocess.check_output(args, text=True).strip()


def c(iid: str, **slots):
    return {
        "instruction_id": iid,
        "slots": slots,
        "parameter_complete": True,
    }


def main() -> int:
    observed_subject = {}
    for rel, expected in EXPECTED_SUBJECT_BLOBS.items():
        path = SUBJECT / rel
        got = sh("git", "hash-object", str(path))
        assert got == expected, (rel, got, expected)
        observed_subject[rel] = got

    assert sh("git", "-C", str(LIVEBENCH), "rev-parse", "HEAD") == LIVEBENCH_COMMIT
    assert sh("git", "-C", str(NLTK_DATA_REPO), "rev-parse", "HEAD") == NLTK_DATA_COMMIT
    punkt_blob = sh(
        "git", "-C", str(NLTK_DATA_REPO), "rev-parse",
        "HEAD:packages/tokenizers/punkt_tab.zip"
    )
    assert punkt_blob == PUNKT_TAB_ZIP_BLOB, (punkt_blob, PUNKT_TAB_ZIP_BLOB)

    sys.path.insert(0, str(SUBJECT))
    from canonical.runtime import livebench_legacy15_exact_postvalidator_v1 as p
    from canonical.runtime import livebench_legacy15_slot_feasibility_v1 as f

    assert p.PINNED_LIVEBENCH_COMMIT == LIVEBENCH_COMMIT
    assert p.PINNED_NLTK_VERSION == "3.10.3"
    source = p.verify_pinned_source(LIVEBENCH)
    assert source["evaluation_main_blob"] == p.PINNED_EVALUATION_MAIN_BLOB
    assert source["strict_nonempty_response_gate_bound"] is True

    registry, binding = p.load_pinned_registry(LIVEBENCH)
    assert binding["nltk_version"] == "3.10.3"
    assert binding["strict_nonempty_response_gate_bound"] is True

    forbidden = c("keywords:forbidden_words", forbidden_words=["omega"])
    strict = p.checker_for_root(LIVEBENCH)

    # Exact checker-local ForbiddenWords would accept empty text; the frozen
    # strict evaluator must reject it before checker credit.
    assert strict("", [forbidden]) == (False,)
    assert strict("   \n\t", [forbidden]) == (False,)
    assert strict("alpha", [forbidden]) == (True,)

    sentence_zero = c(
        "length_constraints:number_sentences",
        num_sentences=1,
        relation="less than",
    )
    assert strict("", [sentence_zero]) == (False,)
    assert strict("x", [sentence_zero]) == (False,)
    reasons = f.hard_unsat_reasons([sentence_zero])
    assert reasons == (STRICT_REASON,), reasons

    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_STRICT_SCORER_BINDING_PUBLIC_RUNNER_VERIFICATION_V1",
        "status": "INDEPENDENT_PASS",
        "subject_blobs": observed_subject,
        "livebench_commit": LIVEBENCH_COMMIT,
        "evaluation_main_blob": source["evaluation_main_blob"],
        "instructions_blob": source["instructions_blob"],
        "registry_blob": source["registry_blob"],
        "instructions_util_blob": source["instructions_util_blob"],
        "nltk_version": binding["nltk_version"],
        "nltk_data_commit": NLTK_DATA_COMMIT,
        "punkt_tab_zip_git_blob": punkt_blob,
        "strict_empty_forbidden_score": False,
        "strict_nonempty_forbidden_score": True,
        "strict_sentence_lt_one_empty_score": False,
        "strict_sentence_lt_one_nonempty_score": False,
        "strict_sentence_lt_one_unsat_reason": STRICT_REASON,
        "terminal_case_content_read": 0,
        "hidden_kwargs_read": 0,
        "comparator_responses_read": 0,
        "terminal_scores_read": 0,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
    }
    out = ROOT / "livebench_strict_scorer_binding_verification.json"
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
