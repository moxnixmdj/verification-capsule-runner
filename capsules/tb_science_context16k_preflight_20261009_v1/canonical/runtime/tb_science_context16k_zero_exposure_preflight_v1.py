"""Zero-benchmark-exposure 16K-context live planner gate for TB-Science V9.

Never reads, enumerates, downloads, or executes benchmark task content.
Uses synthetic inert text to force the exact current planner request above the
observed rank13 9202-token failure boundary while retaining exact structured
multi-action tool-call validation.
"""
from __future__ import annotations
import json
from typing import Any
from canonical.runtime import harbor_science_planner_v1 as planner

SCHEMA="PROJECT_BRAIN_TB_SCIENCE_CONTEXT16K_ZERO_EXPOSURE_PREFLIGHT_V1"
TARGET_MIN_INPUT_TOKENS=10000
TARGET_MAX_INPUT_TOKENS=10200
OBSERVED_RANK13_FAILURE_TOKENS=9202
SERVER_CONTEXT_TOKENS=16384
MAX_FILLER_UNITS=18000
MAX_SEARCH_CALLS=24
REQUESTED_TIMEOUT_S=300

_BASE=(
 "ZERO-BENCHMARK-EXPOSURE CONTEXT-CAPACITY PREFLIGHT. "
 "Synthetic control-plane data only. Never infer benchmark or scientific content. "
 "Use exactly material requirements PRECHECK_A, PRECHECK_B, PRECHECK_C. "
 "Return exactly three harmless local candidates. "
 "PREFLIGHT_A covers PRECHECK_A with command 'printf preflight-a' and verify_command 'printf verify-a'. "
 "PREFLIGHT_B covers PRECHECK_B, depends_on exactly ['PREFLIGHT_A'], timeout_sec 1200, "
 "verify_timeout_sec 300, command 'printf preflight-b', verify_command 'printf verify-b'. "
 "PREFLIGHT_C covers PRECHECK_C, no dependency, command 'printf preflight-c', verify_command 'printf verify-c'. "
 "No files, network, packages, benchmark content, or secrets.\n"
)
_FILLER="SYNTHETIC_INERT_CONTEXT_CAPACITY_UNIT "

class PreflightError(RuntimeError): pass

def _prompt(units:int)->str:
    if not isinstance(units,int) or isinstance(units,bool) or units<0:
        raise PreflightError("PREFLIGHT_FILLER_UNITS_INVALID")
    return _BASE+(_FILLER*units)

def _input_tokens(prompt:str)->int:
    return planner.count_input_tokens(planner._request_payload(prompt))

def select_prompt()->tuple[str,int,int]:
    calls=0; lo=0; hi=MAX_FILLER_UNITS
    hi_tokens=_input_tokens(_prompt(hi)); calls+=1
    if hi_tokens<TARGET_MIN_INPUT_TOKENS: raise PreflightError("PREFLIGHT_TARGET_UNREACHABLE")
    best=None
    while lo<=hi and calls<MAX_SEARCH_CALLS:
        mid=(lo+hi)//2
        candidate=_prompt(mid)
        tokens=_input_tokens(candidate); calls+=1
        if tokens>=TARGET_MIN_INPUT_TOKENS:
            best=(candidate,tokens); hi=mid-1
        else: lo=mid+1
    if best is None: raise PreflightError("PREFLIGHT_PROMPT_SELECTION_FAILED")
    prompt,tokens=best
    if tokens>TARGET_MAX_INPUT_TOKENS:
        raise PreflightError(f"PREFLIGHT_TARGET_WINDOW_OVERSHOT:{tokens}>{TARGET_MAX_INPUT_TOKENS}")
    return prompt,tokens,calls

