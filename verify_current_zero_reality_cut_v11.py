#!/usr/bin/env python3
import json, subprocess, urllib.request
CUT="fixtures/current_zero_reality_cut_v11.json"
DELTA="fixtures/root2_osworld_hle_delta_v1.json"

def load(p):
    with open(p,encoding="utf-8") as f:
        return json.load(f)

def blob(p):
    return subprocess.check_output(["git","hash-object",p],text=True).strip()

def run_ok(run_id):
    req=urllib.request.Request(
        f"https://api.github.com/repos/moxnixmdj/verification-capsule-runner/actions/runs/{run_id}",
        headers={"Accept":"application/vnd.github+json","User-Agent":"Project-Brain-V11-Verifier"}
    )
    with urllib.request.urlopen(req,timeout=30) as r:
        x=json.load(r)
    assert x["status"]=="completed"
    assert x["conclusion"]=="success"

cut=load(CUT)
delta=load(DELTA)
assert blob(CUT)=="452c6f2231fbe93fd54e3299eb54d7103567a08a"
assert blob(DELTA)=="0a00e8b0d4f13d3f7de9566a3b7147be754ac852"
assert cut["schema"]=="PROJECT_BRAIN_CURRENT_ZERO_REALITY_MINIMUM_CUT_V11"
s=cut["exact_state"]
assert (s["accepted_families"],s["open_families"],s["proved_atomic"],s["unresolved_atomic"])==(5,14,12,26)
assert s["terminal"] is False
for k in ["new_reality_units_consumed","terminal_cases_consumed","incremental_spend_usd","acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta"]:
    assert cut[k]==0
assert cut["fresh_reality_authority"] is False
assert cut["execution_authority"] is False
assert cut["promotion_authority"] is False
assert cut["authority"]["root2_osworld_hle_delta"]["git_blob_sha"]=="0a00e8b0d4f13d3f7de9566a3b7147be754ac852"

osd=delta["deltas"]["OSWORLD_2_1_PARTIAL_GE_81_8"]
assert "PINNED_VM_BOOT" in osd["removed"]
assert set(["GATED_TASK_ASSET_ACCESS","SELF_HOST_DEPENDENCIES","PROTOCOL_EQUIVALENCE","BRAIN_SCORE"]).issubset(osd["remaining"])
hled=delta["deltas"]["HLE_TOOLS_GE_67_7"]
assert "STRICT_REFERENCE_SCORER_AS_PROVED_OFFICIAL_JUDGE_LOWER_BOUND" in hled["removed"]
assert "ZERO_COST_COMPARABLE_OFFICIAL_OR_PROVED_EQUIVALENT_JUDGE" in hled["remaining"]

run_ok(37155331628)
run_ok(37155985842)
print("CURRENT_ZERO_REALITY_MINIMUM_CUT_V11_VERIFIED")
