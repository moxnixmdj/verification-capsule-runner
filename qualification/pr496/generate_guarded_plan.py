#!/usr/bin/env python3
import hashlib,json,pathlib,unicodedata
ROOT=pathlib.Path(__file__).resolve().parents[2]
GOAL="Independently adversarially qualify exact Brain PR496 broad explicit-recipe fail-closed repair without executing any parent research task."
PLAN=ROOT/"guarded_pr496_recipe_failclosed_plan.json"
FILES=[
 "canonical/runtime/bound_capabilities/broad_objective_decompose.py",
 "canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py",
 "canonical/tests/test_broad_objective_semantic_decomposition.py",
 "qualification/pr496/verify_recipe_failclosed.py",
 "qualification/pr496/authority.json",
 "qualification/pr496/generate_guarded_plan.py",
 "execution_guard/github_actions_guarded_run_live.py",
 "execution_guard/actions_admission.py",
 "execution_guard/github_ref_store_live.py",
]
EXPECTED={
 "canonical/runtime/bound_capabilities/broad_objective_decompose.py":"3ded762075ed222228a14877af631f1e2e6d9e4c",
 "canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py":"46e8e7466479ea298c34e5fa682d49c374510ce9",
 "canonical/tests/test_broad_objective_semantic_decomposition.py":"4717bd5ebf4b4e6521abf331e93e9675c1b8a785",
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
  raise SystemExit("EXACT_BRAIN_BLOB_MISMATCH:"+rel+":"+observed)
 pins.append({"path":rel,"git_blob_sha1":observed})
norm=" ".join(unicodedata.normalize("NFKC",GOAL).strip().lower().split())
candidate=(ROOT/FILES[0]).read_bytes()
auth=(ROOT/"qualification/pr496/authority.json").read_bytes()
oracle=(ROOT/"qualification/pr496/verify_recipe_failclosed.py").read_bytes()
plan={
 "schema":"BRAIN_GUARDED_LAUNCH_PLAN_V1",
 "goal_text":GOAL,
 "frozen":{
   "gate_id":"BRAIN-PR496-BROAD-RECIPE-FAILCLOSED-QUALIFICATION-20260930-V1",
   "problem_sha256":sha256(("goal_text_v1\0"+norm).encode()),
   "task_sha256":sha256(candidate),
   "runtime_sha256":sha256(oracle),
   "canonical_base":"d472da3082c8a26d16b91aad0997cb369ee5180e",
   "authorization_sha256":sha256(auth)
 },
 "pinned_files":pins,
 "command":["bash","-lc","python -m unittest canonical/tests/test_broad_objective_semantic_decomposition.py && python qualification/pr496/verify_recipe_failclosed.py"],
 "authority":{
   "brain_pr":496,
   "brain_pr_head":"d472da3082c8a26d16b91aad0997cb369ee5180e",
   "parent_task_execution":False,
   "spent_parent_task_replay":False,
   "model_dependency_count":0,
   "incremental_spend_usd":0
 }
}
PLAN.write_text(json.dumps(plan,indent=2,sort_keys=True)+"\n")
print(json.dumps({"status":"PLAN_GENERATED","brain_pr":496,"pin_count":len(pins),"problem_sha256":plan["frozen"]["problem_sha256"]}))