def _validate(text:str)->dict[str,Any]:
    obj=planner.normalize_proposal_object(planner.extract_json_object(text))
    if obj.get("material_requirements")!=["PRECHECK_A","PRECHECK_B","PRECHECK_C"]:
        raise PreflightError("MATERIAL_REQUIREMENTS_NOT_EXACT")
    rows=obj.get("candidates")
    if not isinstance(rows,list) or len(rows)!=3: raise PreflightError("EXACTLY_THREE_CANDIDATES_REQUIRED")
    by={r.get("action_id"):r for r in rows if isinstance(r,dict)}
    if set(by)!={"PREFLIGHT_A","PREFLIGHT_B","PREFLIGHT_C"}: raise PreflightError("ACTION_IDS_NOT_EXACT")
    expected={
      "PREFLIGHT_A":{"covers":["PRECHECK_A"],"command":"printf preflight-a","verify_command":"printf verify-a"},
      "PREFLIGHT_B":{"covers":["PRECHECK_B"],"depends_on":["PREFLIGHT_A"],"timeout_sec":1200,"verify_timeout_sec":300,"command":"printf preflight-b","verify_command":"printf verify-b"},
      "PREFLIGHT_C":{"covers":["PRECHECK_C"],"command":"printf preflight-c","verify_command":"printf verify-c"},
    }
    for aid,fields in expected.items():
        for k,v in fields.items():
            if by[aid].get(k)!=v: raise PreflightError(f"FIELD_NOT_EXACT:{aid}:{k}")
    return obj

def run_preflight()->dict[str,Any]:
    prompt,tokens,calls=select_prompt()
    if tokens<=OBSERVED_RANK13_FAILURE_TOKENS: raise PreflightError("NO_HEADROOM_OVER_RANK13")
    if tokens+planner.MAX_TOOL_COMPLETION_TOKENS>SERVER_CONTEXT_TOKENS:
        raise PreflightError("INPUT_PLUS_MAX_OUTPUT_EXCEEDS_SERVER_CONTEXT")
    expected=planner.effective_timeout_s(tokens,REQUESTED_TIMEOUT_S)
    out=planner.plan(prompt,timeout_s=REQUESTED_TIMEOUT_S)
    if out.get("input_tokens")!=tokens: raise PreflightError("TOKEN_COUNT_DRIFT")
    if out.get("effective_timeout_s")!=expected: raise PreflightError("TIMEOUT_DRIFT")
    proposal=_validate(str(out.get("text") or ""))
    return {
      "schema":SCHEMA,
      "status":"PASS__ZERO_BENCHMARK_EXPOSURE__CONTEXT16K_ACCEPTS_GT9202_MULTI_ACTION_REQUEST",
      "pass":True,
      "benchmark_task_exposure":0,
      "benchmark_trials_executed":0,
      "scientific_capability_credit":0,
      "acceptance_credit_delta":0,
      "terminal_credit_delta":0,
      "observed_rank13_failure_tokens":OBSERVED_RANK13_FAILURE_TOKENS,
      "server_context_tokens":SERVER_CONTEXT_TOKENS,
      "target_min_input_tokens":TARGET_MIN_INPUT_TOKENS,
      "target_max_input_tokens":TARGET_MAX_INPUT_TOKENS,
      "selected_input_tokens":tokens,
      "input_headroom_over_rank13":tokens-OBSERVED_RANK13_FAILURE_TOKENS,
      "reserved_max_output_tokens":planner.MAX_TOOL_COMPLETION_TOKENS,
      "context_headroom_after_input_plus_reserved_output":SERVER_CONTEXT_TOKENS-tokens-planner.MAX_TOOL_COMPLETION_TOKENS,
      "selection_token_count_calls":calls,
      "observed_input_tokens":out.get("input_tokens"),
      "effective_timeout_s":out.get("effective_timeout_s"),
      "planner_duration_s":out.get("duration_s"),
      "planner_model":out.get("model"),
      "planner_transport":out.get("transport"),
      "proposal_candidate_count":len(proposal["candidates"]),
      "proposal_action_ids":sorted(r["action_id"] for r in proposal["candidates"]),
      "dependency_edge_verified":by_dep(proposal),
    }

def by_dep(proposal:dict[str,Any])->bool:
    for row in proposal["candidates"]:
        if row.get("action_id")=="PREFLIGHT_B":
            return row.get("depends_on")==["PREFLIGHT_A"]
    return False

def main()->int:
    try: r=run_preflight()
    except Exception as exc:
        r={"schema":SCHEMA,"status":"FAIL_CLOSED__CONTEXT16K_ZERO_EXPOSURE_PREFLIGHT_FAILED","pass":False,
           "benchmark_task_exposure":0,"benchmark_trials_executed":0,"acceptance_credit_delta":0,
           "terminal_credit_delta":0,"error_type":type(exc).__name__,"error":str(exc)}
    print(json.dumps(r,indent=2,sort_keys=True))
    return 0 if r.get("pass") else 1

if __name__=="__main__": raise SystemExit(main())
