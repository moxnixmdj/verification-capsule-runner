#!/usr/bin/env python3
import json, subprocess, urllib.request

V9="fixtures/current_zero_reality_cut_v9.json"
INV="fixtures/root2_route_inventory_v1.json"

def load(p):
    with open(p,encoding="utf-8") as f:
        return json.load(f)

def blob(p):
    return subprocess.check_output(["git","hash-object",p],text=True).strip()

def run_ok(run_id):
    req=urllib.request.Request(
        f"https://api.github.com/repos/moxnixmdj/verification-capsule-runner/actions/runs/{run_id}",
        headers={"Accept":"application/vnd.github+json","User-Agent":"Project-Brain-V9-Verifier"}
    )
    with urllib.request.urlopen(req,timeout=30) as r:
        x=json.load(r)
    assert x["status"]=="completed", x["status"]
    assert x["conclusion"]=="success", x["conclusion"]

v9=load(V9)
inv=load(INV)

assert blob(V9)=="3cad9a89e6c16e33c833b3c15ba0bdc7aa9bef2f"
assert blob(INV)=="afe631a420b547a8c4e06bf1bdf15467eee3198b"
assert v9["schema"]=="PROJECT_BRAIN_CURRENT_ZERO_REALITY_MINIMUM_CUT_V9"
s=v9["exact_state"]
assert (s["accepted_families"],s["open_families"],s["proved_atomic"],s["unresolved_atomic"])==(5,14,12,26)
assert s["terminal"] is False
for k in ["new_reality_units_consumed","terminal_cases_consumed","incremental_spend_usd","acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta"]:
    assert v9[k]==0, (k,v9[k])
assert v9["fresh_reality_authority"] is False
assert v9["promotion_authority"] is False
assert v9["execution_authority"] is False

routes={r["surface"]:r for r in inv["routes"]}
assert "PAIRWISE_ELO_OWNER_LAYER_OPEN" in routes["GDPval-AA v2.1"]["state"]
assert "OWNER_ROUTE_BOUNDARY_INDEPENDENT_PASS" in routes["FrontierCode v1.1 Main"]["state"]
assert "OWNER_ROUTE_BOUNDARY_INDEPENDENT_PASS" in routes["CursorBench 4.0"]["state"]
assert inv["new_reality_units_consumed"]==0
assert inv["acceptance_credit_delta"]==0
assert inv["fresh_reality_authority"] is False

deltas={d["target"] for d in v9["completed_zero_reality_deltas"]}
for x in ["PROWORK_GDPVAL_GE_1846","CODING_FRONTIERCODE_GE_54_4","CODING_CURSORBENCH_GE_57_8"]:
    assert x in deltas

run_ok(37154939755)
run_ok(37155077586)
print("CURRENT_ZERO_REALITY_MINIMUM_CUT_V9_VERIFIED")
