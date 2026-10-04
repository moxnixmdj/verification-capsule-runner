#!/usr/bin/env python3
from __future__ import annotations
import copy,hashlib,importlib.util,json,pathlib,tempfile
ROOT=pathlib.Path(__file__).resolve().parent
LAUNCH=ROOT/"launch_livebench_replay72_v6.py"
BASE=ROOT/"subject/livebench_retry_v6_20261004/root_base.json"
POINT=ROOT/"subject/livebench_retry_v6_20261004/root_point_of_use.json"
def blob(p):
 b=p.read_bytes();return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
spec=importlib.util.spec_from_file_location("launcher",LAUNCH);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
base=json.loads(BASE.read_text())
# Exact-base point-of-use must pass without terminal execution.
POINT.write_text(json.dumps(base,indent=2,sort_keys=True)+"\n")
r=mod.verify_prelaunch();assert r["compatible"] is True and r["new_case_exposure_authorized"] is False
# A pure scheduler-only addition with no authority must pass.
compatible=copy.deepcopy(base);compatible.setdefault("scheduler_policy",{})["SYNTHETIC_ZERO_AUTH_SCHEDULER_OVERLAY"]={"status":"ACTIVE","scheduling_authority":True,"execution_authority":False,"fresh_reality_authority":False,"promotion_authority":False}
POINT.write_text(json.dumps(compatible,indent=2,sort_keys=True)+"\n");assert mod.verify_prelaunch()["compatible"] is True
# Acceptance mutation must fail.
bad=copy.deepcopy(base);bad["current_acceptance"]["unresolved_atomic"]=25;POINT.write_text(json.dumps(bad,indent=2,sort_keys=True)+"\n")
try:mod.verify_prelaunch();raise AssertionError("ACCEPTANCE_MUTATION_NOT_BLOCKED")
except RuntimeError as e:assert "current_acceptance" in str(e)
# Existing scheduler-policy mutation must fail.
bad=copy.deepcopy(base);first=next(iter(bad["scheduler_policy"]));bad["scheduler_policy"][first]={"tampered":True};POINT.write_text(json.dumps(bad,indent=2,sort_keys=True)+"\n")
try:mod.verify_prelaunch();raise AssertionError("EXISTING_SCHEDULER_MUTATION_NOT_BLOCKED")
except RuntimeError as e:assert "EXISTING_SCHEDULER_POLICY_MODIFIED" in str(e)
# New authority widening must fail.
bad=copy.deepcopy(base);bad["scheduler_policy"]["SYNTHETIC_BAD"]={"execution_authority":True};POINT.write_text(json.dumps(bad,indent=2,sort_keys=True)+"\n")
try:mod.verify_prelaunch();raise AssertionError("AUTHORITY_WIDENING_NOT_BLOCKED")
except RuntimeError as e:assert "AUTHORITY_WIDENED" in str(e)
# Restore exact base snapshot for immutable verification branch state.
POINT.write_text(json.dumps(base,indent=2,sort_keys=True)+"\n")
print(json.dumps({"status":"INDEPENDENT_PUBLIC_RUNNER_PASS","launcher_git_blob_sha":blob(LAUNCH),"activation_git_blob_sha":mod.EXPECTED_ACT,"candidate_git_blob_sha":mod.EXPECTED_CAND,"base_root_git_blob_sha":mod.EXPECTED_BASE,"executor_git_blob_sha":mod.EXPECTED_EXEC,"root_compatibility_rule_verified":True,"acceptance_mutation_fail_closed":True,"existing_scheduler_mutation_fail_closed":True,"authority_widening_fail_closed":True,"terminal_cases_consumed":0,"acceptance_credit_delta":0},sort_keys=True))
