from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
inp = json.loads((ROOT / "input.json").read_text(encoding="utf-8"))
freeze = json.loads((ROOT / "freeze.json").read_text(encoding="utf-8"))
normalizer_path = ROOT / "normalizer.py"


def blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


errors = []

exact = inp["exact_load_bearing_brain_blobs"]
if blob_sha(ROOT / "freeze.json") != exact["canonical/governance/P1_SHARED_FAILURE_SEMANTICS_BATCH_FREEZE_V1.json"]:
    errors.append("FREEZE_BLOB_MISMATCH")
if blob_sha(normalizer_path) != exact["canonical/runtime/p1_shared_failure_semantics_normalizer_v1.py"]:
    errors.append("NORMALIZER_BLOB_MISMATCH")

expected_authority = inp["expected_bound_authority_blobs"]
authority = freeze.get("exact_authority") or {}
if set(authority) != set(expected_authority):
    errors.append("AUTHORITY_KEY_SET")
for key, expected_sha in expected_authority.items():
    row = authority.get(key) or {}
    if row.get("git_blob_sha") != expected_sha:
        errors.append("AUTHORITY_SHA:" + key)

if freeze.get("selected_observation") != "P1_SHARED_SOURCE_BOUND_FAILURE_SEMANTICS_BATCH":
    errors.append("SELECTED_OBSERVATION")
if freeze.get("minimum_new_reality_units") != 1:
    errors.append("MINIMUM_REALITY")
if set(freeze.get("frozen_direct_surfaces") or []) != {
    "T0/FRONTIERCODE_V1_1::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
    "T0/CURSORBENCH_4_0::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
    "T2/RECOVERY_SCOPE_COMPOSITION::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
}:
    errors.append("SURFACE_SET")

pipe = freeze.get("frozen_pipeline") or {}
if pipe.get("candidate") != "canonical/runtime/trajectory_failure_typed_ir_candidate_v7.py":
    errors.append("CANDIDATE_NOT_V7")
if pipe.get("scorer") != "canonical/runtime/trajectory_failure_typed_ir_proof_v6.py::score_case":
    errors.append("SCORER_NOT_V6_INTERVENTION")
if pipe.get("source_semantics_normalizer") != "canonical/runtime/p1_shared_failure_semantics_normalizer_v1.py":
    errors.append("NORMALIZER_PATH")
if set(pipe.get("semantic_classes") or []) != {"DIRECT_CONTRACT", "DERIVED_UPSTREAM"}:
    errors.append("SEMANTIC_CLASSES")

contract = freeze.get("shared_batch_contract") or {}
for key in (
    "one_batch_covers_all_three_surfaces",
    "all_three_surface_identities_required",
    "both_failure_semantics_classes_required_per_admitted_case",
    "v7_candidate_frozen_before_case_selection",
    "scorer_frozen_before_case_selection",
    "normalizer_frozen_before_case_selection",
    "surface_mapping_frozen_before_case_selection",
    "post_freeze_case_selection_required",
    "candidate_must_not_receive_case_selection_information_before_freeze",
    "fresh_case_source_must_be_external_or_source_native_and_not_chosen_from_result_feedback",
    "synthetic_v7_only_credit_forbidden",
):
    if contract.get(key) is not True:
        errors.append("CONTRACT_TRUE:" + key)
for key in ("terminal_v3_replay", "post_result_case_replacement", "post_result_tuning"):
    if contract.get(key) is not False:
        errors.append("CONTRACT_FALSE:" + key)
if contract.get("incremental_spend_usd") != 0:
    errors.append("SPEND")

boundary = freeze.get("admission_boundary") or {}
if boundary.get("this_freeze_consumes_fresh_reality") is not False:
    errors.append("FREEZE_CONSUMES_REALITY")
if boundary.get("this_freeze_authorizes_execution") is not False:
    errors.append("FREEZE_PREMATURE_AUTHORITY")
if boundary.get("execution_may_be_authorized_only_after_independent_verification_of_exact_freeze_and_normalizer_bytes") is not True:
    errors.append("INDEPENDENT_GATE")
if boundary.get("fresh_batch_must_still_supply_source_bound_semantics_and_receipts") is not True:
    errors.append("SOURCE_BINDING_GATE")

if freeze.get("new_reality_units_consumed") != 0:
    errors.append("NEW_REALITY")
