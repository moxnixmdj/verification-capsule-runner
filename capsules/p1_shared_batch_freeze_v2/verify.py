from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from canonical.runtime import contract_native_proof_suites as source
from canonical.runtime import p1_shared_failure_semantics_batch_v1 as batch

inp = json.loads((ROOT / "input.json").read_text(encoding="utf-8"))
freeze = json.loads((ROOT / "freeze.json").read_text(encoding="utf-8"))
errors: list[str] = []


def blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


paths = {
    "freeze": ROOT / "freeze.json",
    "normalizer": ROOT / "canonical/runtime/p1_shared_failure_semantics_normalizer_v1.py",
    "batch_harness": ROOT / "canonical/runtime/p1_shared_failure_semantics_batch_v1.py",
    "source_generator": ROOT / "canonical/runtime/contract_native_proof_suites.py",
    "candidate_v7": ROOT / "canonical/runtime/trajectory_failure_typed_ir_candidate_v7.py",
    "intervention_scorer_v6": ROOT / "canonical/runtime/trajectory_failure_typed_ir_proof_v6.py",
}
for key, path in paths.items():
    if blob_sha(path) != inp["exact_blobs"][key]:
        errors.append("BLOB_MISMATCH:" + key)

authority = freeze.get("exact_authority") or {}
declared = {
    "normalizer": (authority.get("normalizer_v1") or {}).get("git_blob_sha"),
    "batch_harness": (authority.get("batch_harness_v2") or {}).get("git_blob_sha"),
    "source_generator": (authority.get("source_generator") or {}).get("git_blob_sha"),
    "candidate_v7": (authority.get("candidate_v7") or {}).get("git_blob_sha"),
    "intervention_scorer_v6": (authority.get("intervention_scorer_v6") or {}).get("git_blob_sha"),
}
for key, sha in declared.items():
    if sha != inp["exact_blobs"][key]:
        errors.append("FREEZE_AUTHORITY_MISMATCH:" + key)

if freeze.get("selected_observation") != "P1_SHARED_SOURCE_BOUND_FAILURE_SEMANTICS_BATCH":
    errors.append("SELECTED_OBSERVATION")
if freeze.get("minimum_new_reality_units") != 1:
    errors.append("MINIMUM_REALITY")
if set(freeze.get("frozen_direct_surfaces") or []) != set(batch.SURFACES):
    errors.append("SURFACE_SET")
if freeze.get("execution_authority") is not False:
    errors.append("PREMATURE_EXECUTION_AUTHORITY")
if freeze.get("promotion_authority") is not False:
    errors.append("PREMATURE_PROMOTION_AUTHORITY")
if freeze.get("new_reality_units_consumed") != 0:
    errors.append("FREEZE_ALREADY_CONSUMED_REALITY")
if freeze.get("terminal_results_replayed") != 0:
    errors.append("TERMINAL_REPLAY")
if freeze.get("incremental_spend_usd") != 0:
    errors.append("SPEND")

src_contract = freeze.get("source_native_case_contract") or {}
if src_contract.get("semantics_binder_receives_only") != "PUBLIC_SOURCE_CASE_WITH_ORACLE_REMOVED":
    errors.append("BINDER_PUBLIC_ONLY_FREEZE")
if src_contract.get("candidate_oracle_exposure") is not False:
    errors.append("ORACLE_EXPOSURE_FREEZE")
if src_contract.get("noninterference_rule") != "MUTATING_HIDDEN_ORACLE_WHILE_HOLDING_PUBLIC_SOURCE_CASE_FIXED_MUST_NOT_CHANGE_SEMANTICS_BINDING":
    errors.append("NONINTERFERENCE_FREEZE")

contract = freeze.get("shared_batch_contract") or {}
for key in (
    "semantics_binder_hidden_oracle_input_forbidden",
    "semantics_binding_must_depend_only_on_public_source_fields",
    "runtime_cannot_self_claim_fresh_reality",
    "post_freeze_case_selection_required",
    "synthetic_v7_only_credit_forbidden",
):
    if contract.get(key) is not True:
        errors.append("CONTRACT_TRUE:" + key)

if (freeze.get("frozen_selection") or {}).get("namespace") != batch.BEACON_NAMESPACE:
    errors.append("BEACON_NAMESPACE")

