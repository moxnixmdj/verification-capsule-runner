from __future__ import annotations
import json, pathlib

ROOT=pathlib.Path(__file__).resolve().parent
def load(name): return json.loads((ROOT/name).read_text())
errors=[]
def need(cond,msg):
    if not cond: errors.append(msg)

i=load("ACTION_INTENT_TB_SCIENCE_RANK14_POST_PROMPT_SUMMARY_REAUTHORIZE_20261009_V1.json")
c=load("TB_SCIENCE_RANK14_ONE_SLOT_EXECUTION_AUTHORITY_CANDIDATE_20261009_V3.json")
l=load("TB_SCIENCE_CURRENT_SLOT_LEDGER_RECONCILIATION_20261009_V18.json")
m=load("TB_SCIENCE_TRANSITIVE_RUNTIME_CLOSURE_MANIFEST_20261009_V11.json")
mv=load("TB_SCIENCE_TRANSITIVE_RUNTIME_CLOSURE_V11_PUBLIC_VERIFICATION_20261009_V1.json")
pv=load("TB_SCIENCE_RANK14_PLANNER_MANIFEST_SUMMARY_PUBLIC_VERIFICATION_20261009_V1.json")

need(c.get("schema")=="PROJECT_BRAIN_TB_SCIENCE_RANK14_ONE_SLOT_EXECUTION_AUTHORITY_CANDIDATE_20261009_V3","CANDIDATE_SCHEMA")
need(c.get("execution_authority") is False,"CANDIDATE_SELF_AUTHORIZED")
need(c.get("task_read_authority") is False,"TASK_READ_SELF_AUTHORIZED")
need(c.get("task_start_authority") is False,"TASK_START_SELF_AUTHORIZED")
need(c.get("promotion_authority") is False,"PROMOTION_SELF_AUTHORIZED")
need(c["slot"]["id"]=="terminal-bench-science/inverse-lithography::trial-0","SLOT_ID")
need(c["slot"]["digest"]=="sha256:8c4da4b5b3a00283335e83dda92584aaf9293ff773bc43f2bf95eb0e2c0f8530","TASK_DIGEST")
need(c["intent"]["git_blob_sha"]=="70dc5962595a464e4df0b1cfb8f6c49fc160470d","INTENT_BLOB")
need(c["current_ledger"]["git_blob_sha"]=="566a3756392ee2d4cc41947b66617acbc6f6ce92","LEDGER_BLOB")
need(c["repaired_route"]["agent_blob"]=="d397324f411d002bdbdca348aaad708b5b40c9c2","AGENT_BLOB")
need(c["repaired_route"]["v11_closure_blob"]=="1172b57ac436d64027d06fb4897878ae274febb1","V11_BLOB")
need(c["repaired_route"]["v11_closure_verification_blob"]=="d1b3bc55c2ead9137a2368337eb58d96e9b44a17","V11_VERIFY_BLOB")
need(c["repaired_route"]["planner_manifest_summary_verification_blob"]=="721c78aabac58565afa37d734705d652073d99ae","PROMPT_REPAIR_VERIFY_BLOB")
need(c["proposed_controls"]["precheck_failure_consumes_slot"] is False,"PRECHECK_MUST_BE_NONCONSUMING")
need(c["proposed_controls"]["retries_authorized"]==0,"RETRIES_MUST_BE_ZERO")
need(c["proposed_controls"]["token_budget_rule"]=="INPUT_TOKENS_PLUS_4096_MUST_BE_LE_16384","TOKEN_RULE")

need(l["current_counts"]["consumed_slots"]==13,"CONSUMED_SLOTS")
need(l["current_counts"]["next_unconsumed_slot"]["ledger_schedule_rank"]==14,"NEXT_RANK")
need(l["rank14"]["task_started"] is False,"LEDGER_TASK_STARTED")
need(l["rank14"]["execution_authority_consumed"] is False,"LEDGER_AUTH_CONSUMED")
need(l["rank14"]["benchmark_trials_consumed"]==0,"LEDGER_TRIAL_CONSUMED")
need(l["rank14"]["exact_prestart_input_tokens"]==17500,"V2_INPUT_TOKENS")
need(l["rank14"]["exact_context_deficit_tokens"]==5212,"V2_DEFICIT")
need(l["rank14"]["exact_raw_task_obligation_count"]==87,"V2_OBLIGATIONS")

