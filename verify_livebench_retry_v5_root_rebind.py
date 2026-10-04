#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parent
CAND=ROOT/"subject/livebench_retry_v5_root_rebind_20261004/candidate.json"
OLD=ROOT/"subject/livebench_retry_v5_root_rebind_20261004/root_old_601e82.json"
NEW=ROOT/"subject/livebench_retry_v5_root_rebind_20261004/root_current_f1c96d.json"
EXPECTED_CAND="60622ca7b5c824cda767a3e95c6a0ae65a91efcd"
EXPECTED_OLD="601e82d00104b4ed36ee5968ad966a0c02e627c1"
EXPECTED_NEW="f1c96d7924341e9c95a390cccf90d74109f10189"

def blob(p):
 b=p.read_bytes(); return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def main():
 assert blob(CAND)==EXPECTED_CAND
 assert blob(OLD)==EXPECTED_OLD
 assert blob(NEW)==EXPECTED_NEW
 c=json.loads(CAND.read_text()); o=json.loads(OLD.read_text()); n=json.loads(NEW.read_text())
 assert c["schema"]=="PROJECT_BRAIN_LIVEBENCH_RETRY_EXECUTION_EPOCH_V5_CANDIDATE"
 assert c["current_root"]["git_blob_sha"]==EXPECTED_NEW
 assert c["rebind_from_v4"]["prior_root_git_blob_sha"]==EXPECTED_OLD
 assert c["rebind_from_v4"]["current_root_git_blob_sha"]==EXPECTED_NEW
 assert c["executor_verification"]["status"]=="INDEPENDENT_PUBLIC_RUNNER_PASS"
 assert c["executor_verification"]["executor_git_blob_sha"]=="d2a4208c20de549fc5d784e504041553aeb4a71e"
 assert c["retry_scope"]["first_required_replay"]=="EXACT_ALREADY_ATTEMPTED_72_CASE_PREFIX_ONLY"
 assert c["retry_scope"]["new_case_exposure_before_replay_validation"] is False

 old_keys=set(o); new_keys=set(n)
 changed=sorted(k for k in old_keys|new_keys if o.get(k)!=n.get(k))
 assert changed==["scheduler_policy"],changed
 assert o["current_acceptance"]==n["current_acceptance"]
 assert o["current_residual_root_partition"]==n["current_residual_root_partition"]
 assert o["root3_current_execution_state"]==n["root3_current_execution_state"]
 a=n["current_acceptance"]; p=n["current_residual_root_partition"]
 assert a=={"accepted_families":5,"open_families":14,"proved_atomic":12,"unresolved_atomic":26,"total_families":19,"total_atomic":38,"terminal":False}
 assert p["root1_positive_gap_count"]==0
 assert "LIVEBENCH_IF_GE_65_7" in p["root2_only"]
 m=n["scheduler_policy"]["terminal_minimum_causal_depth"]
 assert m["status"].startswith("ACTIVE__INDEPENDENT_PUBLIC_RUNNER_PASS")
 assert m["execution_authority"] is False
 assert m["promotion_authority"] is False
 assert m["fresh_reality_authority"] is False
 print(json.dumps({
   "status":"INDEPENDENT_PUBLIC_RUNNER_PASS",
   "candidate_git_blob_sha":EXPECTED_CAND,
   "prior_root_git_blob_sha":EXPECTED_OLD,
   "current_root_git_blob_sha":EXPECTED_NEW,
   "changed_top_level":["scheduler_policy"],
   "acceptance_state_identical":True,
   "root_partition_identical":True,
   "root3_state_identical":True,
   "livebench_remains_root2_only_unresolved":True,
   "new_scheduler_overlay_authority":"SCHEDULING_ONLY",
   "execution_authority_delta":False,
   "fresh_reality_authority_delta":False,
   "promotion_authority_delta":False,
   "terminal_cases_consumed":0,
   "acceptance_credit_delta":0
 },sort_keys=True))
if __name__=="__main__": main()
