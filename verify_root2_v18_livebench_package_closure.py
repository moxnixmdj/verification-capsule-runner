#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, pathlib

ROOT=pathlib.Path(__file__).resolve().parent
S=ROOT/"subject"/"root2_v18_livebench_package_closure"

EXPECTED={
 "ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V17.json":"8c1325dd652b65a7d5c24e041ac06556a84f569c",
 "ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V18.json":"57d5ee650d4ee250db455d5818899f32aa304918",
 "LIVEBENCH_FROZEN_RUNTIME_PACKAGE_CLOSURE_RECONCILIATION_V1.json":"0c885959a82dc3cbdc061b2c59d85b730ea2b648",
}
def blob(path):
 data=path.read_bytes()
 return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
for name,want in EXPECTED.items():
 p=S/name
 assert p.is_file(), name
 assert blob(p)==want,(name,blob(p),want)

v17=json.loads((S/"ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V17.json").read_text())
v18=json.loads((S/"ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V18.json").read_text())
rec=json.loads((S/"LIVEBENCH_FROZEN_RUNTIME_PACKAGE_CLOSURE_RECONCILIATION_V1.json").read_text())

assert v18["schema"]=="PROJECT_BRAIN_ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V18"
assert v18["supersedes_for_scheduling_if_verified"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V17.json"
assert v18["exact_state"]==v17["exact_state"]
assert v18["exact_state"]["accepted_families"]==5
assert v18["exact_state"]["proved_atomic"]==12
assert v18["exact_state"]["unresolved_atomic"]==26
assert v18["exact_state"]["root1_positive_gap_count"]==0

for key in ("execution_authority","promotion_authority","fresh_reality_authority"):
 assert v18[key] is False,key
assert v18["accounting"]["incremental_spend_usd"]==0
assert v18["accounting"]["new_reality_units_consumed"]==0
assert v18["accounting"]["acceptance_credit_delta"]==0
assert v18["accounting"]["family_credit_delta"]==0
assert v18["accounting"]["capability_credit_delta"]==0
assert v18["accounting"]["ownership_credit_delta"]==0

lb=v18["source_bindings"]["livebench_frozen_runtime_package_closure"]
assert lb["git_blob_sha"]==EXPECTED["LIVEBENCH_FROZEN_RUNTIME_PACKAGE_CLOSURE_RECONCILIATION_V1.json"]
assert lb["verifier_repository"]=="moxnixmdj/verification-capsule-runner"
assert lb["verifier_pull_request"]==1780
assert lb["verifier_merge_commit"]=="7b8ff34653e04e0aa4259e25b03ac9cc817ff8b5"
assert lb["workflow_run_id"]==37190619486
assert lb["workflow_job_id"]==111401825957

assert rec["proved"]["transitive_package_loader_closure"] is True
assert rec["proved"]["terminal_case_content_read"] is False
assert rec["proved"]["terminal_cases_consumed"]==0
assert rec["proved"]["external_frontier_model_calls"]==0
assert rec["proved"]["incremental_spend_usd"]==0
assert rec["separate_synthetic_diagnostic"]["status"]=="BLOCKED_AFTER_PACKAGE_CLOSURE"
assert rec["separate_synthetic_diagnostic"]["compile_blocker"]=="GOAL_COMPILATION_NO_VERIFIED_CAPABILITY_MATCH"
assert rec["separate_synthetic_diagnostic"]["downstream_blocker"]=="CAPABILITY_ACQUISITION_REQUIRED"

deltas=[d for d in v18["projection_deltas"] if d.get("target")=="LIVEBENCH_IF_GE_65_7"]
assert len(deltas)==len([d for d in v17["projection_deltas"] if d.get("target")=="LIVEBENCH_IF_GE_65_7"])+1
new=deltas[-1]
assert new["deletion"]=="EXACT_TRANSITIVE_FROZEN_RUNTIME_DEPENDENCY_CLOSURE_AS_OPEN_BLOCKER"
assert "SYNTHETIC_ZERO_CASE_REACHES_GENERAL_INSTRUCTION_ROUTING_BLOCKER" in new["to"]

route=v18["livebench_if_isolation_route"]
assert route["public_inference_capsule"].startswith("PACKAGE_CLOSURE_PASS")
assert any("GENERAL_MODEL_INDEPENDENT_INSTRUCTION_ROUTING" in x for x in route["remaining_zero_reality"])
assert "SAME_SYNTHETIC_ZERO_CASE_INFERENCE_PASS" in route["remaining_zero_reality"]
assert any("NO_LIVEBENCH_SYNTHETIC_OR_TERMINAL_TASK_SPECIAL_CASE_REPAIR"==x for x in v18["hard_rules"])
assert any("NO_ROOT1_REOPEN_FROM_SYNTHETIC_ZERO_CASE_PREFLIGHT_ALONE"==x for x in v18["hard_rules"])

# Ensure V18 does not silently mutate unrelated top-level exact state/accounting authority.
for key in ("tb4_carrier_portfolio","finance_agent_v2_zero_spend_route","finance_agent_v2_dual_route"):
 assert v18.get(key)==v17.get(key),key

print("PASS: Root2 V18 deletes only verified LiveBench package-closure blocker, preserves synthetic routing residual, zero credit/authority")
