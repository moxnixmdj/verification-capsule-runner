#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parent
ACT=ROOT/"subject/livebench_retry_v5_activation_20261004/activation.json"
CAND=ROOT/"subject/livebench_retry_v5_activation_20261004/candidate.json"
RSTATE=ROOT/"subject/livebench_retry_v5_activation_20261004/root.json"
EXEC=ROOT/"execute_livebench_replay72_v4.py"
EXPECTED_ACT="bf0212e7d62d80c687b829654dd79d39322a7947"
EXPECTED_CAND="60622ca7b5c824cda767a3e95c6a0ae65a91efcd"
EXPECTED_ROOT="f1c96d7924341e9c95a390cccf90d74109f10189"
EXPECTED_EXEC="d2a4208c20de549fc5d784e504041553aeb4a71e"

def blob(p):
 b=p.read_bytes(); return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def main():
 assert blob(ACT)==EXPECTED_ACT
 assert blob(CAND)==EXPECTED_CAND
 assert blob(RSTATE)==EXPECTED_ROOT
 assert blob(EXEC)==EXPECTED_EXEC
 a=json.loads(ACT.read_text()); c=json.loads(CAND.read_text()); r=json.loads(RSTATE.read_text())
 assert a["schema"]=="PROJECT_BRAIN_LIVEBENCH_RETRY_EXECUTION_EPOCH_V5_ACTIVATION_V1"
 assert a["active"] is True and a["target_predicate"]=="LIVEBENCH_IF_GE_65_7"
 b=a["exact_binding"]
 assert b["retry_candidate_git_blob_sha"]==EXPECTED_CAND
 assert b["root_git_blob_sha"]==EXPECTED_ROOT
 assert b["executor_git_blob_sha"]==EXPECTED_EXEC
 assert b["replay_case_count"]==72
 assert b["population_count"]==200
 assert b["case_order"]=="QUESTION_ID_ASCENDING_FIXED_PREEXECUTION"
 assert b["threshold_percent"]==65.7
 assert c["current_root"]["git_blob_sha"]==EXPECTED_ROOT
 assert c["retry_scope"]["first_required_replay"]=="EXACT_ALREADY_ATTEMPTED_72_CASE_PREFIX_ONLY"
 assert c["retry_scope"]["new_case_exposure_before_replay_validation"] is False
 assert c["executor_verification"]["executor_git_blob_sha"]==EXPECTED_EXEC
 ca=r["current_acceptance"]; part=r["current_residual_root_partition"]
 assert ca["terminal"] is False and ca["unresolved_atomic"]==26
 assert part["root1_positive_gap_count"]==0
 assert "LIVEBENCH_IF_GE_65_7" in part["root2_only"]
 auth=a["authority"]
 assert auth["execution"] is True
 assert auth["replay_existing_prefix"] is True
 assert auth["predicate_local_fresh_reality"] is True
 assert auth["new_case_exposure"] is False
 assert auth["global_fresh_reality"] is False
 assert auth["promotion"] is False
 assert auth["acceptance_credit"] is False
 rc=a["replay_contract"]
 assert rc["exact_prefix_case_count"]==72
 assert rc["new_case_exposure_before_replay_validation"] is False
 assert rc["post_prompt_capability_acquisition"] is False
 assert rc["external_tool_discovery_or_install_during_case_inference"] is False
 assert rc["optional_model_planner"] is False
 assert rc["adaptive_case_selection"] is False
 assert rc["case_replacement"] is False
 assert rc["repair_from_terminal_prompt_or_response_content"] is False
 hard=set(a["hard_rules"])
 assert "ONE_REPLAY_EPOCH_ONLY" in hard and "NO_CASE_73_OR_LATER" in hard and "FAIL_CLOSED_ON_ANY_BINDING_OR_ZERO_CASE_PREFLIGHT_FAILURE" in hard
 src=EXEC.read_text()
 assert "REPLAY_LIMIT = 72" in src
 assert "for start in range(0,REPLAY_LIMIT,BATCH):" in src
 assert "for start in range(0,POPULATION,BATCH):" not in src
 assert "_load_auto_capability_acquisition = _blocked_auto_acquisition" in src
 assert 'new_case_exposure_authorized":False' in src
 print(json.dumps({
   "status":"INDEPENDENT_PUBLIC_RUNNER_PASS",
   "activation_git_blob_sha":EXPECTED_ACT,
   "candidate_git_blob_sha":EXPECTED_CAND,
   "root_git_blob_sha":EXPECTED_ROOT,
   "executor_git_blob_sha":EXPECTED_EXEC,
   "execution_authority":"REPLAY_EXISTING_72_PREFIX_ONLY",
   "new_case_exposure_authorized":False,
   "global_fresh_reality_authority":False,
   "promotion_authority":False,
   "terminal_cases_consumed":0,
   "acceptance_credit_delta":0
 },sort_keys=True))
if __name__=="__main__": main()
