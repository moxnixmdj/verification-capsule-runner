from __future__ import annotations
import hashlib, json, urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parent
CAP=ROOT/"capsules/toolathlon_carrier_cut_v1"
COMMIT="9be8d8fe07a497b18ee61e3f2ae694e9797f39eb"
EXPECTED={
    "EVAL_SERVICE_README.md":"28633f85a9fb862bfe4e9a0d419b7f046d68a6d7",
    "eval_client.py":"1c0b7d9611e12c419b94f39dd43f14da5e6c95fe",
    "simple_client_ws.py":"a959b48c114d1bdfe30272b831f1426bc17a7aeb",
}

def git_blob(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def local_blob(name:str)->str:
    return git_blob((CAP/name).read_bytes())

def fetch(path:str)->bytes:
    url=f"https://raw.githubusercontent.com/hkust-nlp/Toolathlon/{COMMIT}/{path}"
    req=urllib.request.Request(url,headers={"User-Agent":"project-brain-carrier-verifier/1.0"})
    with urllib.request.urlopen(req,timeout=60) as r:
        return r.read()

def main()->int:
    assert local_blob("BRAIN_PR1173_CANDIDATE_EXACT.json")=="70e5426dc9ef82f22b37d32aeeb36c1ba4139b06"
    assert local_blob("PUBLIC_STANDARD_RUNNER_ZERO_COST_CARRIER_V1_EXACT.json")=="79f61579c8520b55877f5f99fd6a24a30e064c2e"
    assert local_blob("LOCAL_QWEN3_5_9B_BIOPHYSICS_TASK_B_FALSIFICATION_20260929_V1_EXACT.json")=="405f7059c1ae4387cea61ff23b7adb227dac4351"

    candidate=json.loads((CAP/"BRAIN_PR1173_CANDIDATE_EXACT.json").read_text())
    base=json.loads((CAP/"PUBLIC_STANDARD_RUNNER_ZERO_COST_CARRIER_V1_EXACT.json").read_text())
    qwen=json.loads((CAP/"LOCAL_QWEN3_5_9B_BIOPHYSICS_TASK_B_FALSIFICATION_20260929_V1_EXACT.json").read_text())

    assert candidate["execution_authority"] is False
    assert candidate["promotion_authority"] is False
    assert candidate["capability_credit_delta"]==0 and candidate["family_credit_delta"]==0
    assert candidate["terminal_results_observed"]==0
    assert candidate["service_limit_truth"]["public_service_is_durable_capacity_guarantee"] is False
    assert candidate["service_limit_truth"]["current_service_admission_proved"] is False
    assert candidate["service_limit_truth"]["full_job_completion_under_240_minutes_proved"] is False

    assert base["status"].startswith("VERIFIED_ZERO_INCREMENTAL_SPEND_CARRIER")
    assert base["carrier"]["repository_visibility"]=="public"
    assert base["carrier"]["paid_or_larger_runners"]=="FORBIDDEN"
    assert base["incremental_spend_usd"]==0
    assert candidate["already_verified_inputs"]["zero_cost_public_runner"]["git_blob_sha"]==local_blob("PUBLIC_STANDARD_RUNNER_ZERO_COST_CARRIER_V1_EXACT.json")

    assert qwen["execution"]["incremental_spend_usd"]==0
    assert qwen["exact_route"]["hosted_frontier_model_in_execution_path"] is False
    assert qwen["exact_route"]["quantization_bytes"]==5060174144
    assert qwen["exact_route"]["quantization_sha256"]=="f41c0a0c0e43bf721fb2da29374cd1a97271bac0bab08a9dc42964525e82350c"
    for k in ["llama_cpp_build_and_commit_pin","model_download_bytes_and_sha256","model_server_health","local_external_planner_bridge"]:
        assert qwen["verified_passes"][k] is True
    assert qwen["terminal_result"]["real_task_completed"] is False
    assert qwen["terminal_result"]["frontier_capability_promoted"] is False
    assert candidate["already_verified_inputs"]["pinned_local_substrate_fit_receipt"]["git_blob_sha"]==local_blob("LOCAL_QWEN3_5_9B_BIOPHYSICS_TASK_B_FALSIFICATION_20260929_V1_EXACT.json")

    fetched={}
    for path,sha in EXPECTED.items():
        data=fetch(path)
        observed=git_blob(data)
        assert observed==sha,(path,observed,sha)
        assert candidate["frozen_toolathlon_private_mode_transport"]["exact_blobs"][path]==sha
        fetched[path]=data

    readme=fetched["EVAL_SERVICE_README.md"].decode("utf-8")
    required=[
        "Private Mode (Local OpenAI-ChatCompletion endpoint via vLLM/SGLang etc)",
        "--mode private",
        "--base-url http://localhost:8000/v1",
        "--api-key dummy",
        "Duration limit",
        "180 minutes",
        "Server never sees your credentials",
        "WebSocket proxy",
        "Timeout: 240 minutes",
    ]
    missing=[x for x in required if x not in readme]
    assert not missing,missing

    deleted=set(candidate["deleted_carrier_obligations"])
    assert "PROVISION_TOOLATHLON_MCP_APP_ACCOUNTS_OR_SECRETS_ON_BRAIN_RUNNER" in deleted
    assert "USE_PAID_HOSTED_MODEL_OR_API_FOR_TOOLATHLON_INFERENCE" in deleted
    stages=candidate["atomic_execution_rule"]
    assert "ALL_STAGE_A_CARRIER_PREFLIGHTS_PASS" in stages["stage_b_terminal_gate"]
    assert "TOOLATHLON_MATCHED_SCOPE_COMPOSITION_CERTIFICATE__INDEPENDENT_PASS" in stages["stage_b_terminal_gate"]
    assert "OPUS55_TOOLATHLON_MATCHED_REFERENCE_BAR__INDEPENDENT_PASS" in stages["stage_b_terminal_gate"]

    verdict={
        "schema":"PROJECT_BRAIN_TOOLATHLON_ZERO_COST_CARRIER_CUT_PUBLIC_VERDICT_V1",
        "status":"PASS__ZERO_REALITY_CARRIER_REDUCTION__PRIVATE_MODE_SOURCE_BOUND__FULL_CARRIER_STILL_OPEN",
        "brain_candidate_git_blob_sha":"70e5426dc9ef82f22b37d32aeeb36c1ba4139b06",
        "frozen_toolathlon_commit":COMMIT,
        "frozen_toolathlon_blob_shas":EXPECTED,
        "verified_reduction":[
            "PUBLIC_RUNNER_ZERO_COST_BASE_REUSED",
            "PINNED_LOCAL_QWEN_LLAMA_TRANSPORT_FIT_REUSED_WITH_ZERO_CAPABILITY_CREDIT",
            "OFFICIAL_TOOLATHLON_PRIVATE_MODE_REMOVES_NEED_TO_SELF_HOST_MCP_APP_STACK_ON_BRAIN_RUNNER",
            "LOCAL_ENDPOINT_NEED_NOT_BE_PUBLICLY_ACCESSIBLE",
            "PAID_MODEL_API_NOT_REQUIRED_BY_THE_ROUTE",
            "POINT_OF_USE_LIVE_ADMISSION_AND_OPENAI_TOOL_CALL_COMPATIBILITY_REMAIN_OPEN",
        ],
        "carrier_fact_fully_closed":False,
        "terminal_execution_authorized":False,
        "terminal_results_observed":0,
        "incremental_spend_usd":0,
        "capability_credit_delta":0,
        "family_credit_delta":0,
    }
    Path("TOOLATHLON_ZERO_COST_CARRIER_CUT_PUBLIC_VERDICT_V1.json").write_text(json.dumps(verdict,indent=2,sort_keys=True)+"\n")
    print(json.dumps(verdict,indent=2,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
