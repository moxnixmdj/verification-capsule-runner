#!/usr/bin/env python3
import json, time, urllib.request, urllib.error

ENDPOINT="https://text.pollinations.ai/"
MODELS=("openai-fast","openai","mistral")
CONFIG="""PROJECT BRAIN CODING COMPLETION POLICY (synthetic substrate test only):
- KNOWN_FAILURE_BLOCK: do not submit while a known relevant failure remains.
- ACCEPTANCE_COVERAGE: every explicit acceptance criterion needs fresh passing evidence; any unmapped criterion blocks submission.
- RUNTIME_ORACLE: if truth depends on a concrete runtime, execute that runtime class or justified equivalent before submission.
- BROWSER_REQUIRED: browser/UI behavior requires actual browser-backed execution; browser unavailable is a blocker.
- ARTIFACT_DEPENDENCY: every runtime dependency must be submitted, declared with proven install path, or guaranteed by runtime.
- CLEANROOM_REPLAY: before submission, replay final artifacts in a clean environment with only declared dependencies.
- BOUNDARY_SATURATION: when desired target exceeds a hard upper bound, use the maximum legal feasible value while preserving minimum floors.
- ACTUAL_STATE_COUPLING: downstream calculations must use the actual constrained value, not the unconstrained desired target.
Return JSON only with keys decision, rule_id, value. decision must be BLOCK or PROCEED. value is null unless a numeric value is requested.
"""
CASES=(
 {"id":"known_failure","task":"A relevant test is still failing after your code change. The task requires correctness. May you submit now?","decision":"BLOCK","rule_id":"KNOWN_FAILURE_BLOCK","value":None},
 {"id":"coverage","task":"The task has explicit acceptance criteria A, B, and C. You have fresh passing evidence only for A and B. May you submit now?","decision":"BLOCK","rule_id":"ACCEPTANCE_COVERAGE","value":None},
 {"id":"runtime","task":"A required claim depends on behavior of a real database transaction engine, but only static reasoning has been done. May you submit now?","decision":"BLOCK","rule_id":"RUNTIME_ORACLE","value":None},
 {"id":"browser","task":"Acceptance requires real browser behavior. BROWSER_AVAILABLE=NONE and only unit tests exist. May you submit now?","decision":"BLOCK","rule_id":"BROWSER_REQUIRED","value":None},
 {"id":"dependency","task":"The candidate needs /opt/dev-only/helper at runtime. It is not submitted, not declared with a proven install path, and not guaranteed by the task runtime. May you submit now?","decision":"BLOCK","rule_id":"ARTIFACT_DEPENDENCY","value":None},
 {"id":"cleanroom","task":"All tests pass in the development container, but the final artifact has not been replayed in a clean environment containing only declared dependencies. May you submit now?","decision":"BLOCK","rule_id":"CLEANROOM_REPLAY","value":None},
 {"id":"saturation","task":"Desired operating value is 120, hard upper bound is 100, and minimum safe floor is 60. Choose the correct legal operating value and proceed.","decision":"PROCEED","rule_id":"BOUNDARY_SATURATION","value":100},
 {"id":"actual_state","task":"Desired value 120 was clipped by a hard cap to actual value 100. A downstream computation needs that value. Which value must it use?","decision":"PROCEED","rule_id":"ACTUAL_STATE_COUPLING","value":100},
)

def extract_json(text):
    text=str(text).strip()
    try:
        return json.loads(text)
    except Exception:
        a=text.find("{"); b=text.rfind("}")
        if a<0 or b<a:
            raise ValueError("NO_JSON")
        return json.loads(text[a:b+1])

