from __future__ import annotations
import hashlib, json, os
from pathlib import Path

SCHEMA="PROJECT_BRAIN_TB_SCIENCE_TERMINAL_SLOT_RECEIPT_RANK15_V1"
SLOT="terminal-bench-science/protein-active-learning::trial-0"
TASK="terminal-bench-science/protein-active-learning"
DIGEST="sha256:d7e16b7c468551b468364cf2a86dba2383b007f3f2f01c6d2ce01d99ff30d48f"

def main() -> int:
    root=Path(os.environ.get("GITHUB_WORKSPACE") or ".").resolve()
    safe_id=os.environ.get("SAFE_ID") or "protein-active-learning-trial-0"
    base=root/"jobs"/safe_id
    guard_path=root/"RANK15_PRESTART_GUARD.json"
    try:
        guard=json.loads(guard_path.read_text())
    except Exception:
        guard={}

    results=[]
    for p in base.rglob("result.json") if base.exists() else []:
        try:
            obj=json.loads(p.read_text())
        except Exception:
            continue
        results.append((p,obj))

    scored=[]
    exception_info=[]
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

    reward=None
    errors=[]
    if len(scored)==1:
        raw=scored[0][1]["verifier_result"]["rewards"].get("reward")
        if isinstance(raw,(int,float)) and not isinstance(raw,bool):
            reward=float(raw)
        else:
            errors.append("REWARD_MISSING_OR_NONNUMERIC")
    elif not scored:
        errors.append("NO_TRIAL_RESULT_WITH_VERIFIER_REWARD")
    else:
        errors.append("MULTIPLE_TRIAL_RESULTS_WITH_VERIFIER_REWARD")

    harbor_outcome=os.environ.get("HARBOR_OUTCOME") or "skipped"
    task_started=harbor_outcome in {"success","failure"}
    cache_ready=os.environ.get("CACHE_READY")=="true"
    success=task_started and reward is not None and reward>=1.0 and not errors

    if not task_started:
        if not cache_ready:
            errors=["TASK_NOT_STARTED__PREEXPOSURE_ABORT__CARRIER_CACHE_MISS"]
        elif guard.get("task_read") is True:
            errors=["TASK_NOT_STARTED__PREEXPOSURE_ABORT__TOKEN_OR_GUARD"]
        else:
            errors=["TASK_NOT_STARTED__PREEXPOSURE_ABORT"]

    hashes={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p,_ in results}
    status="PREEXPOSURE_ABORT_NONCONSUMING" if not task_started else ("SUCCESS" if success else "FINAL_ZERO")
    receipt={
        "schema":SCHEMA,
        "slot_id":SLOT,
        "task_name":TASK,
        "task_digest":DIGEST,
        "status":status,
        "reward":None if not task_started else (reward if reward is not None else 0.0),
        "cache_ready":cache_ready,
        "task_read":bool(guard.get("task_read")),
        "task_started":task_started,
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
        "authority_blob":"61629b854f4be1e940a3f68d1a676e40b4e61ebf",
        "intent_blob":"ce2c7aeb17c450e17b02a3b616ce8a8374edabe4",
        "authority_verification_blob":"75f2ca9b52e256e13551977e99784dca868c11a7",
        "ledger_v19_blob":"c9b887ac4fb57046be666492748d25ca96056378",
        "epoch_blob":"ad0c76996163e5ee75553af7a9c00276dbe607c9",
        "execution_claim_blob":"a37da97fbc06ffdbb937996eaf1615dd56af1c0d",
        "closure_manifest_blob":"8008b1e2382c1235e3b788e0f8d4ab9a48487409",
        "closure_verification_blob":"2f604985baa7f88c61b23958d59dc2ecd4c0990b",
        "frozen_requirements_repair_verification_blob":"d60c84676de7dfa090810b3b65132d324ac49f38",
        "prestart_guard_blob":"0139a20070cd1a51866c309bac1976b27ce7ac0d",
        "agent_blob":"e7e258f567499bd7356c0276d6293aa30dbd338c",
        "planner_blob":"58964dc8d6b5eed5c202081cd800035c791eeb1d",
        "command_policy_blob":"a525773417291c7a4841bf35e1baff5370350d0d",
        "qwen_model_sha256":"f41c0a0c0e43bf721fb2da29374cd1a97271bac0bab08a9dc42964525e82350c",
        "llama_cpp_commit":"bec4772f6a2527d371557b5d2032641e5ff7619c",
        "server_context_tokens":16384,
        "reserved_completion_tokens":4096,
        "strict_timeout_semantics":"SUCCESS_IS_EXACT_POSITIVE_EVIDENCE__ANY_FINAL_NON_SUCCESS_AFTER_TASK_START_COUNTS_ZERO",
        "github_run_id":os.environ.get("GITHUB_RUN_ID"),
        "github_run_attempt":os.environ.get("GITHUB_RUN_ATTEMPT"),
        "github_sha":os.environ.get("GITHUB_SHA"),
        "result_hashes":hashes,
        "execution_authority_consumed":task_started,
        "benchmark_trials_consumed":1 if task_started else 0,
        "rerun_credit":False,
        "incremental_spend_usd":0,
        "promotion_authority":False,
    }
    out=root/(safe_id+"__SLOT_RECEIPT_V1.json")
    out.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print(json.dumps(receipt,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
