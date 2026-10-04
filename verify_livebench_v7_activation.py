#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parent
ACT=ROOT/"subject/livebench_v7_activation_20261004/activation.json"
CAND=ROOT/"subject/livebench_v7_activation_20261004/candidate.json"
RSTATE=ROOT/"subject/livebench_v7_activation_20261004/root.json"
DIAG=ROOT/"diagnose_livebench_replay72_v7_sanitized.py"
CLS=ROOT/"livebench_v7_sanitized_classifier.py"
BASE=ROOT/"execute_livebench_if_replay72_v4_candidate.py"
EXPECTED_ACT="16e0bf4ab46d76e0e07fac90d6e4a50dcdf15508"
EXPECTED_CAND="26bd7a5ef24b85b1d57a38d6656876affa036e69"
EXPECTED_ROOT="822d7a0e64b2e919a873526d111e7202c40e1f5b"
EXPECTED_DIAG="e9a5a5937b19e76bf04444c288e3a75113874ed7"
EXPECTED_CLS="44df7313c83914204299953dda81900fae85ab68"
EXPECTED_BASE="2a57ce896ddbd6819246aab8b44d17a00f36b61e"
def blob(p):
 b=p.read_bytes();return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
assert blob(ACT)==EXPECTED_ACT
assert blob(CAND)==EXPECTED_CAND
assert blob(RSTATE)==EXPECTED_ROOT
assert blob(DIAG)==EXPECTED_DIAG
assert blob(CLS)==EXPECTED_CLS
assert blob(BASE)==EXPECTED_BASE
a=json.loads(ACT.read_text());c=json.loads(CAND.read_text());r=json.loads(RSTATE.read_text())
assert a["active"] is True and a["target_predicate"]=="LIVEBENCH_IF_GE_65_7"
b=a["exact_binding"]
assert b["candidate_git_blob_sha"]==EXPECTED_CAND
assert b["diagnostic_git_blob_sha"]==EXPECTED_DIAG
assert b["classifier_git_blob_sha"]==EXPECTED_CLS
assert b["base_executor_git_blob_sha"]==EXPECTED_BASE
assert b["root_git_blob_sha"]==EXPECTED_ROOT
assert b["replay_case_count"]==72
auth=a["authority"]
assert auth["execution"] is True and auth["replay_existing_prefix"] is True
assert auth["new_case_exposure"] is False and auth["global_fresh_reality"] is False
assert auth["promotion"] is False and auth["acceptance_credit"] is False
assert c["replay_scope"]["exact_already_exposed_prefix_count"]==72
assert c["replay_scope"]["new_case_exposure"] is False
assert c["output_contract"]["forbidden"]==["CASE_IDS","PROMPT_TEXT","RESPONSE_TEXT","RAW_EXCEPTION_TEXT","CASE_TO_CLASS_MAPPING","CASE_SPECIFIC_REPAIR_HINTS"]
assert r["current_acceptance"]["terminal"] is False
assert r["current_residual_root_partition"]["root1_positive_gap_count"]==0
assert "LIVEBENCH_IF_GE_65_7" in r["current_residual_root_partition"]["root2_only"]
print(json.dumps({
 "status":"INDEPENDENT_PUBLIC_RUNNER_PASS",
 "activation_git_blob_sha":EXPECTED_ACT,
 "candidate_git_blob_sha":EXPECTED_CAND,
 "root_git_blob_sha":EXPECTED_ROOT,
 "diagnostic_git_blob_sha":EXPECTED_DIAG,
 "classifier_git_blob_sha":EXPECTED_CLS,
 "base_executor_git_blob_sha":EXPECTED_BASE,
 "execution_authority":"REPLAY_EXISTING_72_PREFIX_DIAGNOSTIC_ONLY",
 "new_case_exposure_authorized":False,
 "output_contract_verified":True,
 "terminal_cases_consumed":0,
 "acceptance_credit_delta":0
},sort_keys=True))
