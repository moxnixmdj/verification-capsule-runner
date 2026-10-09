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
        if isinstance(ex,dict): exception_info.append({"path":str(p.relative_to(root)),"exception_type":ex.get("exception_type"),"exception_message":ex.get("exception_message")})
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
    carrier_ready=os.environ.get("CARRIER_READY")=="true"
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
      "errors":errors,"exception_info":exception_info,"harbor_step_outcome":harbor,
      "authority_blob":"52a5ccf4f44f40a84b6f2477e3e1f6859ac43bee",
      "authority_verification_blob":"937e4b398c6cd620618bd4327aec6b33bd7791aa",
      "ledger_v20_blob":"6cbe4022917bd214d69a7596f3f90d5208c4ad66",
      "epoch_v2_blob":"3ead70cc5c625b5523292de6f43446a836944a87",
      "execution_claim_v2_blob":"f377aba4612ed86330c2de05d5adbec3aeb922c6",
      "preflight_v2_blob":"250f550b653561baf5d7c98726a6e9562abb56cf",
      "agent_blob":"e7e258f567499bd7356c0276d6293aa30dbd338c",
      "planner_blob":"58964dc8d6b5eed5c202081cd800035c791eeb1d",
      "command_policy_blob":"a525773417291c7a4841bf35e1baff5370350d0d",
      "qwen_model_sha256":"f41c0a0c0e43bf721fb2da29374cd1a97271bac0bab08a9dc42964525e82350c",
      "llama_cpp_commit":"bec4772f6a2527d371557b5d2032641e5ff7619c",
      "llama_binary_policy":"CLEAN_BUILD_ON_LIVE_RUNNER",
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
