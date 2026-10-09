from __future__ import annotations
import json, pathlib, urllib.request

ROOT=pathlib.Path(__file__).parent
def load(name): return json.loads((ROOT/name).read_text())
c=load("CANDIDATE.json"); l=load("LEDGER_V17.json"); r=load("REPAIR_VERIFY.json"); v=load("CLOSURE_V10.json")
errors=[]

a=load("AUTHORITY_V2.json"); bv=load("BRAIN_VERIFY.json")
need(a.get("schema")=="PROJECT_BRAIN_TB_SCIENCE_RANK14_ONE_SLOT_EXECUTION_AUTHORITY_V2","AUTHORITY_SCHEMA")
need(a.get("execution_authority") is True,"ACTIVE_EXECUTION_AUTHORITY_REQUIRED")
need(a.get("task_read_authority") is False,"TASK_READ_MUST_WAIT_FOR_FRESH_LEASE")
need(a.get("fresh_reality_authority") is True,"FRESH_REALITY_AUTHORITY")
need(a.get("promotion_authority") is False,"NO_PROMOTION_AUTHORITY")
need(a["state"]["fresh_public_execution_lease_published"] is False,"NO_PRETEND_FRESH_LEASE")
need(a["state"]["authority_consumed"] is False,"AUTHORITY_NOT_CONSUMED")
need(a["ledger"]["rank14_slot_consumed"] is False,"AUTHORITY_SLOT_UNCONSUMED")
need(a["exact_route"]["agent_blob"]=="16e8ab7918c4f8d052698282dddf674b54a23016","AUTHORITY_REPAIRED_AGENT")
need(a["exact_route"]["carrier_closure_blob"]=="ae37559320105277e017ff17af7c3dbeae2f9c27","AUTHORITY_V10_CLOSURE")
need(a["candidate"]["git_blob_sha"]=="e57e8588048b58c7fad5f273608f463bc586be9e","AUTHORITY_CANDIDATE_BINDING")
need(a["candidate"]["verification_git_blob_sha"]=="a7ae7e35e34595e0fcd096a61f410e485b2af268","AUTHORITY_VERIFICATION_BINDING")
need(bv.get("status","").startswith("PASS__REPAIRED_RANK14_AUTHORITY_CANDIDATE_INDEPENDENTLY_VERIFIED"),"BRAIN_VERIFY_PASS")

def need(cond,msg):
    if not cond: errors.append(msg)

