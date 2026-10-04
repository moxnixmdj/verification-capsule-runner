#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_COMMITMENT_OPENING_PUBLIC_VERIFICATION_V1"
HISTORICAL_RUNNER_COMMIT = "d8e6edd61fb1fbeedd856aa31cc202348e52529c"
HISTORICAL_RUNNER_BLOB = "05d71d3d06ebac9b5d74eb31b137141e6b8797c2"
PRIOR_RECEIPT_BLOB = "0ddffd52cd05b880964cf034527aabddb255baef"
PUBLISHED_TERMINAL_SET_COMMITMENT = "af4eeddebf27394eb689d2049f2f8104ae081ebafe237258bdc1a992e96f598d"

ACTIVE_IDS = (
    "keywords:existence",
    "keywords:forbidden_words",
    "length_constraints:number_paragraphs",
    "length_constraints:number_words",
    "length_constraints:number_sentences",
    "length_constraints:nth_paragraph_first_word",
    "detectable_content:postscript",
    "detectable_format:number_bullet_lists",
    "detectable_format:title",
    "detectable_format:multiple_sections",
    "detectable_format:json_format",
    "combination:repeat_prompt",
    "combination:two_responses",
    "startend:end_checker",
    "startend:quotation",
)

EXPECTED_EXPRESSION = 'hashlib.sha256(json.dumps(sorted(unknown)).encode()).hexdigest()'

def git_blob(data: bytes) -> str:
    h = hashlib.sha1()
    h.update(b"blob " + str(len(data)).encode("ascii") + b"\0" + data)
    return h.hexdigest()

def main() -> int:
    root = Path(__file__).resolve().parent
    runner_repo = root
    raw = subprocess.check_output(
        ["git", "-C", str(runner_repo), "show", f"{HISTORICAL_RUNNER_COMMIT}:execute_livebench_if_threshold_v1.py"]
    )
    if git_blob(raw) != HISTORICAL_RUNNER_BLOB:
        raise SystemExit("FAIL_CLOSED:HISTORICAL_RUNNER_BLOB_DRIFT")
    text = raw.decode("utf-8")
    if EXPECTED_EXPRESSION not in text:
        raise SystemExit("FAIL_CLOSED:COMMITMENT_EXPRESSION_DRIFT")
    if "if iid not in instructions_registry.INSTRUCTION_DICT:" not in text:
        raise SystemExit("FAIL_CLOSED:UNKNOWN_SET_SEMANTICS_DRIFT")

    got = hashlib.sha256(json.dumps(sorted(ACTIVE_IDS)).encode()).hexdigest()
    if len(ACTIVE_IDS) != 15 or len(set(ACTIVE_IDS)) != 15:
        raise SystemExit("FAIL_CLOSED:ACTIVE_SET_CARDINALITY")
    if got != PUBLISHED_TERMINAL_SET_COMMITMENT:
        raise SystemExit("FAIL_CLOSED:COMMITMENT_OPENING_MISMATCH")

    receipt = {
        "schema": SCHEMA,
        "status": "PASS_EXISTING_TERMINAL_COMMITMENT_OPENS_TO_EXACT_15_ID_SET",
        "prior_terminal_receipt_binding": {
            "brain_receipt_git_blob_sha": PRIOR_RECEIPT_BLOB,
            "published_unmatched_instruction_id_set_sha256": PUBLISHED_TERMINAL_SET_COMMITMENT,
        },
        "historical_runner_binding": {
            "repository": "moxnixmdj/verification-capsule-runner",
            "commit": HISTORICAL_RUNNER_COMMIT,
            "runner_git_blob_sha": HISTORICAL_RUNNER_BLOB,
            "verified_hash_expression": EXPECTED_EXPRESSION,
            "unknown_set_semantics": "IDS_PRESENT_IN_FROZEN_POPULATION_BUT_ABSENT_FROM_MODERN_IFBENCH_REGISTRY",
        },
        "opening": {
            "active_distinct_id_count": 15,
            "ids": sorted(ACTIVE_IDS),
            "recomputed_sha256": got,
            "matches_published_commitment": True,
        },
        "firewall": {
            "new_terminal_cases_read": 0,
            "terminal_prompt_text_read": False,
            "terminal_kwargs_read": False,
            "terminal_question_ids_read": False,
            "terminal_scores_read": False,
            "incremental_spend_usd": 0,
        },
        "hard_nonclaims": [
            "SHA256_OPENING_PROVES_THE_COMMITTED_SET_UNDER_COLLISION_RESISTANCE",
            "THIS_RECEIPT_DOES_NOT_PROVE_CASE_FREQUENCIES_OR_COMBINATIONS",
            "THIS_RECEIPT_DOES_NOT_PROVE_A_LIVEBENCH_PASS",
            "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
        ],
    }
    Path("livebench_legacy15_commitment_opening_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
