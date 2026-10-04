#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, pathlib
ROOT=pathlib.Path(__file__).resolve().parent
SUB=ROOT/"subject"/"livebench_root1_reclassification_20261004"
EXPECTED={
"reclassification.json":"eef18a73b23db53082b934976bcbd05cab9c5684",
"forced_fail_binding.json":"98659983c43ac37508177b4003a08cfd5d1e9447",
"root_state.json":"36ac53134b123cfed7e63c31a871a30f9b4579e4"}
def blob(p):
 b=p.read_bytes(); return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def load(n):
 p=SUB/n
 if not p.is_file() or blob(p)!=EXPECTED[n]: raise SystemExit("FAIL_CLOSED:BLOB_MISMATCH:"+n)
 return json.loads(p.read_text())
r=load("reclassification.json"); f=load("forced_fail_binding.json"); s=load("root_state.json")
pid="LIVEBENCH_IF_GE_65_7"
if r.get("target_predicate")!=pid or f.get("target_predicate")!=pid: raise SystemExit("FAIL_CLOSED:TARGET")
if f.get("frozen_candidate")!=r.get("frozen_candidate"): raise SystemExit("FAIL_CLOSED:CANDIDATE_DRIFT")
mc=f.get("mathematical_certificate") or {}
if not (mc.get("population_count")==200 and mc.get("observed_zero_score_cases")==72 and mc.get("unseen_cases")==128 and mc.get("maximum_possible_remaining_score_mass")==128): raise SystemExit("FAIL_CLOSED:MASS")
if not (128/200*100==64.0 and 64.0<65.7): raise SystemExit("FAIL_CLOSED:ARITHMETIC")
iv=f.get("independent_verification") or {}
if iv.get("predicate_false_for_frozen_candidate") is not True or iv.get("additional_case_exposure_needed") is not False: raise SystemExit("FAIL_CLOSED:FAIL_BINDING")
part=s.get("current_residual_root_partition") or {}
if pid not in (part.get("root2_only") or []): raise SystemExit("FAIL_CLOSED:PRIOR_ROOT2_MEMBERSHIP")
if part.get("root1_positive_gap_count")!=0: raise SystemExit("FAIL_CLOSED:PRIOR_ROOT1_NOT_ZERO")
tr=r.get("root_transition") or {}
if not (tr.get("root1_positive_gap") is True and tr.get("root2_local_residual") is False and tr.get("root3_local_residual") is False): raise SystemExit("FAIL_CLOSED:TRANSITION")
if (r.get("authority") or {}).get("root_state_git_blob_sha")!=EXPECTED["root_state.json"]: raise SystemExit("FAIL_CLOSED:ROOT_BINDING")
acct=r.get("accounting") or {}
for k in ("new_terminal_cases_exposed","acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta"):
 if acct.get(k)!=0: raise SystemExit("FAIL_CLOSED:ACCOUNTING:"+k)
print("PASS:LIVEBENCH_LOCAL_ROOT1_RECLASSIFICATION_INDEPENDENT_VERIFICATION")
