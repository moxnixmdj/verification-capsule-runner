#!/usr/bin/env python3
import json, subprocess, urllib.request

CUT="fixtures/current_zero_reality_cut_v10.json"
INV="fixtures/root2_route_inventory_v10.json"

def load(p):
    with open(p,encoding="utf-8") as f:
        return json.load(f)

def blob(p):
    return subprocess.check_output(["git","hash-object",p],text=True).strip()

def run_ok(run_id):
    req=urllib.request.Request(
        f"https://api.github.com/repos/moxnixmdj/verification-capsule-runner/actions/runs/{run_id}",
        headers={"Accept":"application/vnd.github+json","User-Agent":"Project-Brain-V10-Verifier"}
    )
    with urllib.request.urlopen(req,timeout=30) as r:
        x=json.load(r)
    assert x["status"]=="completed"
    assert x["conclusion"]=="success"

cut=load(CUT)
inv=load(INV)
assert blob(CUT)=="4fa152903a4575d18b1ce44c2ba53c40618e9338"
assert blob(INV)=="f7a6e7c4ed86076959a0c8cea4371f49c85a8d59"
assert cut["schema"]=="PROJECT_BRAIN_CURRENT_ZERO_REALITY_MINIMUM_CUT_V10"
s=cut["exact_state"]
assert (s["accepted_families"],s["open_families"],s["proved_atomic"],s["unresolved_atomic"])==(5,14,12,26)
assert s["terminal"] is False
for k in ["new_reality_units_consumed","terminal_cases_consumed","incremental_spend_usd","acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta"]:
    assert cut[k]==0
assert cut["fresh_reality_authority"] is False
assert cut["execution_authority"] is False
assert cut["promotion_authority"] is False
a=cut["authority"]
assert a["root2_routes"]["git_blob_sha"]=="f7a6e7c4ed86076959a0c8cea4371f49c85a8d59"
assert a["finance_componentwise_residual_vector"]["git_blob_sha"]=="c386e8f792170bd5a249d7e10d7d4df9d3a41c78"
assert a["finance_monotone_aggregation_theorem"]["git_blob_sha"]=="ebe67fc336d905b347790db8499b143c28d08345"
assert a["gdpval_primary_source_verification"]["git_blob_sha"]=="dee93e49f5ecf0bd2b939670931ff27886623a6c"
routes={r["surface"]:r for r in inv["routes"]}
assert "EXACT_PAIRWISE_ELO_RESULT_ROUTE_OPEN" in routes["GDPval-AA v2.1"]["state"]
finance=[x for x in cut["active_zero_reality_work"] if x["surface"]=="Finance & Accounting Index"]
assert len(finance)==1 and "SIX_COMPONENT_PREMISES_ONLY" in finance[0]["work"]
assert any(x["class"]=="FINANCE_INDEX_SEPARATE_RUN" for x in cut["exhausted_or_waiting"])
run_ok(37155624877)
run_ok(37155381249)
run_ok(37155634503)
print("CURRENT_ZERO_REALITY_MINIMUM_CUT_V10_VERIFIED")
