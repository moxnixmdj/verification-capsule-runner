#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
SUBJECT = ROOT / "subject/livebench_reduction_m_20261005"

EXPECTED = {
    "canonical/runtime/livebench_legacy15_composition_archetypes_v1.py": "0dbef76a6189a3cdc21ce3dae97ef6921e333b34",
    "canonical/runtime/livebench_legacy15_contract_composer_v2.py": "d73ec366b32252996258eae6d10d67d4d6a5e042",
    "canonical/runtime/livebench_legacy15_slot_feasibility_v1.py": "7477f5ea5bdeac3595ee2784a38d078fe2f385b0",
    "canonical/runtime/livebench_legacy15_lexical_slot_quotient_v1.py": "5803c31e3972c6d40415f319e808c48420bc0388",
    "canonical/runtime/livebench_legacy15_pointwise_optimal_v1.py": "71e637c70edf1c582e28ea38b3b798965c803a06",
    "canonical/runtime/livebench_pointwise_minimum_cut_v1.py": "0d4e563b618f8fd7f37396a88738cefb50979ff3",
    "canonical/runtime/livebench_legacy15_numeric_quotient_v1.py": "72189bb8adb12ad36a52ee666a1f79fbb201b06b",
}

def git_blob(path: pathlib.Path) -> str:
    return subprocess.run(
        ["git", "hash-object", str(path)],
        check=True, text=True, capture_output=True
    ).stdout.strip()

def main() -> int:
    observed = {}
    for rel, expected in EXPECTED.items():
        path = SUBJECT / rel
        got = git_blob(path)
        observed[rel] = got
        assert got == expected, (rel, got, expected)

    sys.path.insert(0, str(SUBJECT))
    from canonical.runtime import livebench_legacy15_numeric_quotient_v1 as numeric
    from canonical.runtime import livebench_pointwise_minimum_cut_v1 as cut

    numeric_out = numeric.verify()
    cut_out = cut.verify()

    assert numeric_out["status"] == "PASS__PARAMETRIC_NUMERIC_REDUCTION", numeric_out
    word = numeric_out["word_upper_bound"]
    cross = word["executable_structural_crosscheck"]
    assert word["analytic_constructor_ceiling"] == 48, word
    assert word["minimum_safety_margin"] == 52, word
    assert cross["examined"] == 371, cross
    assert cross["constructed"] == 371, cross
    assert cross["maximum"] <= 48, cross

    expected_cut_status = (
        "PASS__EXACT_STRUCTURAL_X_LEXICAL_X_SENTENCE_PARTITION__"
        "ONLY_TWO_MANDATORY_LOSS_COORDINATES"
    )
    assert cut_out["status"] == expected_cut_status, cut_out
    assert cut_out["structural_id_sets"] == 928, cut_out
    assert cut_out["reachable_lexical_signatures"] == 192, cut_out
    assert cut_out["sentence_partition_states"] == 2, cut_out
    assert cut_out["exact_classification_cases"] == 356352, cut_out
    assert cut_out["maximum_mandatory_sacrifices_per_case"] == 2, cut_out

    coords = {
        x["coordinate"]: x["minimum_sacrifice"]
        for x in cut_out["mandatory_loss_coordinates"]
    }
    assert coords == {
        "sentence_zero": "length_constraints:number_sentences",
        "forbidden_collision_cluster": "keywords:forbidden_words",
    }, coords

    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_REDUCTION_INDEPENDENT_VERIFICATION_20261005_V1",
        "status": "PASS__CONTENT_BOUND_MINIMUM_CUT_AND_NUMERIC_REDUCTION",
        "subject_blobs": observed,
        "numeric": {
            "word_ceiling": word["analytic_constructor_ceiling"],
            "minimum_public_word_threshold": numeric.WORD_MIN,
            "safety_margin": word["minimum_safety_margin"],
            "structural_sets_with_word_checker": cross["examined"],
            "executable_maximum": cross["maximum"],
            "sentence_partition": numeric_out["sentence_partition"],
        },
        "minimum_cut": {
            "structural_id_sets": cut_out["structural_id_sets"],
            "lexical_signatures": cut_out["reachable_lexical_signatures"],
            "sentence_partition_states": cut_out["sentence_partition_states"],
            "exact_classification_cases": cut_out["exact_classification_cases"],
            "maximum_mandatory_sacrifices_per_case": cut_out["maximum_mandatory_sacrifices_per_case"],
            "mandatory_loss_coordinates": cut_out["mandatory_loss_coordinates"],
            "loss_histogram": cut_out["loss_histogram_over_classification_basis"],
        },
        "terminal_rows_read": 0,
        "hidden_kwargs_read": 0,
        "target_scores_read": 0,
        "acceptance_credit_delta": 0,
        "hard_nonclaims": [
            "THIS_RECEIPT_DOES_NOT_BY_ITSELF_PROVE_UNIVERSAL_POST_SACRIFICE_CONSTRUCTION",
            "THIS_RECEIPT_DOES_NOT_BY_ITSELF_PROMOTE_LIVEBENCH_ACCEPTANCE",
        ],
    }
    pathlib.Path("livebench_reduction_independent_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
