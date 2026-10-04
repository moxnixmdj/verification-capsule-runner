#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT=pathlib.Path(__file__).resolve().parent
SUB=ROOT/"subject/one_use_benchmark_atomic_claim_v1"
EXPECTED={
    SUB/"canonical/runtime/atomic_one_use_execution_claim_v1.py":"9e4bdb4cd4e73292499fdd3b6fe8219349509e18",
    SUB/"canonical/tests/test_atomic_one_use_execution_claim_v1.py":"6fadec28875491ee4e75285aef7b6d1ec6388958",
    SUB/"canonical/governance/ONE_USE_BENCHMARK_REPLAY_ATOMIC_CLAIM_POLICY_V1.json":"eb9127b4196b347aec0ce7eb3e61b96aac183342",
    SUB/"canonical/governance/LIVEBENCH_V6_DUPLICATE_REPLAY_CONCURRENCY_RECONCILIATION_V1.json":"5139529097ffdb0cf5231b4626bf3e3e639b6ac2",
}

def git_blob_sha(p:pathlib.Path)->str:
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

for p,want in EXPECTED.items():
    if not p.is_file():
        raise SystemExit("MISSING_SUBJECT:"+str(p))
    got=git_blob_sha(p)
    if got!=want:
        raise SystemExit("SUBJECT_BLOB_DRIFT:"+str(p)+":"+got+":"+want)

env=os.environ.copy()
env["PYTHONPATH"]=str(SUB)
cp=subprocess.run(
    [sys.executable,"-m","unittest","-v","canonical.tests.test_atomic_one_use_execution_claim_v1"],
    cwd=SUB,env=env,text=True,capture_output=True
)
print(cp.stdout,end="")
print(cp.stderr,end="")
if cp.returncode!=0:
    raise SystemExit("COPIED_SUBJECT_TESTS_FAILED")

sys.path.insert(0,str(SUB))
from canonical.runtime.atomic_one_use_execution_claim_v1 import (
    INPUT_SCHEMA,
    execution_lease_digest,
    expected_claim_ref,
    verify_atomic_one_use_execution_claim,
)

policy=json.loads((SUB/"canonical/governance/ONE_USE_BENCHMARK_REPLAY_ATOMIC_CLAIM_POLICY_V1.json").read_text())
recon=json.loads((SUB/"canonical/governance/LIVEBENCH_V6_DUPLICATE_REPLAY_CONCURRENCY_RECONCILIATION_V1.json").read_text())

assert recon["ordering_proof"]["first_terminal_result_precedes_second_prelaunch"] is True
assert recon["authoritative_first_epoch"]["workflow_run_id"]==37191763314
assert recon["non_authoritative_duplicate_epoch"]["workflow_run_id"]==37191913947
assert recon["non_authoritative_duplicate_epoch"]["result"]["new_case_exposure_count"]==0
assert recon["additional_v6_replay_authority"] is False
assert recon["root_cause"]["class"]=="CONTROL_PLANE_LINEARIZATION_FAILURE"
assert policy["claim_protocol"]["absence_precheck"]=="FORBIDDEN"
assert policy["accounting"]["acceptance_credit_delta"]==0
assert policy["execution_authority"] is False

token=os.environ.get("GH_TOKEN")
repo=os.environ.get("GITHUB_REPOSITORY")
target_sha=os.environ.get("GITHUB_SHA")
if not token or not repo or not target_sha:
    raise SystemExit("GITHUB_ENV_REQUIRED")

lease={
  "activation":{"path":"verification/activation.json","git_blob_sha":"a"*40},
  "candidate":{"path":"verification/candidate.json","git_blob_sha":"b"*40},
  "scope":{
    "benchmark_id":"VERIFIER_ATOMIC_ONE_USE_V1",
    "target_predicate":"VERIFIER_ONLY",
    "execution_kind":"DISPOSABLE_REAL_GIT_REF_TRANSACTION",
    "scope_id":"EXACT_SUBJECT_"+EXPECTED[SUB/"canonical/runtime/atomic_one_use_execution_claim_v1.py"],
    "max_case_count":0,
    "new_case_exposure":False,
  },
}
digest=execution_lease_digest(lease)
claim_ref=expected_claim_ref(digest)

api="https://api.github.com/repos/"+repo
headers={
    "Authorization":"Bearer "+token,
    "Accept":"application/vnd.github+json",
    "X-GitHub-Api-Version":"2022-11-28",
    "Content-Type":"application/json",
}

