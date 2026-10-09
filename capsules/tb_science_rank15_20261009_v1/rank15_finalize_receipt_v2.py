from __future__ import annotations
import hashlib,json,os
from pathlib import Path

SCHEMA="PROJECT_BRAIN_TB_SCIENCE_TERMINAL_SLOT_RECEIPT_RANK15_V2"
SLOT="terminal-bench-science/protein-active-learning::trial-0"
TASK="terminal-bench-science/protein-active-learning"
DIGEST="sha256:d7e16b7c468551b468364cf2a86dba2383b007f3f2f01c6d2ce01d99ff30d48f"

def main()->int:
    root=Path(os.environ.get("GITHUB_WORKSPACE") or ".").resolve()
    safe=os.environ.get("SAFE_ID") or "protein-active-learning-trial-0"
    base=root/"jobs"/safe
    try: guard=json.loads((root/"RANK15_PRESTART_GUARD.json").read_text())
    except Exception: guard={}
    results=[]
    for p in base.rglob("result.json") if base.exists() else []:
        try: results.append((p,json.loads(p.read_text())))
        except Exception: pass
    scored=[]
    exception_info=[]
    for p,obj in results:
        vr=obj.get("verifier_result")
        if isinstance(vr,dict) and isinstance(vr.get("rewards"),dict): scored.append((p,obj))
        ex=obj.get("exception_info")
        if isinstance(ex,dict):
            exception_info.append({"path":str(p.relative_to(root)),"exception_type":ex.get("exception_type"),"exception_message":ex.get("exception_message")})
    reward=None
    errors=[]
    if len(scored)==1:
        raw=scored[0][1]["verifier_result"]["rewards"].get("reward")
        if isinstance(raw,(int,float)) and not isinstance(raw,bool): reward=float(raw)
        else: errors.append("REWARD_MISSING_OR_NONNUMERIC")
    elif not scored: errors.append("NO_TRIAL_RESULT_WITH_VERIFIER_REWARD")
    else: errors.append("MULTIPLE_TRIAL_RESULTS_WITH_VERIFIER_REWARD")
    harbor=os.environ.get("HARBOR_OUTCOME") or "skipped"
    task_started=harbor in {"success","failure"}
    carrier_ready=os.environ.get("CACHE_READY")=="true"
    success=task_started and reward is not None and reward>=1.0 and not errors
    if not task_started:
        if not carrier_ready: errors=["TASK_NOT_STARTED__PREEXPOSURE_ABORT__CARRIER_NOT_READY"]
        elif guard.get("task_read") is True: errors=["TASK_NOT_STARTED__PREEXPOSURE_ABORT__TOKEN_OR_GUARD"]
        else: errors=["TASK_NOT_STARTED__PREEXPOSURE_ABORT"]
    hashes={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p,_ in results}
    receipt={
      "schema":SCHEMA,
      "slot_id":SLOT,"task_name":TASK,"task_digest":DIGEST,
      "status":"PREEXPOSURE_ABORT_NONCONSUMING" if not task_started else ("SUCCESS" if success else "FINAL_ZERO"),
      "reward":None if not task_started else (reward if reward is not None else 0.0),
      "carrier_ready":carrier_ready,
      "task_read":bool(guard.get("task_read")),
      "task_started":task_started,
      "prestart_guard_status":guard.get("status"),
      "prestart_guard_pass":guard.get("pass"),
      "prestart_input_tokens":guard.get("input_tokens"),
      "prestart_context_headroom_tokens":guard.get("context_headroom_tokens"),
      "prestart_instruction_sha256":guard.get("instruction_sha256"),
      "prestart_first_cycle_prompt_sha256":guard.get("first_cycle_prompt_sha256"),
      "raw_task_obligation_count":guard.get("raw_task_obligation_count"),
      "logical_attempt_id":guard.get("logical_attempt_id"),
      "seed":guard.get("seed"),
      "request_identity_sha256":guard.get("request_identity_sha256"),
      "errors":errors,"exception_info":exception_info,"harbor_step_outcome":harbor,
      "public_authority_binding_blob":"a3907605eeb818a9e89d5ecbba02991601fd53c0",
      "brain_authority_blob":"a292a898231973204f66bf92c3f70ce2bf422449",
      "brain_authority_verification_blob":"87250e14dc83ad792671d5087adc7de99dc367d5",
      "brain_ledger_v21_blob":"475f56128d6e9f22a540db1f007b2dfe47e723f7",
      "epoch_v2_blob":"2653e53826dceab82a3717148965f025dd69478a",
      "execution_claim_v2_blob":"ac0db733ddfbbcc71a314bfdf1d024dd06bef7f8",
      "preflight_v2_blob":"b665e9a375d7e71a68e8fcc2d59afe0e685e78fc",
      "workflow_v2_pre_reseal_blob":"13d9e4a402b10f43d22b7c8cdbc80ec9e75dffb9",
      "agent_v2_blob":"fb4d8202192ca7a7ff03b36b9ba31be48f19dfa4",
      "planner_v2_blob":"92161f95f211377ed40c11a38e641046bb45bd26",
      "prestart_guard_v2_blob":"b296e442535d4cf7770f7c1464da441c80fc65a1",
      "qwen_model_sha256":"f41c0a0c0e43bf721fb2da29374cd1a97271bac0bab08a9dc42964525e82350c",
      "llama_cpp_commit":"bec4772f6a2527d371557b5d2032641e5ff7619c",
      "server_context_tokens":16384,"reserved_completion_tokens":4096,
      "github_run_id":os.environ.get("GITHUB_RUN_ID"),"github_run_attempt":os.environ.get("GITHUB_RUN_ATTEMPT"),"github_sha":os.environ.get("GITHUB_SHA"),
      "result_hashes":hashes,
      "execution_authority_consumed":task_started,
      "benchmark_trials_consumed":1 if task_started else 0,
      "rerun_credit":False,"incremental_spend_usd":0,"promotion_authority":False,
      "terminal_credit_delta":0
    }
    (root/(safe+"__SLOT_RECEIPT_V2.json")).write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print(json.dumps(receipt,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
