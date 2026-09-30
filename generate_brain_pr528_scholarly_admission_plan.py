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
DISC="canonical/runtime/bound_capabilities/open_web_source_candidate_discovery.py"
FOCUS="canonical/runtime/bound_capabilities/research_query_focus.py"
EXTRACT="canonical/runtime/bound_capabilities/objective_evidence_unit_extract.py"
TEST="canonical/tests/test_scholarly_provenance_admission_materialization.py"
INTENT="canonical/action_intents/2026-09-30_REPAIR_SCHOLARLY_PROVENANCE_ADMISSION_MATERIALIZATION_V1.json"
GOAL=(
 "Independently qualify frozen Brain PR529 commit 4df38e5aa55cfd86a1fda6fbe11666ab6221da2c: "
 "all provenance-verified candidate classes compete in relevance; weak subject coverage fails closed; only a "
 "selected bibliographic winner is live-materialized under its verified identity; failed direct materialization "
 "may use one metadata-anchored retrieval refinement; ordinary live candidates are not rematerialized; and no "
 "authority, primary-source, factual-correctness, sufficiency, or parent-capability credit is inferred. Non-parent only."
)
def sha256(path): return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
plan={
 "schema":"BRAIN_GUARDED_LAUNCH_PLAN_V1",
 "goal_text":GOAL,
 "frozen":{
   "gate_id":"BRAIN-PR529-FROZEN-SCHOLARLY-ADMISSION-QUALIFICATION-20260930-V1",
   "problem_sha256":problem_sha256(GOAL),
   "task_sha256":sha256(TEST),
   "runtime_sha256":sha256(FRONT),
   "canonical_base":"3e2435efb9398a062ee40a7bdbb3e3610724b330",
   "authorization_sha256":sha256(AUTH)
 },
 "pinned_files":[
   {"path":PROV,"git_blob_sha1":"8f6f80403dc48268ecbf244ae633ea2928204148"},
   {"path":FRONT,"git_blob_sha1":"830fd35c816140cb6ddb2d3dac9f0886e595d993"},
   {"path":REL,"git_blob_sha1":"31d3703b38dcec3215b77d1038e2521b1a89ea95"},
   {"path":DISC,"git_blob_sha1":"81f73bca882d35603e5be43e8c40dd57e73ffce0"},
   {"path":FOCUS,"git_blob_sha1":"5403e1dc05716fcfc4f9a91b4534f55dc547eb7f"},
   {"path":EXTRACT,"git_blob_sha1":"227877b9f7c80c8e810a1042a0bad5c0ed94577d"},
   {"path":TEST,"git_blob_sha1":"d99e2fdf0db70a62d0c7483cb223a6159f681f0e"},
   {"path":INTENT,"git_blob_sha1":"26c5e477cdd1f5a2cdd6afbd70e4e843c4500d4b"},
   {"path":AUTH,"git_blob_sha1":"a80f4b82629faa9924ea6a15677234352b933c9a"},
   {"path":ORACLE,"git_blob_sha1":"e51c9e06d19b07f0e87cca7bf83330559a4b049e"},
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
   "brain_pr":529,
   "brain_candidate_head":"4df38e5aa55cfd86a1fda6fbe11666ab6221da2c",
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