if freeze.get("terminal_results_replayed") != 0:
    errors.append("REPLAY")
if freeze.get("incremental_spend_usd") != 0:
    errors.append("TOP_LEVEL_SPEND")
if freeze.get("capability_credit_delta") != 0 or freeze.get("family_credit_delta") != 0:
    errors.append("CREDIT")
if freeze.get("execution_authority") is not False or freeze.get("promotion_authority") is not False:
    errors.append("AUTHORITY_OVERCLAIM")

source = normalizer_path.read_text(encoding="utf-8")
if 'get("failure_semantics",' in source or "get('failure_semantics'," in source:
    errors.append("NORMALIZER_HAS_DEFAULT_FAILURE_SEMANTICS")

spec = importlib.util.spec_from_file_location("p1_normalizer", normalizer_path)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)

surfaces = sorted(module.SURFACES)


def good_case(surface: str):
    return {
        "surface_id": surface,
        "case_id": "independent-preflight",
        "source_observation_receipt": "source:independent",
        "trajectory": [
            {
                "step": 1,
                "action_id": "A1",
                "domain": "CODE",
                "reads": [],
                "writes": ["x"],
                "depends_on": [],
                "dependency_composition": "SEQUENTIAL",
                "checks": [
                    {"kind": "SCOPE", "id": "A1:S", "pass": False, "evidence": ["receipt:A1"], "failure_semantics": "DIRECT_CONTRACT"}
                ],
            },
            {
                "step": 2,
                "action_id": "A2",
                "domain": "CODE",
                "reads": ["x"],
                "writes": ["terminal"],
                "depends_on": ["A1"],
                "dependency_composition": "SEQUENTIAL",
                "checks": [
                    {"kind": "INVARIANT", "id": "A2:I", "pass": False, "evidence": ["receipt:A2"], "failure_semantics": "DERIVED_UPSTREAM"}
                ],
            },
        ],
        "terminal_failed_resources": ["terminal"],
    }


for surface in surfaces:
    g = good_case(surface)
    if module.normalize_case(g).get("status") != "PASS":
        errors.append("VALID_CASE_REJECTED:" + surface)

    missing = good_case(surface)
    del missing["trajectory"][0]["checks"][0]["failure_semantics"]
    out = module.normalize_case(missing)
    if out.get("status") != "FAIL_CLOSED" or not str(out.get("reason")).startswith("FAILURE_SEMANTICS_UNBOUND"):
        errors.append("MISSING_SEMANTICS_NOT_FAIL_CLOSED:" + surface)

    empty_receipt = good_case(surface)
    empty_receipt["trajectory"][0]["checks"][0]["evidence"] = []
    out = module.normalize_case(empty_receipt)
    if out.get("status") != "FAIL_CLOSED" or not str(out.get("reason")).startswith("FAILED_CHECK_RECEIPTS_EMPTY"):
        errors.append("EMPTY_RECEIPT_NOT_FAIL_CLOSED:" + surface)

    one_class = good_case(surface)
    one_class["trajectory"][1]["checks"][0]["pass"] = True
    out = module.normalize_case(one_class)
    if out.get("status") != "FAIL_CLOSED" or out.get("reason") != "DERIVED_UPSTREAM_NOT_PRESENT":
        errors.append("ONE_CLASS_NOT_FAIL_CLOSED:" + surface)

result = {
    "schema": "PROJECT_BRAIN_P1_SHARED_BATCH_FREEZE_PUBLIC_RUNNER_VERDICT_V1",
    "status": "PASS__EXACT_ONE_BATCH_PRECASE_FREEZE_AND_NO_GUESS_NORMALIZER" if not errors else "FAIL_CLOSED",
    "errors": sorted(set(errors)),
    "exact_freeze_blob": blob_sha(ROOT / "freeze.json"),
    "exact_normalizer_blob": blob_sha(normalizer_path),
    "minimum_new_reality_units": 1,
    "surface_count": len(surfaces),
    "no_failure_semantics_default": "NORMALIZER_HAS_DEFAULT_FAILURE_SEMANTICS" not in errors,
    "fresh_reality_consumed": 0,
    "execution_authority": False,
    "capability_credit_delta": 0,
    "family_credit_delta": 0,
}
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if not errors else 1)
