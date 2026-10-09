from __future__ import annotations
import hashlib, json, os
from pathlib import Path

SCHEMA="PROJECT_BRAIN_TB_SCIENCE_TERMINAL_SLOT_RECEIPT_RANK15_V3"
SLOT="terminal-bench-science/protein-active-learning::trial-0"
TASK="terminal-bench-science/protein-active-learning"
DIGEST="sha256:d7e16b7c468551b468364cf2a86dba2383b007f3f2f01c6d2ce01d99ff30d48f"

def _load(path: Path) -> dict:
    try:
        value=json.loads(path.read_text())
        return value if isinstance(value,dict) else {}
    except Exception:
        return {}

def main() -> int:
    root=Path(os.environ.get("GITHUB_WORKSPACE") or ".").resolve()
    safe_id=os.environ.get("SAFE_ID") or "protein-active-learning-trial-0"
    base=root/"jobs"/safe_id
    guard=_load(root/"RANK15_PRESTART_GUARD.json")
    cas=_load(root/"TERMINAL_SLOT_START_CAS_RECEIPT.json")
    surface=_load(root/"execution_guard/CURRENT_TERMINAL_EXECUTION_SURFACE_V1.json")

    results=[]
    for p in base.rglob("result.json") if base.exists() else []:
        try: obj=json.loads(p.read_text())
        except Exception: continue
        if isinstance(obj,dict): results.append((p,obj))

    scored=[]; exception_info=[]
    for p,obj in results:
        vr=obj.get("verifier_result")
        if isinstance(vr,dict) and isinstance(vr.get("rewards"),dict):
            scored.append((p,obj))
        ex=obj.get("exception_info")
        if isinstance(ex,dict):
            exception_info.append({
                "path":str(p.relative_to(root)),
                "exception_type":ex.get("exception_type"),
                "exception_message":ex.get("exception_message"),
            })

    reward=None; errors=[]
    if len(scored)==1:
        raw=scored[0][1]["verifier_result"]["rewards"].get("reward")
        if isinstance(raw,(int,float)) and not isinstance(raw,bool): reward=float(raw)
        else: errors.append("REWARD_MISSING_OR_NONNUMERIC")
    elif not scored: errors.append("NO_TRIAL_RESULT_WITH_VERIFIER_REWARD")
    else: errors.append("MULTIPLE_TRIAL_RESULTS_WITH_VERIFIER_REWARD")

    harbor_outcome=os.environ.get("HARBOR_OUTCOME") or "skipped"
    carrier_ready=os.environ.get("CARRIER_READY")=="true"
    cas_committed=(
        cas.get("status")=="TASK_START_INTENT_COMMITTED"
        and cas.get("slot_id")==SLOT
        and cas.get("task_digest")==DIGEST
    )
    harbor_reported_start=harbor_outcome in {"success","failure"}

    if not cas_committed:
        status="PREEXPOSURE_ABORT_NONCONSUMING"
        errors=["TASK_START_CAS_NOT_COMMITTED__NO_SLOT_CONSUMPTION"]
        consumed=0; successes=0; failures=0; success=False
    else:
        consumed=1
        success=(harbor_outcome=="success" and reward is not None and reward>=1.0 and not errors)
        successes=1 if success else 0
        failures=0 if success else 1
        if success:
            status="SUCCESS"
        elif harbor_reported_start:
            status="FINAL_ZERO"
        else:
            status="FINAL_ZERO__START_INTENT_COMMITTED__START_OUTCOME_UNCERTAIN__NO_REPLAY"
            errors=["START_INTENT_COMMITTED__START_OUTCOME_UNCERTAIN__CONSERVATIVE_FINAL_ZERO"]

    hashes={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p,_ in results}
    receipt={
        "schema":SCHEMA,
        "slot_id":SLOT,
        "task_name":TASK,
        "task_digest":DIGEST,
        "status":status,
        "reward":reward if cas_committed else None,
        "carrier_ready":carrier_ready,
        "task_read":bool(guard.get("task_read")),
        "task_started":True if harbor_reported_start else (None if cas_committed else False),
        "task_start_outcome_uncertain":bool(cas_committed and not harbor_reported_start),
        "start_cas_committed":cas_committed,
        "start_cas_key":cas.get("key"),
        "logical_attempt_id":cas.get("logical_attempt_id") or guard.get("logical_attempt_id"),
        "prestart_guard_status":guard.get("status"),
        "prestart_guard_pass":guard.get("pass"),
        "prestart_input_tokens":guard.get("input_tokens"),
        "prestart_context_headroom_tokens":guard.get("context_headroom_tokens"),
        "prestart_instruction_sha256":guard.get("instruction_sha256"),
        "prestart_first_cycle_prompt_sha256":guard.get("first_cycle_prompt_sha256"),
        "raw_task_obligation_count":guard.get("raw_task_obligation_count"),
        "errors":errors,
        "exception_info":exception_info,
        "harbor_step_outcome":harbor_outcome,
        "surface_status":surface.get("status"),
        "workflow_blob":surface.get("workflow_git_blob_sha"),
        "authority_binding":surface.get("authority"),
        "ledger_binding":surface.get("ledger"),
        "epoch_binding":surface.get("epoch"),
        "execution_claim_binding":surface.get("execution_claim"),
        "planner_binding":surface.get("planner"),
        "agent_binding":surface.get("agent"),
        "prestart_binding":surface.get("prestart_guard"),
        "start_cas_binding":surface.get("start_cas"),
        "qwen_model_sha256":"f41c0a0c0e43bf721fb2da29374cd1a97271bac0bab08a9dc42964525e82350c",
        "llama_cpp_commit":"bec4772f6a2527d371557b5d2032641e5ff7619c",
        "server_context_tokens":16384,
        "reserved_completion_tokens":4096,
        "github_run_id":os.environ.get("GITHUB_RUN_ID"),
        "github_run_attempt":os.environ.get("GITHUB_RUN_ATTEMPT"),
        "github_sha":os.environ.get("GITHUB_SHA"),
        "result_hashes":hashes,
        "execution_authority_consumed":cas_committed,
        "benchmark_trials_consumed":consumed,
        "consumed_successes_delta":successes,
        "consumed_final_failures_delta":failures,
        "rerun_credit":False,
        "replacement_carrier_authority":False,
        "incremental_spend_usd":0,
        "promotion_authority":False,
        "acceptance_credit_delta":0,
        "terminal_credit_delta":0,
    }
    out=root/(safe_id+"__SLOT_RECEIPT_V3.json")
    out.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print(json.dumps(receipt,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