def request(method,url,payload=None):
    data=None if payload is None else json.dumps(payload).encode()
    req=urllib.request.Request(url,data=data,method=method,headers=headers)
    try:
        with urllib.request.urlopen(req,timeout=30) as r:
            body=r.read()
            return r.status,json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        body=e.read()
        try: parsed=json.loads(body) if body else {}
        except Exception: parsed={"raw":body.decode(errors="replace")}
        return e.code,parsed

# Cleanup any stale verifier-only ref from an aborted prior verification. This is
# not a production lease and uses a verifier-only benchmark id/scope.
delete_path=urllib.parse.quote(claim_ref.removeprefix("refs/"),safe="/")
request("DELETE",api+"/git/refs/"+delete_path)

status1,body1=request("POST",api+"/git/refs",{"ref":claim_ref,"sha":target_sha})
if status1!=201:
    raise SystemExit("REAL_ATOMIC_FIRST_CREATE_NOT_201:"+str(status1))
status2,body2=request("POST",api+"/git/refs",{"ref":claim_ref,"sha":target_sha})
if status2!=422:
    raise SystemExit("REAL_ATOMIC_DUPLICATE_NOT_422:"+str(status2))

first_receipt={
    "lease_digest_sha256":digest,
    "claim_ref":claim_ref,
    "create_http_status":status1,
    "reference_created":True,
    "response_ref":body1.get("ref"),
    "response_object_sha":(body1.get("object") or {}).get("sha"),
    "expected_target_sha":target_sha,
    "claim_uniqueness_source":"ATOMIC_CREATE_RESPONSE",
    "claim_ref_absence_precheck_performed":False,
    "case_read_before_claim":False,
    "execution_started_before_claim":False,
    "evaluation_output_exists_before_claim":False,
}
out1=verify_atomic_one_use_execution_claim({
    "schema":INPUT_SCHEMA,"lease":lease,"claim_receipt":first_receipt
})
if out1.get("status")!="PASS__ATOMIC_ONE_USE_EXECUTION_CLAIM__EXACT_LEASE_ONLY":
    raise SystemExit("RUNTIME_REJECTED_REAL_FIRST_CREATE:"+json.dumps(out1,sort_keys=True))

duplicate_receipt=dict(first_receipt)
duplicate_receipt.update({
    "create_http_status":status2,
    "reference_created":False,
    "response_ref":None,
    "response_object_sha":None,
})
out2=verify_atomic_one_use_execution_claim({
    "schema":INPUT_SCHEMA,"lease":lease,"claim_receipt":duplicate_receipt
})
if out2.get("status")!="FAIL_CLOSED" or out2.get("execution_authority") is not False:
    raise SystemExit("RUNTIME_ACCEPTED_DUPLICATE_CREATE:"+json.dumps(out2,sort_keys=True))

cleanup_status,_=request("DELETE",api+"/git/refs/"+delete_path)
if cleanup_status not in {204,404}:
    raise SystemExit("TEST_REF_CLEANUP_FAILED:"+str(cleanup_status))

print(json.dumps({
  "schema":"PROJECT_BRAIN_ONE_USE_BENCHMARK_ATOMIC_CLAIM_PUBLIC_RUNNER_VERIFICATION_20261004_V1",
  "status":"PASS__EXACT_SUBJECT_BLOBS__UNIT_TESTS__REAL_GIT_REF_201_THEN_422__DUPLICATE_REPLAY_RECONCILED__ZERO_CREDIT",
  "subject_blobs":{str(k.relative_to(ROOT)):v for k,v in EXPECTED.items()},
  "copied_subject_tests":"PASS",
  "real_git_ref_transaction":{
    "first_create_status":status1,
    "duplicate_create_status":status2,
    "claim_ref":claim_ref,
    "cleanup_status":cleanup_status,
  },
  "verified":{
    "first_create_grants_exact_lease_only":True,
    "duplicate_create_fails_closed":True,
    "absence_precheck_forbidden":True,
    "v6_second_replay_non_authoritative":True,
    "v6_no_new_case_exposure_from_duplicate":True,
    "additional_v6_replay_authority":False,
  },
  "accounting":{
    "terminal_cases_consumed":0,
    "incremental_spend_usd":0,
    "acceptance_credit_delta":0,
    "family_credit_delta":0,
    "capability_credit_delta":0,
    "ownership_credit_delta":0
  },
  "execution_authority":False,
  "fresh_reality_authority":False,
  "promotion_authority":False
},sort_keys=True))
