#!/usr/bin/env python3
import hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parent
files={
"root":"subject/LIVE_TERMINAL_ROOT_CAUSE_STATE_V1.json",
"auth":"subject/ROOT2_V5_ACTIVE_CURRENT_TERMINAL_AUTHORITY_V1.json",
"bridge":"subject/ROOT2_V5_ACTIVE_MEASUREMENT_BRIDGE_CURRENT_V1.json",
"activation":"subject/ROOT2_V5_ACTIVATION_V1.json",
"frontier":"subject/ROOT2_V5_FRONTIER.json",
"receipt":"subject/ROOT2_V5_PROJECTION_VERIFICATION.json"}
expected={"root":"dea20117a3ba934cf6f5499606f04e0d0da78e15","auth":"a46484f2932ecc1ec03a1838f78af57c033f7d5f","bridge":"f98d33d98c2fa123570f1b835d28a8b61423ba6b","activation":"2d15df0daab51c5cc61c4194197da7f7fcd5a1b0","frontier":"e948022f0a4e8d91b949a5155d850d56aa137c87","receipt":"2475a8583e2ed2889c3e9e0613ae3bcf269ffc82"}
def blob(p):
 b=p.read_bytes(); return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def load(k):
 p=R/files[k]; assert blob(p)==expected[k],(k,blob(p),expected[k]); return json.loads(p.read_text())
root,auth,bridge,act,frontier,receipt=[load(k) for k in files]
V5="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V5.json"
ACT="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V5_ACTIVATION_V1.json"
VER="canonical/verification/ROOT2_V5_PROJECTION_VERIFICATION_20261004_V1.json"
assert act["subject"]["git_blob_sha"]==expected["frontier"]
assert act["verification"]["git_blob_sha"]==expected["receipt"]
assert act["authority"]["effective_scheduling_authority"] is True
assert act["authority"]["execution_authority"] is False
assert act["authority"]["promotion_authority"] is False
assert act["authority"]["fresh_reality_authority"] is False
assert receipt["verifier"]["conclusion"]=="success"
assert receipt["fresh_reality_authority"] is False
r2=root["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]
assert (r2["current_frontier_path"],r2["current_frontier_git_blob_sha"])==(V5,expected["frontier"])
assert (r2["current_frontier_activation_path"],r2["current_frontier_activation_git_blob_sha"])==(ACT,expected["activation"])
assert (r2["current_frontier_verification_path"],r2["current_frontier_verification_git_blob_sha"])==(VER,expected["receipt"])
assert r2["effective_scheduling_authority"] is True and r2["fresh_reality_authority"] is False
assert root["scheduler_policy"]["root2_effective_scheduling_authority"] is True
acc=root["current_acceptance"]; assert (acc["accepted_families"],acc["proved_atomic"],acc["unresolved_atomic"],acc["terminal"])==(5,12,26,False)
s=auth["sources"]["root2_closure_v2_current_frontier"]
assert (s["path"],s["git_blob_sha"])==(V5,expected["frontier"])
assert (s["activation"],s["activation_git_blob_sha"])==(ACT,expected["activation"])
assert (s["verification"],s["verification_git_blob_sha"])==(VER,expected["receipt"])
assert s["effective_scheduling_authority"] is True and auth["truth"]["achieved"] is False
b=bridge["root2_closure_controller_v2"]
assert (b["frontier_path"],b["frontier_git_blob_sha"])==(V5,expected["frontier"])
assert (b["frontier_activation_path"],b["frontier_activation_git_blob_sha"])==(ACT,expected["activation"])
assert (b["frontier_verification_path"],b["frontier_verification_git_blob_sha"])==(VER,expected["receipt"])
assert b["effective_scheduling_authority"] is True
assert bridge["execution_authority"] is False and bridge["promotion_authority"] is False and bridge["fresh_reality_authority"] is False
assert bridge["terminal_cases_consumed"]==0 and bridge["incremental_spend_usd"]==0 and bridge["acceptance_credit_delta"]==0
assert frontier["tb4_carrier_portfolio"]["candidates"][0]["provider"]=="Buildkite"
assert [x["provider"] for x in frontier["tb4_carrier_portfolio"]["deleted"]]==["CircleCI"]
print(json.dumps({"pass":True,"status":"PASS__THREE_WAY_V5_POINTER_ALIGNMENT__SCHEDULING_ONLY__NO_FRESH_REALITY","exact_blobs":expected},sort_keys=True))
