#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, pathlib, sys
ROOT=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/"execution_guard"))
from actions_admission import problem_sha256

AUTH="pr510_query_relevance_authority.json"
ORACLE="verify_brain_pr510_query_relevance.py"
DISC="canonical/runtime/bound_capabilities/open_web_source_candidate_discovery.py"
FRONT="canonical/runtime/bound_capabilities/open_research_source_frontend.py"
REL="canonical/runtime/bound_capabilities/objective_relevance_bm25.py"
DECOMP="canonical/runtime/bound_capabilities/broad_objective_decompose.py"
TEST1="canonical/tests/test_open_web_source_candidate_discovery.py"
TEST2="canonical/tests/test_open_research_query_focus_regression.py"

GOAL=(
 "Independently qualify Brain PR510 exact generic open-research repair: derive discovery from the supplied "
 "decision-bearing clause, align deterministic relevance ranking to that focused query, preserve the full "
 "objective for extraction/binding, preserve explicit search objectives, survive cross-domain and punctuation "
 "boundaries, and demonstrate fresh non-parent live search reachability. No genomics parent replay."
)
def sha256(path):
    return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()

plan={
 "schema":"BRAIN_GUARDED_LAUNCH_PLAN_V1",
 "goal_text":GOAL,
 "frozen":{
   "gate_id":"BRAIN-PR510-QUERY-RELEVANCE-FOCUS-QUALIFICATION-20260930-V1",
   "problem_sha256":problem_sha256(GOAL),
   "task_sha256":sha256(TEST2),
   "runtime_sha256":sha256(DISC),
   "canonical_base":"0d795dad885e706e6eb1cfd4d20cd2b2edd5cf12",
   "authorization_sha256":sha256(AUTH)
 },
 "pinned_files":[
   {"path":DISC,"git_blob_sha1":"c913c20203b638caff050e7461a4b0023852ee10"},
   {"path":FRONT,"git_blob_sha1":"a6fa0f32eab09791ec6a8cdabe961519d073be58"},
   {"path":REL,"git_blob_sha1":"95d2b6bac6f6ffb5db97526407fcd22cbcc6c790"},
   {"path":DECOMP,"git_blob_sha1":"3ded762075ed222228a14877af631f1e2e6d9e4c"},
   {"path":TEST1,"git_blob_sha1":"cdde67e65f5c7fcf3793c5e10973fb409b8c4f66"},
   {"path":TEST2,"git_blob_sha1":"d92ff787afa66bd4317ba127305ccd1937f1be16"},
   {"path":AUTH,"git_blob_sha1":"fc6e0f59a829b0009eb4aa4b3217b35e8f57cd15"},
   {"path":ORACLE,"git_blob_sha1":"8a5c35add5b98054c8a119de94cba9d8179afe90"},
   {"path":"execution_guard/github_actions_guarded_run_live.py","git_blob_sha1":"30ea2fd2cc548444477c7b234a59129ff8386235"},
   {"path":"execution_guard/actions_admission.py","git_blob_sha1":"6c46abef66c036f5382d5792b11a82a289b4dd94"},
   {"path":"execution_guard/github_ref_store_live.py","git_blob_sha1":"a8b0cf3facd91f4d4248bd4d2ed53f72f7d480c3"}
 ],
 "command":["bash","-lc",
   "set -euo pipefail; python canonical/tests/test_open_web_source_candidate_discovery.py && "
   "python canonical/tests/test_open_research_query_focus_regression.py && "
   "python verify_brain_pr510_query_relevance.py"
 ],
 "authority":{
   "kind":"NON_PARENT_GUARDED_INDEPENDENT_QUALIFICATION",
   "brain_pr":510,
   "brain_candidate_head":"135bb413448cb9a0c2fc1f39943d1cd800fbb9ef",
   "authoritative_parent_evidence_run":36690682680,
   "qualification_only":True,
   "parent_task_execution":False,
   "parent_task_replay":False,
   "spent_genomics_task_b_replay":False,
   "model_dependency_count":0,
   "incremental_spend_usd":0
 }
}
(ROOT/"brain_pr510_query_relevance_plan.json").write_text(json.dumps(plan,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps({"status":"PLAN_GENERATED","problem_sha256":plan["frozen"]["problem_sha256"]},sort_keys=True))
