#!/usr/bin/env python3
import json, subprocess, urllib.request
P="fixtures/current_zero_reality_cut_active_pointer_v13.json"
EXPECTED="204b636b99ea26a14b2cbdbb7ce4938ef4be4842"

def blob(p):
    return subprocess.check_output(["git","hash-object",p],text=True).strip()

def run_ok(run_id):
    req=urllib.request.Request(
        f"https://api.github.com/repos/moxnixmdj/verification-capsule-runner/actions/runs/{run_id}",
        headers={"Accept":"application/vnd.github+json","User-Agent":"Project-Brain-V13-Pointer-Verifier"})
    with urllib.request.urlopen(req,timeout=30) as r:
        x=json.load(r)
    assert x["status"]=="completed"
    assert x["conclusion"]=="success"

with open(P,encoding="utf-8") as f:
    x=json.load(f)
assert blob(P)==EXPECTED
assert x["schema"]=="PROJECT_BRAIN_CURRENT_ZERO_REALITY_MINIMUM_CUT_ACTIVE_POINTER_V1"
assert x["status"]=="ACTIVE__V13_INDEPENDENT_PUBLIC_RUNNER_PASS__ZERO_CREDIT"
assert x["active_cut"]["path"]=="canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V13.json"
assert x["active_cut"]["git_blob_sha"]=="0e90450aaaad27714b272ad2b143ba23dd8f3dc0"
assert x["verification"]["git_blob_sha"]=="ed8c1731589501f87cf26194301677c77ea9ebc4"
assert x["verification"]["workflow_run_id"]==37157748058
assert x["verification"]["workflow_job_id"]==111304604528
run_ok(37157748058)
s=x["exact_state"]
assert (s["accepted_families"],s["open_families"],s["proved_atomic"],s["unresolved_atomic"])==(5,14,12,26)
assert s["terminal"] is False
for k in ["new_reality_units_consumed","terminal_cases_consumed","incremental_spend_usd","acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta"]:
    assert x[k]==0
assert x["execution_authority"] is False
assert x["promotion_authority"] is False
assert x["fresh_reality_authority"] is False
print("CURRENT_ZERO_REALITY_MINIMUM_CUT_V13_ACTIVE_POINTER_VERIFIED")