need(c.get("schema")=="PROJECT_BRAIN_TB_SCIENCE_RANK14_REPAIRED_ONE_SLOT_AUTHORITY_CANDIDATE_V2","CANDIDATE_SCHEMA")
need(c.get("execution_authority") is False,"CANDIDATE_MUST_NOT_SELF_AUTHORIZE")
need(c.get("task_read_authority") is False,"CANDIDATE_TASK_READ_MUST_BE_FALSE")
need(c.get("promotion_authority") is False,"CANDIDATE_PROMOTION_MUST_BE_FALSE")
need(c["source_bindings"]["ledger"]["git_blob_sha"]=="c8e9720e3f53c0eb483552c902b7841821f335b0","LEDGER_BLOB_BINDING")
need(l.get("schema")=="PROJECT_BRAIN_TB_SCIENCE_CURRENT_SLOT_LEDGER_RECONCILIATION_20261009_V17","LEDGER_SCHEMA")
need(l["current_counts"]["consumed_slots"]==13,"CONSUMED_SLOTS")
need(l["current_counts"]["next_unconsumed_slot"]["ledger_schedule_rank"]==14,"NEXT_RANK")
need(l["rank14_nonconsuming_prestart_truth"]["task_read"] is True,"TASK_READ_TRUTH")
need(l["rank14_nonconsuming_prestart_truth"]["task_started"] is False,"TASK_START_FALSE")
need(l["rank14_nonconsuming_prestart_truth"]["benchmark_trials_consumed"]==0,"TRIALS_ZERO")
need(l["rank14_nonconsuming_prestart_truth"]["execution_authority_consumed"] is False,"AUTHORITY_UNCONSUMED")
need(l["rank14"]["slot_consumed"] is False,"SLOT_UNCONSUMED")
need(l["rank14"]["old_v9_authority_reusable"] is False,"OLD_AUTHORITY_FORBIDDEN")
need(r.get("status","").startswith("PASS__FALSE_64_OBLIGATION_CEILING_REMOVED"),"REPAIR_VERIFY_PASS")
need(r["exact_repair_blobs"]["agent"]=="16e8ab7918c4f8d052698282dddf674b54a23016","REPAIRED_AGENT")
need(r["public_independent_verification"]["large_required_obligations"]==80,"REPAIR_80_REQUIRED")
need(r["public_independent_verification"]["large_accounted_obligations"]==80,"REPAIR_80_ACCOUNTED")
need(v.get("schema")=="PROJECT_BRAIN_TB_SCIENCE_TRANSITIVE_RUNTIME_CLOSURE_MANIFEST_V10","V10_SCHEMA")
need(v["closure_file_count"]==15,"V10_FILE_COUNT")
need(v["unresolved_dynamic_imports"]==[],"V10_DYNAMIC_IMPORTS")
agent=[x for x in v["closure"] if x["path"]=="canonical/runtime/harbor_science_agent_v1.py"]
need(len(agent)==1 and agent[0]["git_blob_sha"]=="16e8ab7918c4f8d052698282dddf674b54a23016","V10_AGENT_BINDING")
need(c["exact_route"]["agent_blob"]=="16e8ab7918c4f8d052698282dddf674b54a23016","CANDIDATE_AGENT")
need(c["exact_route"]["v10_closure_blob"]=="ae37559320105277e017ff17af7c3dbeae2f9c27","CANDIDATE_V10_BLOB")
need(c["controls"]["precheck_failure_consumes_slot"] is False,"PRECHECK_NONCONSUMING")
need(c["controls"]["retries_after_task_start"]==0,"NO_POSTSTART_RETRY")
need(c["verified_preconditions"]["rank14_trial_consumed"] is False,"UNCONSUMED_PRECONDITION")

for run_id, expected_conclusion in [(37880547075,"success"),(37881878913,"success")]:
    with urllib.request.urlopen(f"https://api.github.com/repos/moxnixmdj/verification-capsule-runner/actions/runs/{run_id}") as resp:
        obj=json.load(resp)
    need(obj.get("status")=="completed",f"RUN_{run_id}_COMPLETED")
    need(obj.get("conclusion")==expected_conclusion,f"RUN_{run_id}_CONCLUSION")

result={
  "schema":"PROJECT_BRAIN_TB_SCIENCE_RANK14_REPAIRED_AUTHORITY_CANDIDATE_PUBLIC_VERIFY_V1",
  "pass":not errors,
  "status":"PASS__REPAIRED_RANK14_ACTIVE_AUTHORITY_EXACT_BINDINGS_VERIFIED__TASK_READ_STILL_LEASE_GATED" if not errors else "FAIL_CLOSED",
  "errors":errors,
  "ledger_blob":"c8e9720e3f53c0eb483552c902b7841821f335b0",
  "candidate_blob":"e57e8588048b58c7fad5f273608f463bc586be9e",
  "repair_blob":"6e8e3938b00e3fe39e38ac4a1b38a21eeb25c96f",
  "v10_closure_blob":"ae37559320105277e017ff17af7c3dbeae2f9c27",
  "public_runs_verified":[37880547075,37881878913],
  "active_authority_blob":"65bad902596c39b98acbd81446fb1014437ef8f3",
  "brain_verification_blob":"a7ae7e35e34595e0fcd096a61f410e485b2af268",
  "execution_authority":True,
  "task_read_authority":False,
  "task_start_authority":False,
  "benchmark_trials_consumed_delta":0,
  "acceptance_credit_delta":0,
  "terminal_credit_delta":0,
}
print(json.dumps(result,sort_keys=True))
pathlib.Path("RANK14_REPAIRED_AUTHORITY_VERIFY_RESULT.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
raise SystemExit(0 if not errors else 1)
