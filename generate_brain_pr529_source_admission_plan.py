#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/"execution_guard"))
from actions_admission import problem_sha256
AUTH="pr529_source_admission_authority.json"
ORACLE="verify_brain_pr529_source_admission.py"
FILES={
 "canonical/runtime/bound_capabilities/source_candidate_provenance_verify.py":"8f6f80403dc48268ecbf244ae633ea2928204148",
 "canonical/runtime/bound_capabilities/open_research_source_frontend.py":"830fd35c816140cb6ddb2d3dac9f0886e595d993",
 "canonical/runtime/bound_capabilities/objective_relevance_bm25.py":"31d3703b38dcec3215b77d1038e2521b1a89ea95",
 "canonical/runtime/bound_capabilities/research_query_focus.py":"5403e1dc05716fcfc4f9a91b4534f55dc547eb7f",
 "canonical/runtime/bound_capabilities/objective_evidence_unit_extract.py":"227877b9f7c80c8e810a1042a0bad5c0ed94577d",
 "canonical/runtime/bound_capabilities/open_web_source_candidate_discovery.py":"81f73bca882d35603e5be43e8c40dd57e73ffce0",
 "canonical/tests/test_scholarly_provenance_admission_materialization.py":"d99e2fdf0db70a62d0c7483cb223a6159f681f0e",
 "canonical/action_intents/2026-09-30_REPAIR_SCHOLARLY_PROVENANCE_ADMISSION_MATERIALIZATION_V1.json":"26c5e477cdd1f5a2cdd6afbd70e4e843c4500d4b",
 AUTH:"5dabdb7d670ab0826414af479ef2d920eb7d09ea",
 ORACLE:"25ceb1331a3470a4b389c291a65baffb1a9a557b",
 "execution_guard/github_actions_guarded_run_live.py":"30ea2fd2cc548444477c7b234a59129ff8386235",
 "execution_guard/actions_admission.py":"6c46abef66c036f5382d5792b11a82a289b4dd94",
 "execution_guard/github_ref_store_live.py":"a8b0cf3facd91f4d4248bd4d2ed53f72f7d480c3"
}
def sha256(p): return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
GOAL=("Independently qualify frozen Brain PR529 commit 4df38e5aa55cfd86a1fda6fbe11666ab6221da2c: "
      "provenance-class-preserving relevance admission, bounded subject-coverage admission, identity-bound selected-only "
      "bibliographic materialization, one metadata-anchored live retrieval retry, downstream extraction enforcement, "
      "and fail-closed uncertainty. No parent execution or seismology replay.")
plan={
 "schema":"BRAIN_GUARDED_LAUNCH_PLAN_V1",
 "goal_text":GOAL,
 "frozen":{
   "gate_id":"BRAIN-PR529-SOURCE-ADMISSION-QUALIFICATION-20260930-V1",
   "problem_sha256":problem_sha256(GOAL),
   "task_sha256":sha256("canonical/tests/test_scholarly_provenance_admission_materialization.py"),
   "runtime_sha256":sha256("canonical/runtime/bound_capabilities/open_research_source_frontend.py"),
   "canonical_base":"3e2435efb9398a062ee40a7bdbb3e3610724b330",
   "authorization_sha256":sha256(AUTH)
 },
 "pinned_files":[{"path":p,"git_blob_sha1":s} for p,s in FILES.items()],
 "command":["bash","-lc",
   "set -euo pipefail; python canonical/tests/test_scholarly_provenance_admission_materialization.py && "
   "python verify_brain_pr529_source_admission.py"
 ],
 "authority":{
   "kind":"NON_PARENT_GUARDED_INDEPENDENT_QUALIFICATION",
   "brain_pr":529,"brain_candidate_head":"4df38e5aa55cfd86a1fda6fbe11666ab6221da2c",
   "qualification_only":True,"parent_task_execution":False,"parent_task_replay":False,
   "spent_seismology_replay":False,"model_dependency_count":0,"incremental_spend_usd":0
 }
}
(ROOT/"brain_pr529_source_admission_plan.json").write_text(json.dumps(plan,indent=2,sort_keys=True)+"\n")
print(json.dumps({"status":"PLAN_GENERATED","problem_sha256":plan["frozen"]["problem_sha256"]},sort_keys=True))
