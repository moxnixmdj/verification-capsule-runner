#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, pathlib

ROOT=pathlib.Path(__file__).resolve().parent
PRIOR=ROOT/"subject/livebench_retry_v5_activation_20261004/root.json"
CURRENT=ROOT/"subject/root2_decision_only_root_projection_v1/TERMINAL_ROOT_CAUSE_STATE_V1.json"

PRIOR_BLOB="f1c96d7924341e9c95a390cccf90d74109f10189"
CURRENT_BLOB="822d7a0e64b2e919a873526d111e7202c40e1f5b"

def blob(p):
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def diff(a,b,path=""):
    out=[]
    if not isinstance(a,dict) or not isinstance(b,dict):
        if a!=b: out.append(path)
        return out
    for k in sorted(set(a)|set(b)):
        p=f"{path}.{k}" if path else k
        if k not in a or k not in b:
            out.append(p)
        else:
            out.extend(diff(a[k],b[k],p))
    return out

assert blob(PRIOR)==PRIOR_BLOB
assert blob(CURRENT)==CURRENT_BLOB
a=json.loads(PRIOR.read_text())
b=json.loads(CURRENT.read_text())

assert a["current_acceptance"]==b["current_acceptance"]
assert a["current_acceptance"]=={
 "accepted_families":5,"open_families":14,"proved_atomic":12,
 "unresolved_atomic":26,"total_families":19,"total_atomic":38,"terminal":False
}
assert a["current_residual_root_partition"]==b["current_residual_root_partition"]
assert "LIVEBENCH_IF_GE_65_7" in b["current_residual_root_partition"]["root2_only"]
assert b["current_residual_root_partition"]["root1_positive_gap_count"]==0
assert a["root3_current_execution_state"]==b["root3_current_execution_state"]
assert a["accounting"]==b["accounting"]

paths=diff(a,b)
assert paths==[
 "scheduler_policy.arena_public_semantics_truth_repair",
 "scheduler_policy.root2_decision_only_evaluation",
], paths

arena=b["scheduler_policy"]["arena_public_semantics_truth_repair"]
assert arena["scheduling_authority"] is True
assert arena["execution_authority"] is False
assert arena["promotion_authority"] is False
assert arena["fresh_reality_authority"] is False

dec=b["scheduler_policy"]["root2_decision_only_evaluation"]
assert dec["scheduling_authority"] is True
assert dec["decision_certificate_compilation"] is True
assert dec["execution_authority"] is False
assert dec["promotion_authority"] is False
assert dec["fresh_reality_authority"] is False
assert dec["acceptance_credit_delta"]==0

print(json.dumps({
 "schema":"PROJECT_BRAIN_LIVEBENCH_V5_ROOT_COMPATIBLE_REBIND_PUBLIC_RUNNER_VERIFICATION_20261004_V1",
 "status":"PASS__EXACT_ROOT_DELTA_SCHEDULING_ONLY__LIVEBENCH_SEMANTICS_UNCHANGED__ZERO_CREDIT",
 "prior_root_blob":PRIOR_BLOB,
 "current_root_blob":CURRENT_BLOB,
 "exact_delta_paths":paths,
 "livebench_predicate":"LIVEBENCH_IF_GE_65_7",
 "livebench_root_class":"ROOT2_ONLY",
 "accepted_families":5,
 "proved_atomic":12,
 "unresolved_atomic":26,
 "execution_authority_created":False,
 "fresh_reality_authority_created":False,
 "promotion_authority_created":False,
 "acceptance_credit_delta":0,
},sort_keys=True))
