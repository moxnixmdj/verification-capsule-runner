#!/usr/bin/env python3
from __future__ import annotations
import hashlib,importlib.util,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parent
ACT=ROOT/"subject/livebench_retry_v6_20261004/activation.json"
CAND=ROOT/"subject/livebench_retry_v6_20261004/candidate.json"
BASE=ROOT/"subject/livebench_retry_v6_20261004/root_base.json"
POINT=ROOT/"subject/livebench_retry_v6_20261004/root_point_of_use.json"
EXEC=ROOT/"execute_livebench_if_replay72_v4_candidate.py"
EXPECTED_ACT="c449329ad9e6e9ac001c5a1cdb2f3fa187fa49b3"
EXPECTED_CAND="07e857f0a7095838cecbc6a79961fe9580673ee4"
EXPECTED_BASE="54021118b1b1f299cf0191d1e413a3009d95d76c"
EXPECTED_EXEC="2a57ce896ddbd6819246aab8b44d17a00f36b61e"
FORBIDDEN_AUTH_KEYS=("execution_authority","fresh_reality_authority","global_fresh_reality","predicate_local_fresh_reality","promotion_authority","promotion","acceptance_credit_authority","acceptance_credit")

def git_blob_sha(p:pathlib.Path)->str:
 b=p.read_bytes(); return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def _true_forbidden_authority(obj,path=""):
 if isinstance(obj,dict):
  for k,v in obj.items():
   p=(path+"."+str(k)).strip(".")
   lk=str(k).lower()
   if any(tok==lk or tok in lk for tok in FORBIDDEN_AUTH_KEYS):
    if v is True: return p
   found=_true_forbidden_authority(v,p)
   if found:return found
 elif isinstance(obj,list):
  for i,v in enumerate(obj):
   found=_true_forbidden_authority(v,f"{path}[{i}]")
   if found:return found
 return None

def verify_root_compatibility(base:dict,current:dict)->dict:
 stable=("current_acceptance","current_residual_root_partition","root3_current_execution_state")
 for k in stable:
  if base.get(k)!=current.get(k): raise RuntimeError("INCOMPATIBLE_ROOT_DELTA:"+k)
 part=current.get("current_residual_root_partition") or {}
 if "LIVEBENCH_IF_GE_65_7" not in (part.get("root2_only") or []):
  raise RuntimeError("LIVEBENCH_NOT_ROOT2_ONLY_UNRESOLVED")
 for k in set(base)|set(current):
  if k=="scheduler_policy":continue
  if base.get(k)!=current.get(k):raise RuntimeError("INCOMPATIBLE_ROOT_TOP_LEVEL:"+k)
 bs=base.get("scheduler_policy") or {}; cs=current.get("scheduler_policy") or {}
 removed=sorted(set(bs)-set(cs))
 if removed: raise RuntimeError("SCHEDULER_POLICY_KEYS_REMOVED:"+",".join(removed))
 modified=[k for k in bs if bs.get(k)!=cs.get(k)]
 if modified: raise RuntimeError("EXISTING_SCHEDULER_POLICY_MODIFIED:"+",".join(sorted(modified)))
 added=sorted(set(cs)-set(bs))
 for k in added:
  bad=_true_forbidden_authority(cs[k],f"scheduler_policy.{k}")
  if bad: raise RuntimeError("NEW_SCHEDULER_OVERLAY_AUTHORITY_WIDENED:"+bad)
 return {"compatible":True,"added_scheduler_overlays":added}

def verify_prelaunch()->dict:
 if git_blob_sha(ACT)!=EXPECTED_ACT:raise RuntimeError("ACTIVATION_BLOB_DRIFT")
 if git_blob_sha(CAND)!=EXPECTED_CAND:raise RuntimeError("CANDIDATE_BLOB_DRIFT")
 if git_blob_sha(BASE)!=EXPECTED_BASE:raise RuntimeError("BASE_ROOT_BLOB_DRIFT")
 if git_blob_sha(EXEC)!=EXPECTED_EXEC:raise RuntimeError("EXECUTOR_BLOB_DRIFT")
 a=json.loads(ACT.read_text()); c=json.loads(CAND.read_text()); b=json.loads(BASE.read_text()); p=json.loads(POINT.read_text())
 if a.get("schema")!="PROJECT_BRAIN_LIVEBENCH_RETRY_EXECUTION_EPOCH_V6_ACTIVATION_V1" or a.get("active") is not True:raise RuntimeError("ACTIVATION_NOT_ACTIVE_V6")
 eb=a.get("exact_binding") or {}
 if eb.get("retry_candidate_git_blob_sha")!=EXPECTED_CAND or eb.get("base_root_git_blob_sha")!=EXPECTED_BASE or eb.get("executor_git_blob_sha")!=EXPECTED_EXEC:raise RuntimeError("ACTIVATION_BINDING_MISMATCH")
 if eb.get("replay_case_count")!=72 or eb.get("population_count")!=200:raise RuntimeError("REPLAY_SCOPE_DRIFT")
 auth=a.get("authority") or {}
 if auth.get("execution") is not True or auth.get("replay_existing_prefix") is not True:raise RuntimeError("REPLAY_AUTHORITY_MISSING")
 if auth.get("new_case_exposure") is not False or auth.get("global_fresh_reality") is not False or auth.get("promotion") is not False or auth.get("acceptance_credit") is not False:raise RuntimeError("ACTIVATION_AUTHORITY_WIDENED")
 if c.get("schema")!="PROJECT_BRAIN_LIVEBENCH_RETRY_EXECUTION_EPOCH_V6_CANDIDATE":raise RuntimeError("CANDIDATE_SCHEMA")
 if c.get("current_root",{}).get("git_blob_sha")!=EXPECTED_BASE:raise RuntimeError("CANDIDATE_BASE_ROOT_DRIFT")
 compat=verify_root_compatibility(b,p)
 return {"status":"PASS__V6_POINT_OF_USE_PRELAUNCH","activation_git_blob_sha":EXPECTED_ACT,"candidate_git_blob_sha":EXPECTED_CAND,"base_root_git_blob_sha":EXPECTED_BASE,"point_of_use_root_git_blob_sha":git_blob_sha(POINT),"executor_git_blob_sha":EXPECTED_EXEC,**compat,"terminal_cases_consumed":0,"new_case_exposure_authorized":False}

def main()->int:
 receipt=verify_prelaunch()
 print("LIVEBENCH_V6_PRELAUNCH="+json.dumps(receipt,sort_keys=True),flush=True)
 spec=importlib.util.spec_from_file_location("livebench_replay72_verified",EXEC)
 if spec is None or spec.loader is None:raise RuntimeError("EXECUTOR_IMPORT_SPEC")
 mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 return int(mod.main(authorized=True,activation_blob=EXPECTED_ACT))

if __name__=="__main__":raise SystemExit(main())
