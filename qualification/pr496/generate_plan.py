#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, pathlib, unicodedata

ROOT=pathlib.Path(__file__).resolve().parents[2]
PLAN=ROOT/"qualification/pr496/guarded_plan.json"
GOAL="Independently guard-qualify exact Brain PR 496 broad explicit-recipe fail-closed repair on fresh non-parent adversarial cases without executing any parent task."
FILES=[
    "canonical/runtime/bound_capabilities/broad_objective_decompose.py",
    "canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py",
    "canonical/tests/test_broad_objective_semantic_decomposition.py",
    "qualification/pr496/authorization.json",
    "qualification/pr496/independent_oracle.py",
    "execution_guard/github_actions_guarded_run_live.py",
    "execution_guard/actions_admission.py",
    "execution_guard/github_ref_store_live.py",
]
EXPECTED={
    "canonical/runtime/bound_capabilities/broad_objective_decompose.py":"3ded762075ed222228a14877af631f1e2e6d9e4c",
    "canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py":"46e8e7466479ea298c34e5fa682d49c374510ce9",
    "canonical/tests/test_broad_objective_semantic_decomposition.py":"4717bd5ebf4b4e6521abf331e93e9675c1b8a785",
    "execution_guard/github_actions_guarded_run_live.py":"30ea2fd2cc548444477c7b234a59129ff8386235",
    "execution_guard/actions_admission.py":"6c46abef66c036f5382d5792b11a82a289b4dd94",
    "execution_guard/github_ref_store_live.py":"a8b0cf3facd91f4d4248bd4d2ed53f72f7d480c3",
}
def sha256(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()
def git_blob(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

payload={}
pins=[]
for rel in FILES:
    p=ROOT/rel
    if not p.is_file():
        raise SystemExit("PIN_FILE_MISSING:"+rel)
    data=p.read_bytes()
    observed=git_blob(data)
    if rel in EXPECTED and observed!=EXPECTED[rel]:
        raise SystemExit("EXACT_BLOB_MISMATCH:"+rel+":"+observed)
    payload[rel]=data
    pins.append({"path":rel,"git_blob_sha1":observed,"sha256":sha256(data)})

norm=" ".join(unicodedata.normalize("NFKC",GOAL).strip().lower().split())
plan={
    "schema":"BRAIN_GUARDED_LAUNCH_PLAN_V1",
    "goal_text":GOAL,
    "frozen":{
        "gate_id":"BRAIN-QUALIFY-PR496-EXPLICIT-RECIPE-FAILCLOSED-V2-20260930-V1",
        "problem_sha256":sha256(("goal_text_v1\0"+norm).encode()),
        "task_sha256":sha256(payload["canonical/tests/test_broad_objective_semantic_decomposition.py"]+b"\0"+payload["qualification/pr496/independent_oracle.py"]),
        "runtime_sha256":sha256(payload["canonical/runtime/bound_capabilities/broad_objective_decompose.py"]+b"\0"+payload["canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py"]),
        "canonical_base":"b8a0102421e68f4137a4c5fe72d27ed96fb448b2",
        "authorization_sha256":sha256(payload["qualification/pr496/authorization.json"]),
    },
    "pinned_files":pins,
    "command":["bash","-lc","python canonical/tests/test_broad_objective_semantic_decomposition.py && python qualification/pr496/independent_oracle.py"],
    "authority":{
        "kind":"NON_PARENT_GUARDED_INDEPENDENT_ADVERSARIAL_QUALIFICATION",
        "brain_pr":496,
        "brain_head_sha":"691d5368eb280b42db2b1fdd79381e9f85af29af",
        "authoritative_red_run":36689999285,
        "parent_task_execution":False,
        "parent_task_replay":False,
        "frozen_genomics_parent_task_execution":False,
        "model_dependency_count":0,
        "incremental_spend_usd":0,
    },
}
PLAN.write_text(json.dumps(plan,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps({"status":"PLAN_GENERATED","pin_count":len(pins),"problem_sha256":plan["frozen"]["problem_sha256"]},sort_keys=True))
