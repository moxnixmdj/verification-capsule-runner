#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import urllib.request
from decimal import Decimal, getcontext
from pathlib import Path

getcontext().prec = 40

BRAIN_COMMIT = "8dc7eec6f6cff6d1adb08fcf378b4e187cb002db"
SUBJECT_PATH = "canonical/governance/LIVEBENCH_ROOT1_THREE_TRANSFORM_MINIMUM_REPAIR_CUT_V1.json"
SUBJECT_BLOB = "2c583464110cbc4a60f2302eae062aa203bc7427"
GEOMETRY_PATH = "canonical/governance/LIVEBENCH_2026_06_25_OPUS55_IF_TARGET_GEOMETRY_V1.json"
GEOMETRY_BLOB = "0214ddfa1082b3fafd652bab23a1ed9e130ee94f"
MASS_PATH = "canonical/governance/LIVEBENCH_IF_SCORE_MASS_MINIMUM_CUT_V1.json"
MASS_BLOB = "ad60e8dce539f9f2b1d631ae2c6ced9efb6b1aeb"
FRONTIER_PATH = "canonical/governance/LIVEBENCH_ROOT1_SEMANTIC_SEED_REPAIR_FRONTIER_V1.json"
FRONTIER_BLOB = "844eb26e1ddefb49240c1ad61d7e5466b58e45c2"

def fetch(path: str) -> bytes:
    url = f"https://raw.githubusercontent.com/moxnixmdj/brain/{BRAIN_COMMIT}/{path}"
    req = urllib.request.Request(url, headers={"User-Agent":"project-brain-independent-verifier"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()

def git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def load(path: str, expected_blob: str):
    raw = fetch(path)
    assert git_blob_sha(raw) == expected_blob, (path, git_blob_sha(raw), expected_blob)
    return json.loads(raw)

def D(x) -> Decimal:
    return Decimal(str(x))

def main() -> int:
    subject = load(SUBJECT_PATH, SUBJECT_BLOB)
    geometry = load(GEOMETRY_PATH, GEOMETRY_BLOB)
    _mass = load(MASS_PATH, MASS_BLOB)
    frontier = load(FRONTIER_PATH, FRONTIER_BLOB)

    assert subject["target_predicate"] == "LIVEBENCH_IF_GE_65_7"
    assert geometry["target_predicate"] == subject["target_predicate"]
    g = geometry["exact_geometry"]
    assert g["questions_per_task"] == {
        "paraphrase":50, "simplify":50, "story_generation":50, "summarize":50
    }
    assert g["total_questions"] == 200
    assert g["pooled_question_mean_equivalent"] is True

    displayed = D(g["one_decimal_display_percent"])
    exact = D(g["exact_equal_weight_mean_percent"])
    assert displayed == D("65.7")
    assert exact == D("65.73775")

    three_display_sum = displayed * D(4)
    three_display_mean = three_display_sum / D(3)
    three_exact_sum = exact * D(4)
    three_exact_mean = three_exact_sum / D(3)

    assert three_display_sum == D("262.8")
    assert three_display_mean == D("87.6")
    assert three_exact_sum == D("262.951")
    assert three_exact_mean == D("87.65033333333333333333333333333333333333")

    assert (D(100)+D(100)+D(100)+D(0))/D(4) == D(75)
    assert (D(100)+D(100)+D("62.8")+D(0))/D(4) == displayed
    assert (D(100)+D(100)+D("62.951")+D(0))/D(4) == exact

    theorem = subject["theorem"]
    assert D(theorem["displayed_threshold"]["required_sum_of_three_task_scores_percent"]) == three_display_sum
    assert D(theorem["displayed_threshold"]["required_mean_of_three_task_scores_percent"]) == three_display_mean
    assert D(theorem["stricter_raw_comparator_mean"]["required_sum_of_three_task_scores_percent"]) == three_exact_sum
    assert D(theorem["stricter_raw_comparator_mean"]["required_mean_of_three_task_scores_percent"]) == three_exact_mean

    prior = frontier["minimum_repair_layers"][0]["required_effects"]
    assert "text.story.generate_instruction_grounded" in prior
    assert set(["text.paraphrase.semantic_preserving","text.simplify.semantic_preserving","text.summarize.faithful"]).issubset(prior)

    nonclaims = set(subject["hard_nonclaims"])
    assert "NO_CLAIM_THE_THREE_TRANSFORM_TASKS_ARE_CURRENTLY_SOLVED" in nonclaims
    assert "NO_CLAIM_STORY_GENERATION_IS_NOT_A_USEFUL_TERMINAL_CAPABILITY" in nonclaims
    assert subject["semantic_truth_firewall"]["story_generation_terminal_obligation"].startswith("DEFERRED_FROM_THIS_ROOT1_MINIMUM_CUT_ONLY")

    receipt = {
        "schema":"PROJECT_BRAIN_LIVEBENCH_THREE_TRANSFORM_MINIMUM_REPAIR_CUT_INDEPENDENT_VERIFICATION_V1",
        "status":"PASS",
        "verified_brain_commit":BRAIN_COMMIT,
        "verified_blobs":{
            "subject":SUBJECT_BLOB,
            "target_geometry":GEOMETRY_BLOB,
            "score_mass_cut":MASS_BLOB,
            "prior_semantic_frontier":FRONTIER_BLOB,
        },
        "verified":{
            "four_equal_task_groups":True,
            "questions_per_group":50,
            "total_questions":200,
            "displayed_threshold_percent":"65.7",
            "exact_comparator_mean_percent":"65.73775",
            "story_zero_displayed_required_three_task_sum_percent":"262.8",
            "story_zero_displayed_required_three_task_mean_percent":"87.6",
            "story_zero_exact_required_three_task_sum_percent":"262.951",
            "story_zero_exact_required_three_task_mean_percent":str(three_exact_mean),
            "three_full_transform_tasks_aggregate_percent":"75",
            "two_full_plus_62_8_third_aggregate_percent":"65.7",
            "two_full_plus_62_951_third_aggregate_percent":"65.73775",
        },
        "deduction":[
            "STORY_GENERATION_IS_NOT_REQUIRED_ON_THE_MINIMUM_PATH_TO_DISCHARGE_LIVEBENCH_IF_GE_65_7",
            "THE_PRIOR_FOUR_SEMANTIC_EFFECT_LIST_IS_OVERCONSTRAINED_FOR_THIS_ROOT1_FIXED_BAR",
            "THREE_NON_STORY_TASKS_CAN_CARRY_THE_ENTIRE_FIXED_BAR_SCORE_MASS",
            "THIS_DOES_NOT_DELETE_STORY_GENERATION_FROM_THE_TERMINAL_CAPABILITY_OBJECTIVE",
        ],
        "hard_nonclaims":[
            "NO_CLAIM_THE_THREE_TRANSFORM_TASKS_ARE_SOLVED",
            "NO_BENCHMARK_PASS_OR_ACCEPTANCE_PROMOTION",
            "NO_SEMANTIC_CAPABILITY_CREDIT_FROM_ARITHMETIC",
            "NO_NEW_TERMINAL_CASE_EXPOSURE",
        ],
        "accounting":{
            "incremental_spend_usd":0,
            "new_terminal_cases_exposed":0,
            "acceptance_credit_delta":0,
        },
    }
    Path("livebench_three_transform_cut_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True)+"\n", encoding="utf-8"
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
