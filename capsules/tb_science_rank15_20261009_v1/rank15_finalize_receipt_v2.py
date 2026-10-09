from __future__ import annotations
import hashlib, json, os
from pathlib import Path

SCHEMA="PROJECT_BRAIN_TB_SCIENCE_TERMINAL_SLOT_RECEIPT_RANK15_V2"
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
    carrier_ready=os.environ.get("CACHE_READY")=="true"
    success=task_started and reward is not None and reward>=1.0 and not errors

    if not task_started:
        if not carrier_ready:
            errors=["TASK_NOT_STARTED__PREEXPOSURE_ABORT__CARRIER_NOT_QUALIFIED"]
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
        "errors":errors,
        "exception_info":exception_info,
        "harbor_step_outcome":harbor_outcome,
        "public_authority_binding_blob":"710abe99e5ff92c3b0ec0086123edade248a6477",
        "brain_authority_blob":"a292a898231973204f66bf92c3f70ce2bf422449",
        "brain_ledger_blob":"475f56128d6e9f22a540db1f007b2dfe47e723f7",
        "public_ledger_binding_blob":"62eec1814fa9b1682772f096c36200c0069b9f00",
        "epoch_blob":"029fb6e958e8ab451fcd2fa75da64c8cff5f11b6",
        "execution_claim_blob":"fda33be2c4b75ba397a55ee912bbcfab5c5e3c97",
        "workflow_blob":"77b4f822a4785f185453a18a1de69256254736bd",
        "behavior_blob":"5caedddb7b5714fe74c4ba5709a43391e66dcf3a",
        "invariant_registry_blob":"3d156b5b3274ea7fe6542206137ddc7c782903b5",
        "admission_guard_blob":"84d1186b012d51fa5faafa37cf52e87467e80857",
        "runtime_semantic_verification_blob":"30b854d096e597a332cf183394a8b67c84a30e53",
        "prestart_guard_blob":"b296e442535d4cf7770f7c1464da441c80fc65a1",
        "agent_blob":"fb4d8202192ca7a7ff03b36b9ba31be48f19dfa4",
        "planner_blob":"92161f95f211377ed40c11a38e641046bb45bd26",
        "transport_blob":"ec46f648214a37bb16025d5ef2593efdf59f0d79",
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
        "acceptance_credit_delta":1 if success else 0,
        "terminal_credit_delta":0,
    }
    out=root/(safe_id+"__SLOT_RECEIPT_V2.json")
    out.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print(json.dumps(receipt,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
