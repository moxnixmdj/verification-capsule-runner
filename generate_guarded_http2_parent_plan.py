#!/usr/bin/env python3
import hashlib, json, pathlib, unicodedata

ROOT=pathlib.Path(__file__).resolve().parent
OUT="guarded_http2_parent_task_a_plan.json"
TERMINAL="http2-parent-task-terminal.json"
AUTH="canonical/action_intents/2026-09-30_REPAIR_OPEN_RESEARCH_QUERY_FOCUS_V1.json"
DISCOVERY="canonical/runtime/bound_capabilities/open_web_source_candidate_discovery.py"
FRONTEND="canonical/runtime/bound_capabilities/open_research_source_frontend.py"
AUTHORED_DISCOVERY_TEST="canonical/tests/test_open_web_source_candidate_discovery.py"
AUTHORED_INTEGRATION_TEST="canonical/tests/test_open_research_query_focus_regression.py"
INDEPENDENT="verify_brain_pr510_query_focus.py"

PINNED=[
    AUTH,
    DISCOVERY,
    FRONTEND,
    "canonical/runtime/bound_capabilities/objective_relevance_bm25.py",
    "canonical/runtime/bound_capabilities/broad_objective_decompose.py",
    AUTHORED_DISCOVERY_TEST,
    AUTHORED_INTEGRATION_TEST,
    INDEPENDENT,
    "execution_guard/github_actions_guarded_run_live.py",
    "execution_guard/actions_admission.py",
    "execution_guard/github_ref_store_live.py",
]

def raw(rel):
    return (ROOT/rel).read_bytes()

def sha256(rel):
    return hashlib.sha256(raw(rel)).hexdigest()

def blob_sha1(rel):
    data=raw(rel)
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

goal=(
    "Independently qualify Brain PR 510 decision-clause query focusing on exact mirrored "
    "candidate bytes using authored regressions, fresh cross-domain adversarial cases, "
    "and a live non-parent search check; do not execute or replay any parent task."
)
norm=" ".join(unicodedata.normalize("NFKC",goal).strip().lower().split())
plan={
  "schema":"BRAIN_GUARDED_LAUNCH_PLAN_V1",
  "goal_text":goal,
  "frozen":{
    "gate_id":"BRAIN-QUALIFY-PR510-OPEN-RESEARCH-QUERY-FOCUS-20260930-V1",
    "problem_sha256":hashlib.sha256(("goal_text_v1\0"+norm).encode()).hexdigest(),
    "task_sha256":sha256(AUTHORED_INTEGRATION_TEST),
    "runtime_sha256":sha256(DISCOVERY),
    "canonical_base":"0d795dad885e706e6eb1cfd4d20cd2b2edd5cf12",
    "authorization_sha256":sha256(AUTH),
  },
  "pinned_files":[{"path":p,"git_blob_sha1":blob_sha1(p)} for p in PINNED],
  "command":[
    "bash","-lc",
    "set -o pipefail; { "
    "python -m py_compile "
    "canonical/runtime/bound_capabilities/open_web_source_candidate_discovery.py "
    "canonical/runtime/bound_capabilities/open_research_source_frontend.py "
    "verify_brain_pr510_query_focus.py; "
    "python canonical/tests/test_open_web_source_candidate_discovery.py; "
    "python canonical/tests/test_open_research_query_focus_regression.py; "
    "python verify_brain_pr510_query_focus.py; "
    "} 2>&1 | tee "+TERMINAL,
  ],
  "authority":{
    "kind":"NON_PARENT_GUARDED_INDEPENDENT_QUALIFICATION",
    "brain_pr":510,
    "brain_candidate_head":"135bb413448cb9a0c2fc1f39943d1cd800fbb9ef",
    "parent_task_execution":False,
    "parent_task_replay":False,
    "spent_genomics_parent_run":36690682680,
    "model_dependency_count":0,
    "incremental_spend_usd":0,
  },
}
(ROOT/OUT).write_text(json.dumps(plan,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps({
  "status":"PR510_QUALIFICATION_PLAN_GENERATED",
  "problem_sha256":plan["frozen"]["problem_sha256"],
  "runtime_sha256":plan["frozen"]["runtime_sha256"],
  "pin_count":len(plan["pinned_files"]),
},sort_keys=True))
