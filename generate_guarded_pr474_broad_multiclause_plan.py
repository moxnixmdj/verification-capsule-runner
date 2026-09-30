#!/usr/bin/env python3
from __future__ import annotations
import hashlib
import json
import pathlib
import unicodedata

ROOT=pathlib.Path(__file__).resolve().parent
PLAN=ROOT/"guarded_pr474_broad_multiclause_plan.json"
AUTH="pr474_broad_multiclause_qualification_authorization.json"
GROUNDING="canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py"
DECOMPOSER="canonical/runtime/bound_capabilities/broad_objective_decompose.py"
REGRESSION="canonical/tests/test_broad_objective_semantic_decomposition.py"
ORACLE="verify_pr474_broad_multiclause_routing.py"

EXPECTED_BLOBS={
  GROUNDING:"46e8e7466479ea298c34e5fa682d49c374510ce9",
  DECOMPOSER:"1efaec4ba51ecb5c40072b3190853f4de89d8f77",
  REGRESSION:"2df7c6ec85083458a69675f6ff86eca9c00ea278",
  ORACLE:"02d911d6d998aea626ba78a47e68336da62deaab",
  AUTH:"9bc8b91600150d48129c436d06b73e1eaa2d75eb",
  "execution_guard/github_actions_guarded_run_live.py":"30ea2fd2cc548444477c7b234a59129ff8386235",
  "execution_guard/actions_admission.py":"6c46abef66c036f5382d5792b11a82a289b4dd94",
  "execution_guard/github_ref_store_live.py":"a8b0cf3facd91f4d4248bd4d2ed53f72f7d480c3",
}

def git_blob(path):
    raw=(ROOT/path).read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def sha256_file(path):
    return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()

for path,want in EXPECTED_BLOBS.items():
    got=git_blob(path)
    if got!=want:
        raise SystemExit("EXACT_BLOB_MISMATCH:"+path+":"+got+":"+want)

goal=(
  "Independently qualify Brain PR474's exact generic broad multi-clause research-routing repair "
  "across fresh non-parent domains: all-unresolved multi-clause objectives must reach broad "
  "decomposition, generic research-method wording must not be treated as a supplied execution "
  "recipe, concrete commands and URLs must remain fail-closed, partial grounding must prevent "
  "whole-goal broad decomposition, and no parent task may execute."
)
norm=" ".join(unicodedata.normalize("NFKC",goal).strip().lower().split())
problem=hashlib.sha256(("goal_text_v1\0"+norm).encode("utf-8")).hexdigest()
runtime=hashlib.sha256(
    (ROOT/GROUNDING).read_bytes()+b"\0"+(ROOT/DECOMPOSER).read_bytes()
).hexdigest()

plan={
  "schema":"BRAIN_GUARDED_LAUNCH_PLAN_V1",
  "goal_text":goal,
  "frozen":{
    "gate_id":"BRAIN-PR474-BROAD-MULTICLAUSE-ROUTING-QUALIFICATION-20260930-V1",
    "problem_sha256":problem,
    "task_sha256":sha256_file(REGRESSION),
    "runtime_sha256":runtime,
    "canonical_base":"2b2ad1272c28229b3a26fc48f3515138313fd774",
    "authorization_sha256":sha256_file(AUTH),
  },
  "pinned_files":[
    {"path":path,"git_blob_sha1":blob}
    for path,blob in EXPECTED_BLOBS.items()
  ],
  "command":[
    "bash","-lc",
    "python canonical/tests/test_broad_objective_semantic_decomposition.py && "
    "python verify_pr474_broad_multiclause_routing.py"
  ],
  "authority":{
    "kind":"NON_PARENT_GUARDED_INDEPENDENT_QUALIFICATION",
    "brain_pr":474,
    "brain_candidate_head":"2b2ad1272c28229b3a26fc48f3515138313fd774",
    "authoritative_spent_parent_run":36688193204,
    "parent_task_execution":False,
    "parent_task_replay":False,
    "model_dependency_count":0,
    "incremental_spend_usd":0,
  },
}
PLAN.write_text(json.dumps(plan,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps({
  "status":"PLAN_GENERATED",
  "problem_sha256":problem,
  "task_sha256":plan["frozen"]["task_sha256"],
  "runtime_sha256":runtime,
  "authorization_sha256":plan["frozen"]["authorization_sha256"],
  "pinned_file_count":len(plan["pinned_files"]),
},sort_keys=True))