neg = batch.mutation_preflight()
if neg.get("pass") is not True:
    errors.append("MUTATION_PREFLIGHT")
if neg.get("hidden_oracle_input", {}).get("reason") != "HIDDEN_ORACLE_INPUT_FORBIDDEN":
    errors.append("HIDDEN_ORACLE_NOT_REJECTED")
if neg.get("fresh_reality_units_consumed") != 0:
    errors.append("PREFLIGHT_SELF_PROMOTED")

# Metamorphic noninterference: change hidden source oracle only. Public projection
# and the complete semantics binding must remain byte-identical.
full = source.generate_case("TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001", 991337, 4)
public = source.public_task(full)
base = batch.bind_public_source_case(public, surface_id=batch.SURFACES[0], case_index=0)
mutant = copy.deepcopy(full)
mutant["_oracle"]["cause_step"] = 0
mutant["_oracle"]["repair_id"] = "repair_0"
mutant_public = source.public_task(mutant)
changed = batch.bind_public_source_case(mutant_public, surface_id=batch.SURFACES[0], case_index=0)
if base.get("status") != "PASS":
    errors.append("BASE_BIND_FAIL")
if base != changed:
    errors.append("HIDDEN_ORACLE_INFLUENCES_BINDING")
if batch.bind_public_source_case(full, surface_id=batch.SURFACES[0], case_index=0).get("reason") != "HIDDEN_ORACLE_INPUT_FORBIDDEN":
    errors.append("FULL_HIDDEN_CASE_ACCEPTED")

# Spent deterministic probes validate both scorers and all three surface tags.
spent = "spent-independent-p1-v2-preflight"
for surface in batch.SURFACES:
    for i in (0, 17, 63):
        row = batch.evaluate_one(beacon=spent, surface_id=surface, case_index=i)
        if row.get("pass") is not True:
            errors.append(f"SPENT_CASE:{surface}:{i}")
        if row.get("v7_intervention_scorer_pass") is not True:
            errors.append(f"SPENT_V7:{surface}:{i}")
        if row.get("source_native_rescue_scorer_pass") is not True:
            errors.append(f"SPENT_SOURCE:{surface}:{i}")
        if row.get("semantic_binding_basis") != "FROZEN_PUBLIC_SOURCE_STATE_AND_INVARIANT_RESULT_ONLY__HIDDEN_ORACLE_INPUT_FORBIDDEN":
            errors.append(f"SPENT_BINDING_BASIS:{surface}:{i}")

full_shape = batch.run_batch("spent-independent-full-p1-v2-shape")
if full_shape.get("pass") is not True:
    errors.append("FULL_BATCH_SHAPE_FAIL")
if full_shape.get("cases") != 192 or full_shape.get("passes") != 192:
    errors.append("FULL_BATCH_COUNTS")
if full_shape.get("fresh_reality_units_consumed") != 0:
    errors.append("FULL_BATCH_SELF_PROMOTED")
if full_shape.get("reality_unit_candidate_if_separately_authorized_and_independently_adjudicated") != 1:
    errors.append("REALITY_CANDIDATE_SHAPE")
if full_shape.get("execution_authority") is not False or full_shape.get("promotion_authority") is not False:
    errors.append("FULL_BATCH_AUTHORITY_OVERCLAIM")

result = {
    "schema": "PROJECT_BRAIN_P1_SHARED_BATCH_FREEZE_PUBLIC_RUNNER_VERDICT_V2",
    "status": "PASS__PUBLIC_ONLY_BINDER_DUAL_SCORER_FREEZE__ZERO_REALITY" if not errors else "FAIL_CLOSED",
    "errors": sorted(set(errors)),
    "exact_blobs": {k: blob_sha(v) for k, v in paths.items()},
    "surface_count": len(batch.SURFACES),
    "spent_full_batch_cases": full_shape.get("cases"),
    "spent_full_batch_passes": full_shape.get("passes"),
    "hidden_oracle_input_rejected": neg.get("hidden_oracle_input", {}).get("reason") == "HIDDEN_ORACLE_INPUT_FORBIDDEN",
    "hidden_oracle_noninterference": base == changed,
    "fresh_reality_units_consumed": 0,
    "execution_authority": False,
    "capability_credit_delta": 0,
    "family_credit_delta": 0,
    "promotion_authority": False,
}
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if not errors else 1)
