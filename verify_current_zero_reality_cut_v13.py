#!/usr/bin/env python3
import json, subprocess, urllib.request

P="fixtures/current_zero_reality_cut_v13.json"
EXPECTED_BLOB="0e90450aaaad27714b272ad2b143ba23dd8f3dc0"

def load(p):
    with open(p,encoding="utf-8") as f: return json.load(f)

def blob(p):
    return subprocess.check_output(["git","hash-object",p],text=True).strip()

def run_ok(run_id):
    req=urllib.request.Request(
        f"https://api.github.com/repos/moxnixmdj/verification-capsule-runner/actions/runs/{run_id}",
        headers={"Accept":"application/vnd.github+json","User-Agent":"Project-Brain-V13-Composition-Verifier"}
    )
    with urllib.request.urlopen(req,timeout=30) as r:
        x=json.load(r)
    assert x["status"]=="completed", x
    assert x["conclusion"]=="success", x

x=load(P)
assert blob(P)==EXPECTED_BLOB
assert x["schema"]=="PROJECT_BRAIN_CURRENT_ZERO_REALITY_MINIMUM_CUT_V13"
s=x["exact_state"]
assert (s["accepted_families"],s["open_families"],s["proved_atomic"],s["unresolved_atomic"])==(5,14,12,26)
assert s["terminal"] is False
assert s["root1_positive_gap_count"]==0

for k in ["new_reality_units_consumed","terminal_cases_consumed","incremental_spend_usd","acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta"]:
    assert x[k]==0
assert x["execution_authority"] is False
assert x["promotion_authority"] is False
assert x["fresh_reality_authority"] is False

pub=x["authority"]["root2_public_account_boundary_delta"]
assert pub["git_blob_sha"]=="e5e49002a1a3635062cdb580d5a85f5f4e0734a4"
assert pub["independent_run"]["workflow_run_id"]==37157621217
assert pub["independent_run"]["workflow_job_id"]==111304219083
assert pub["independent_run"]["conclusion"]=="success"
run_ok(37157621217)

fin=x["authority"]["finance_weighted_bound"]
assert fin["theorem"]["git_blob_sha"]=="c2af9c7c4b06ee7e5bec7963dd062a84f802fce2"
assert fin["verification"]["git_blob_sha"]=="6b948a574f0889923b945b7ec790e3e9b280a915"
assert fin["verification"]["workflow_run_id"]==37157285340
assert fin["verification"]["workflow_job_id"]==111303179578
run_ok(37157285340)

classes={z["class"]:z for z in x["exhausted_or_waiting"]}
assert classes["CHARTOGRAPHY_GENERIC_PUBLIC_QUOTA_SEARCH"]["state"]=="CLOSED_TO_ACCOUNT_BOUND_STATE"
assert classes["OSWORLD_V21_GENERIC_TASK_GATE_AND_COMPONENT_IDENTITY_SEARCH"]["state"]=="DISCHARGED"
assert classes["FINANCE_SIX_COMPONENTWISE_NONINFERIORITY_AS_MANDATORY_ROUTE"]["state"]=="DOMINATED"

work={z["surface"]:z["work"] for z in x["active_zero_reality_work"]}
assert "1000_TOTAL_JUDGE_CALLS" in work["Chartography with tools"]
assert "TASK_GATE_PUBLICLY_AUTO_APPROVED" in work["OSWorld 2.1 partial"]
assert "WEIGHTED_LOWER_BOUND" in work["Finance & Accounting Index"]
assert "DO_NOT_REQUIRE_ALL_SIX_COMPONENTS_INDIVIDUALLY_GE_OPUS" in work["Finance & Accounting Index"]

deltas=[d["target"] for d in x["completed_zero_reality_deltas"][-3:]]
assert deltas==["CHARTOGRAPHY_TOOLS_GE_89","OSWORLD_2_1_PARTIAL_GE_81_8","FINANCE_ACCOUNTING_INDEX_GE_61"]

print("CURRENT_ZERO_REALITY_MINIMUM_CUT_V13_COMPOSITION_VERIFIED")
