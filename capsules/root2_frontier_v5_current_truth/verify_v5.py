#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def blob_sha(path:Path)->str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

m=json.loads((ROOT/"EXPECTED_BRAIN_BLOBS.json").read_text())
for rel,expected in m["exact_brain_blobs"].items():
    got=blob_sha(ROOT/rel)
    assert got==expected,(rel,got,expected)

def load(rel):
    return json.loads((ROOT/rel).read_text())

v5=load("canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V5.json")
v4=load("canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V4.json")
circle=load("canonical/governance/TB4_CIRCLECI_FREE_XLARGE_CONTRADICTION_RECONCILIATION_20261004_V1.json")
finance=load("canonical/governance/FINANCE_AGENT_V2_PUBLIC_RUNNER_ROUTE_RECONCILIATION_20261004_V1.json")
component=load("canonical/verification/ROOT2_V5_COMPONENT_TRUTH_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json")
intent=load("canonical/action_intents/2026-10-04_ROOT2_FRONTIER_V5_CURRENT_MAIN_TRUTH_REPAIR_V1.json")

assert v5["schema"]=="PROJECT_BRAIN_ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V5"
assert v5["supersedes_for_scheduling_if_verified"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V4.json"
assert v5["source_bindings"]["prior_frontier_v4"]["git_blob_sha"]=="8c90a1dc4903f9b895788ff2864822d6ebc26ac9"
assert v5["source_bindings"]["component_verification"]["git_blob_sha"]=="0f0e8632425e32a1f446291b5536843b07545255"
assert v5["source_bindings"]["circleci_truth_repair"]["git_blob_sha"]=="0c5d16da02e7a71c5583f7c1a743adf389fc47b1"
assert v5["source_bindings"]["finance_agent_v2_route"]["git_blob_sha"]=="126ff389982aab89f810388b1adbe402c25a7a59"

state=v5["exact_state"]
assert state=={
 "accepted_families":5,
 "open_families":14,
 "proved_atomic":12,
 "unresolved_atomic":26,
 "root1_positive_gap_count":0,
 "root2_only_count":16,
 "root3_only_count":7,
 "root2_and_root3_count":3,
 "root2_touching_predicates":19
}

deltas={x["target"]:x for x in v5["projection_deltas"]}
assert "CODING_TB4_GE_66_4" in deltas
assert "FINANCE_AGENT_V2_GE_58_59" in deltas
assert deltas["CODING_TB4_GE_66_4"]["deletion"]=="CIRCLECI_FREE_XLARGE_GEN2_ROUTE"
assert "VALS_GATED_PLATFORM_EXACT_SUITE_ID" in deltas["FINANCE_AGENT_V2_GE_58_59"]["to"]

providers=[x["provider"] for x in v5["tb4_carrier_portfolio"]["candidates"]]
assert providers==["Buildkite"],providers
deleted={x["provider"] for x in v5["tb4_carrier_portfolio"]["deleted"]}
assert deleted=={"CircleCI"}
assert not any("CIRCLECI_FREE_PLAN_ACCOUNT" in x for x in v5["runnable_zero_reality"])
assert "FINANCE_AGENT_V2_VALS_PLATFORM_APPROVAL_EXACT_SUITE_ID_CUSTOM_HARNESS_AND_ZERO_COST_TOOL_DEPENDENCY_PREFLIGHT" in v5["runnable_zero_reality"]

assert circle["conclusion"]["current_circleci_free_xlarge_route_killed"] is True
assert circle["conclusion"]["current_circleci_free_xlarge_route_killed"] is True
assert circle["conclusion"]["documented_free_route_meets_tb4_8cpu_envelope"] is False

assert finance["route_reduction"]["owner_run_receipt_remains_valid_alternative"] is True
assert "PUBLIC_RUNNER_EXISTS" in finance["proved_by_first_party_readme"]
assert "CUSTOM_MODEL_OR_HARNESS_CAN_BE_BOUND_VIA_GET_CUSTOM_MODEL" in finance["proved_by_first_party_readme"]
assert "USER_CURRENTLY_HAS_VALS_PLATFORM_APPROVAL" in finance["not_proved"]
assert "BRAIN_SCORE_GE_58_59" in finance["not_proved"]

assert component["independent_verifier"]["conclusion"]=="success"
assert component["verified"]["circleci_current_documented_free_route_meets_tb4_8cpu_envelope"] is False
assert component["verified"]["vals_public_runner_exists"] is True
assert component["verified"]["finance_agent_v2_brain_score_proved"] is False
assert component["verified"]["acceptance_counts_unchanged"] is True
assert component["verified"]["zero_terminal_credit_preserved"] is True

assert intent["canonical_base_commit"]=="6405c322026a21896c3fcbc2cb88e0244773145c"
assert intent["accounting"]["acceptance_credit_delta"]==0

for obj in (v5,circle,finance,component,intent):
    if "execution_authority" in obj: assert obj["execution_authority"] is False
    if "promotion_authority" in obj: assert obj["promotion_authority"] is False
    if "fresh_reality_authority" in obj: assert obj["fresh_reality_authority"] is False
    if "accounting" in obj:
        assert obj["accounting"]["incremental_spend_usd"]==0
        assert obj["accounting"]["terminal_cases_consumed"]==0
        assert obj["accounting"]["acceptance_credit_delta"]==0

assert v4["root2_touching_predicates"]==19
assert v4["accounting"]["acceptance_credit_delta"]==0

print(json.dumps({
 "schema":"PROJECT_BRAIN_ROOT2_FRONTIER_V5_CURRENT_TRUTH_PUBLIC_RUNNER_RESULT",
 "status":"PASS__EXACT_V5_CURRENT_MAIN_TRUTH_REPAIR__CIRCLECI_ROUTE_DELETED__VALS_RUNNER_BOUND__COUNTS_PRESERVED__ZERO_CREDIT",
 "pass":True
},sort_keys=True))