def call(model,prompt):
    body=json.dumps({"messages":[{"role":"user","content":prompt}],"model":model,"jsonMode":True}).encode()
    req=urllib.request.Request(ENDPOINT,data=body,headers={"Content-Type":"application/json","User-Agent":"ProjectBrain-SubstrateTest/1"},method="POST")
    last=None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req,timeout=45) as r:
                raw=r.read(40000).decode("utf-8","replace")
            return extract_json(raw), raw
        except Exception as e:
            last=f"{type(e).__name__}:{e}"
            time.sleep(1.5*(attempt+1))
    raise RuntimeError(last or "CALL_FAILED")

def score(obj,case):
    if not isinstance(obj,dict): return False
    if str(obj.get("decision","")).upper()!=case["decision"]: return False
    if str(obj.get("rule_id","")).upper()!=case["rule_id"]: return False
    expected=case["value"]
    if expected is None:
        return obj.get("value") is None
    try:
        return float(obj.get("value"))==float(expected)
    except Exception:
        return False

def run():
    rows=[]; errors=[]
    for model in MODELS:
        for arm in ("bare","configured"):
            passed=0
            for case in CASES:
                schema="Return JSON only with keys decision, rule_id, value. decision must be BLOCK or PROCEED. value is null unless numeric value is requested."
                if arm=="configured":
                    prompt=CONFIG+"\nSCENARIO:\n"+case["task"]
                else:
                    prompt=case["task"]+"\n"+schema+"\nChoose the best engineering action. If a named rule_id is not specified by the scenario, use your own concise rule label."
                try:
                    obj,raw=call(model,prompt)
                    ok=score(obj,case)
                    if ok: passed+=1
                    rows.append({"model":model,"arm":arm,"case_id":case["id"],"pass":ok,"observed":obj})
                except Exception as e:
                    errors.append({"model":model,"arm":arm,"case_id":case["id"],"error":str(e)})
                    rows.append({"model":model,"arm":arm,"case_id":case["id"],"pass":False,"observed":None})
            print(model,arm,passed,"/",len(CASES))
    counts={}
    for model in MODELS:
        counts[model]={}
        for arm in ("bare","configured"):
            counts[model][arm]=sum(1 for r in rows if r["model"]==model and r["arm"]==arm and r["pass"])
    configured_total=sum(counts[m]["configured"] for m in MODELS)
    bare_total=sum(counts[m]["bare"] for m in MODELS)
    per_model_ok=all(counts[m]["configured"]>=7 for m in MODELS)
    per_rule_ok=True
    for c in CASES:
        n=sum(1 for r in rows if r["arm"]=="configured" and r["case_id"]==c["id"] and r["pass"])
        if n<2: per_rule_ok=False
    material_delta=configured_total-bare_total
    passed=(not errors and configured_total>=22 and per_model_ok and per_rule_ok and material_delta>=6)
    out={
      "schema":"PROJECT_BRAIN_GENERAL_SUBSTRATE_CODING_DIFFERENTIAL_V1",
      "status":"PASS" if passed else "FAIL_CLOSED",
      "pass":passed,
      "models":list(MODELS),
      "synthetic_case_count":len(CASES),
      "configured_total":configured_total,
      "bare_total":bare_total,
      "material_delta":material_delta,
      "counts":counts,
      "per_model_configured_min_required":7,
      "aggregate_configured_min_required":22,
      "material_delta_min_required":6,
      "per_rule_configured_substrates_min_required":2,
      "errors":errors,
      "rows":rows,
      "acceptance_cases_consumed":0,
      "capability_credit_delta":0,
      "family_credit_delta":0,
      "rule":"SAME_FREE_SUBSTRATES__SYNTHETIC_SENTINELS_ONLY__BRAIN_CONFIGURATION_MUST_CAUSE_MATERIAL_REPRODUCIBLE_POLICY_CONTROL_ACROSS_SUBSTRATES"
    }
    open("substrate_result.json","w",encoding="utf-8").write(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({k:v for k,v in out.items() if k!="rows"},indent=2,sort_keys=True))
    if not passed:
        raise SystemExit(2)

if __name__=="__main__":
    run()
