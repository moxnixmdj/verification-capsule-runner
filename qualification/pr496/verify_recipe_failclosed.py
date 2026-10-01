#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util, json, pathlib

ROOT=pathlib.Path(__file__).resolve().parents[2]
CAND=ROOT/"canonical/runtime/bound_capabilities/broad_objective_decompose.py"
REPORT=ROOT/"qualification/pr496/independent-report.json"
EXPECTED_BLOB="3ded762075ed222228a14877af631f1e2e6d9e4c"

def git_blob_sha(path):
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

assert git_blob_sha(CAND)==EXPECTED_BLOB,(git_blob_sha(CAND),EXPECTED_BLOB)
spec=importlib.util.spec_from_file_location("independent_pr496_candidate",CAND)
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

reject=[
 "Assess whether two values differ. Run /usr/bin/python verify_values.py",
 "Assess whether two values differ. Run customtool --verify values.json",
 "Evaluate whether two values differ. Execute /opt/tools/checker --input data.bin",
 "Assess whether two values differ. Run a verification method with python verify.py",
 "Compare two values. Execute mystery-cli --flag",
 "Determine whether values differ using https://example.com/data",
]
allow=[
 "Assess whether two measured values differ. Use authoritative evidence, choose and run a zero-cost verification method, identify limitations, and independently verify the result.",
 "Evaluate whether two regimes differ. Execute a validation procedure, and independently verify the result.",
 "Investigate whether two regimes differ. Run an independently chosen verification approach; preserve material limitations.",
 "Compare two measurements. Run an autonomously selected validation check and preserve provenance.",
 "Analyze whether two observations differ. Execute the analysis method and independently verify the result.",
]
checks=[]
for text in reject:
    out=mod.decompose(text)
    ok=out.get("status")=="UNSUPPORTED" and out.get("reason")=="OBJECTIVE_ALREADY_CONTAINS_EXPLICIT_EXECUTION_RECIPE"
    assert ok,(text,out)
    checks.append({"case":"reject","text":text,"status":"PASS"})
for text in allow:
    out=mod.decompose(text)
    assert out.get("status")=="DECOMPOSED",(text,out)
    assert out.get("model_dependency_count")==0,(text,out)
    checks.append({"case":"allow","text":text,"status":"PASS"})
report={
 "schema":"PROJECT_BRAIN_PR496_INDEPENDENT_ADVERSARIAL_QUALIFICATION_V1",
 "status":"PASS",
 "brain_pr":496,
 "candidate_blob":git_blob_sha(CAND),
 "checks":checks,
 "check_count":len(checks),
 "authoritative_red_reproduced_as_rejected":True,
 "parent_task_execution_count":0,
 "model_dependency_count":0,
 "incremental_spend_usd":0
}
REPORT.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
print("INDEPENDENT_PR496_RECIPE_FAILCLOSED_PASS")
print(json.dumps(report,sort_keys=True))
