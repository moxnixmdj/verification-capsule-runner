#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/"execution_guard"))
from actions_admission import problem_sha256

AUTH="pr528_scholarly_admission_authority.json"
ORACLE="verify_brain_pr528_scholarly_admission.py"
FRONT="canonical/runtime/bound_capabilities/open_research_source_frontend.py"
PROV="canonical/runtime/bound_capabilities/source_candidate_provenance_verify.py"
REL="canonical/runtime/bound_capabilities/objective_relevance_bm25.py"
FOCUS="canonical/runtime/bound_capabilities/research_query_focus.py"
EXTRACT="canonical/runtime/bound_capabilities/objective_evidence_unit_extract.py"
TEST="canonical/tests/test_scholarly_provenance_admission_materialization.py"
INTENT="canonical/action_intents/2026-09-30_REPAIR_SCHOLARLY_PROVENANCE_ADMISSION_MATERIALIZATION_V1.json"
GOAL=(
 "Independently qualify frozen Brain PR528 commit 6d4064312705eaa11ce5817287934e6c5d87d5f4: "
 "provenance-verified scholarly candidates survive relevance, weak relevance fails closed, only the selected "
 "bibliographic winner is live-materialized under its verified identity, ordinary retrieval candidates are not "
 "rematerialized, and no authority/primary-source/factual-correctness credit is inferred. Non-parent only."
)
def sha256(path): return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
plan={
 "schema":"BRAIN_GUARDED_LAUNCH_PLAN_V1",
 "goal_text":GOAL,
 "frozen":{
   "gate_id":"BRAIN-PR528-SCHOLARLY-ADMISSION-QUALIFICATION-20260930-V1",
   "problem_sha256":problem_sha256(GOAL),
   "task_sha256":sha256(TEST),
   "runtime_sha256":sha256(FRONT),
   "canonical_base":"3e2435efb9398a062ee40a7bdbb3e3610724b330",
   "authorization_sha256":sha256(AUTH)
 },
 "pinned_files":[
   {"path":PROV,"git_blob_sha1":"8f6f80403dc48268ecbf244ae633ea2928204148"},
   {"path":FRONT,"git_blob_sha1":"0f8ef8ea7f24694f2e2ea8e9741cab5f2d9a8bf2"},
   {"path":REL,"git_blob_sha1":"31d3703b38dcec3215b77d1038e2521b1a89ea95"},
   {"path":FOCUS,"git_blob_sha1":"5403e1dc05716fcfc4f9a91b4534f55dc547eb7f"},
   {"path":EXTRACT,"git_blob_sha1":"227877b9f7c80c8e810a1042a0bad5c0ed94577d"},
   {"path":TEST,"git_blob_sha1":"24acc968c08134eddd43f819cac5f6f47b758a66"},
   {"path":INTENT,"git_blob_sha1":"9453d9c9844e597b36591680d84f34b72ad2815f"},
   {"path":AUTH,"git_blob_sha1":"1ea385e130c2d4e1b5e4dabc31e410816b5ae6ed"},
   {"path":ORACLE,"git_blob_sha1":"ad45703b56a4d30340781b8e95d26d01190cf57f"},
   {"path":"execution_guard/github_actions_guarded_run_live.py","git_blob_sha1":"30ea2fd2cc548444477c7b234a59129ff8386235"},
   {"path":"execution_guard/actions_admission.py","git_blob_sha1":"6c46abef66c036f5382d5792b11a82a289b4dd94"},
   {"path":"execution_guard/github_ref_store_live.py","git_blob_sha1":"a8b0cf3facd91f4d4248bd4d2ed53f72f7d480c3"}
 ],
 "command":["bash","-lc",
   "set -euo pipefail; python canonical/tests/test_scholarly_provenance_admission_materialization.py && "
   "python verify_brain_pr528_scholarly_admission.py"
 ],
 "authority":{
   "kind":"NON_PARENT_GUARDED_INDEPENDENT_QUALIFICATION",
   "brain_pr":528,
   "brain_candidate_head":"6d4064312705eaa11ce5817287934e6c5d87d5f4",
   "qualification_only":True,
   "parent_task_execution":False,
   "parent_task_replay":False,
   "spent_seismology_replay":False,
   "model_dependency_count":0,
   "incremental_spend_usd":0
 }
}
(ROOT/"brain_pr528_scholarly_admission_plan.json").write_text(json.dumps(plan,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps({"status":"PLAN_GENERATED","problem_sha256":plan["frozen"]["problem_sha256"]},sort_keys=True))
