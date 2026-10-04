#!/usr/bin/env python3
from __future__ import annotations
import hashlib,importlib.util,pathlib,tempfile
ROOT=pathlib.Path(__file__).resolve().parent
OLD=ROOT/"execute_livebench_replay72_v4.py"
NEW=ROOT/"execute_livebench_replay72_v5.py"
OLD_BLOB="d2a4208c20de549fc5d784e504041553aeb4a71e"
OLD_VALUES=[
 ('RETRY_CANDIDATE_BLOB = "2b9dcdc466ae3519a4378011394d1f4145840638"','RETRY_CANDIDATE_BLOB = "60622ca7b5c824cda767a3e95c6a0ae65a91efcd"'),
 ('CURRENT_ROOT_BLOB = "601e82d00104b4ed36ee5968ad966a0c02e627c1"','CURRENT_ROOT_BLOB = "f1c96d7924341e9c95a390cccf90d74109f10189"'),
 ('ACTIVATION_PATH = "subject/livebench_retry_v4_20261004/activation_v1.json"','ACTIVATION_PATH = "subject/livebench_retry_v5_20261004/activation_v1.json"'),
 ('EXECUTOR_PATH = "execute_livebench_replay72_v4.py"','EXECUTOR_PATH = "execute_livebench_replay72_v5.py"'),
 ('PROJECT_BRAIN_LIVEBENCH_RETRY_EXECUTION_EPOCH_V4_ACTIVATION_V1','PROJECT_BRAIN_LIVEBENCH_RETRY_EXECUTION_EPOCH_V5_ACTIVATION_V1'),
]
def blob(p):
 b=p.read_bytes(); return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def main():
 assert blob(OLD)==OLD_BLOB,(blob(OLD),OLD_BLOB)
 expected=OLD.read_text()
 for old,new in OLD_VALUES: expected=expected.replace(old,new)
 actual=NEW.read_text()
 assert actual==expected,"V5_EXECUTOR_DELTA_EXCEEDS_IDENTITY_REBIND"
 spec=importlib.util.spec_from_file_location("v5exec",NEW); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
 assert mod.REPLAY_LIMIT==72
 assert mod.RETRY_CANDIDATE_BLOB=="60622ca7b5c824cda767a3e95c6a0ae65a91efcd"
 assert mod.CURRENT_ROOT_BLOB=="f1c96d7924341e9c95a390cccf90d74109f10189"
 assert mod.ACTIVATION_PATH=="subject/livebench_retry_v5_20261004/activation_v1.json"
 assert mod.EXECUTOR_PATH=="execute_livebench_replay72_v5.py"
 assert mod.FROZEN_RUNTIME_CLOSURE_FILE_COUNT==24
 with tempfile.TemporaryDirectory(prefix="verify-lb-v5exec-") as td:
  template=mod.build_runtime_template(pathlib.Path(td))
  q1={"question_id":"ZERO_CASE_BOUND_CAPABILITY_SMOKE","turns":["Read canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json. Read canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json."]}
  _,a,e=mod.infer_one(template,q1); assert e is None,e; assert a
  q2={"question_id":"ZERO_CASE_POLICY_BLOCK_SMOKE","turns":["Respond with exactly SYNTHETIC_OK."]}
  _,a2,e2=mod.infer_one(template,q2); assert a2==""; assert e2==mod.POLICY_BLOCK,e2
 print('{"status":"INDEPENDENT_PUBLIC_RUNNER_PASS","semantic_delta":"IDENTITY_REBIND_ONLY","replay_case_count":72,"new_case_exposure_authorized":false,"terminal_cases_consumed":0,"acceptance_credit_delta":0,"executor_git_blob_sha":"'+blob(NEW)+'"}')
if __name__=="__main__": main()