need(m["schema"]=="PROJECT_BRAIN_TB_SCIENCE_TRANSITIVE_RUNTIME_CLOSURE_MANIFEST_V11","V11_SCHEMA")
need(m["closure_file_count"]==15,"V11_COUNT")
need(m["unresolved_dynamic_imports"]==[],"V11_DYNAMIC_IMPORTS")
agent=[x for x in m["closure"] if x["path"]=="canonical/runtime/harbor_science_agent_v1.py"]
need(len(agent)==1 and agent[0]["git_blob_sha"]=="d397324f411d002bdbdca348aaad708b5b40c9c2","V11_AGENT")
need(mv.get("status","").startswith("PASS__V11_15_FILE_TRANSITIVE_CLOSURE_EXACT"),"V11_VERIFY_STATUS")
need(mv["verification"]["missing_paths"]==0,"V11_MISSING")
need(mv["verification"]["mismatched_paths"]==0,"V11_MISMATCHED")
need(mv["verification"]["unresolved_dynamic_imports"]==0,"V11_UNRESOLVED")
need(pv.get("status","").startswith("PASS__87_OF_87_ACCEPTANCE_PRESERVED"),"PROMPT_VERIFY_STATUS")
need(pv["independent_results"]["required_obligations_preserved"]==87,"PROMPT_87_REQUIRED")
need(pv["independent_results"]["accounted_obligations_preserved"]==87,"PROMPT_87_ACCOUNTED")
need(pv["independent_results"]["metadata_reduction_ratio"]>30,"PROMPT_REDUCTION")
need(pv["independent_results"]["brain_full_acceptance_contract_retained"] is True,"PROMPT_FULL_CONTRACT")
need(pv["independent_results"]["planner_acceptance_or_finish_authority"] is False,"PROMPT_PLANNER_AUTHORITY")

need(i["target_obligation"]=="TB_SCIENCE_GE_58_7","INTENT_TARGET")
need(i["current_truth"]["consumed_slots"]==13,"INTENT_CONSUMED")
need(i["current_truth"]["task_started"] is False,"INTENT_TASK_START")
need(i["repaired_route"]["agent_blob"]=="d397324f411d002bdbdca348aaad708b5b40c9c2","INTENT_AGENT")

out={
  "schema":"PROJECT_BRAIN_TB_SCIENCE_RANK14_AUTHORITY_V3_CANDIDATE_PUBLIC_VERIFY_V1",
  "status":"PASS__RANK14_V3_CANDIDATE__V18_LEDGER__V11_CLOSURE__PROMPT_SUMMARY_REPAIR__ZERO_EXPOSURE" if not errors else "FAIL_CLOSED",
  "pass":not errors,
  "errors":errors,
  "candidate_blob":"c740f16395328edad175c234bb7b52b011a2b89f",
  "intent_blob":"70dc5962595a464e4df0b1cfb8f6c49fc160470d",
  "ledger_v18_blob":"566a3756392ee2d4cc41947b66617acbc6f6ce92",
  "v11_closure_blob":"1172b57ac436d64027d06fb4897878ae274febb1",
  "planner_repair_verify_blob":"721c78aabac58565afa37d734705d652073d99ae",
  "execution_authority":False,
  "task_read_authority":False,
  "benchmark_task_exposure":0,
  "benchmark_trials_executed":0,
  "acceptance_credit_delta":0,
  "terminal_credit_delta":0
}
print(json.dumps(out,sort_keys=True))
pathlib.Path("RANK14_AUTHORITY_V3_CANDIDATE_VERIFY.json").write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
raise SystemExit(0 if not errors else 1)
