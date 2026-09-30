#!/usr/bin/env python3
import hashlib,json,pathlib,unicodedata
ROOT=pathlib.Path(__file__).resolve().parents[2]
GOAL="Independently qualify exact Brain PR 474 corrected generic broad multi-clause open-research routing without executing or replaying any parent research task."
PLAN=ROOT/"guarded_pr474_multiclause_routing_plan.json"
FILES=[
 "qualification/pr468/broad_objective_decompose.py",
 "qualification/pr468/plain_goal_bound_grounding.py",
 "qualification/pr468/verify_multiclause_routing.py",
 "qualification/pr468/authority.json",
 "qualification/pr468/generate_guarded_plan.py",
 "execution_guard/github_actions_guarded_run_live.py",
 "execution_guard/actions_admission.py",
 "execution_guard/github_ref_store_live.py",
]
EXPECTED={
 "qualification/pr468/broad_objective_decompose.py":"1efaec4ba51ecb5c40072b3190853f4de89d8f77",
 "qualification/pr468/plain_goal_bound_grounding.py":"46e8e7466479ea298c34e5fa682d49c374510ce9",
}
def sha256(b): return hashlib.sha256(b).hexdigest()
def blob(p):
 raw=p.read_bytes()
 return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
pins=[]
for rel in FILES:
 p=ROOT/rel
 if not p.is_file(): raise SystemExit("PIN_FILE_MISSING:"+rel)
 observed=blob(p)
 if rel in EXPECTED and observed!=EXPECTED[rel]:
  raise SystemExit("EXACT_CANDIDATE_BLOB_MISMATCH:"+rel+":"+observed)
 pins.append({"path":rel,"git_blob_sha1":observed})
norm=" ".join(unicodedata.normalize("NFKC",GOAL).strip().lower().split())
dec=(ROOT/FILES[0]).read_bytes()
grd=(ROOT/FILES[1]).read_bytes()
ver=(ROOT/FILES[2]).read_bytes()
auth=(ROOT/FILES[3]).read_bytes()
plan={
 "schema":"BRAIN_GUARDED_LAUNCH_PLAN_V1",
 "goal_text":GOAL,
 "frozen":{
   "gate_id":"BRAIN-PR474-CORRECTED-BROAD-ROUTING-QUALIFICATION-20260930-V1",
   "problem_sha256":sha256(("goal_text_v1\0"+norm).encode()),
   "task_sha256":sha256(dec+b"\0"+grd),
   "runtime_sha256":sha256(ver),
   "canonical_base":"2b2ad1272c28229b3a26fc48f3515138313fd774",
   "authorization_sha256":sha256(auth)
 },
 "pinned_files":pins,
 "command":["bash","-lc","python -m py_compile qualification/pr468/broad_objective_decompose.py qualification/pr468/plain_goal_bound_grounding.py qualification/pr468/verify_multiclause_routing.py && python qualification/pr468/verify_multiclause_routing.py"],
 "authority":{"brain_pr":474,"brain_pr_head":"2b2ad1272c28229b3a26fc48f3515138313fd774","parent_task_execution":False,"spent_parent_task_replay":False,"model_dependency_count":0,"incremental_spend_usd":0}
}
PLAN.write_text(json.dumps(plan,indent=2,sort_keys=True)+"\n")
print(json.dumps({"status":"PLAN_GENERATED","brain_pr":474,"pin_count":len(pins),"problem_sha256":plan["frozen"]["problem_sha256"]}))
