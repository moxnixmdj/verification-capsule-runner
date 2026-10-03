from __future__ import annotations
import json, time, urllib.request
from pathlib import Path

ENDPOINT="https://text.pollinations.ai/"
MODELS=("openai-fast","openai","mistral")
PROMPT='''Return JSON only. You are a general cognition substrate proposing actions to a Brain-owned science controller. Synthetic task only; no benchmark content exists. Output exactly an object with material_requirements, candidates, finish_summary. material_requirements must contain one item {"id":"R1","description":"write synthetic marker"}. candidates must contain one item with action_id "A1", covers ["R1"], command "printf synthetic > /tmp/brain_science_synthetic", verify_command "test -s /tmp/brain_science_synthetic". finish_summary must be "synthetic preflight".'''
errors=[]
for model in MODELS:
    body=json.dumps({"messages":[{"role":"user","content":PROMPT}],"model":model,"jsonMode":True}).encode()
    req=urllib.request.Request(ENDPOINT,data=body,headers={"Content-Type":"application/json","User-Agent":"ProjectBrain/1.0"},method="POST")
    t=time.monotonic()
    try:
        with urllib.request.urlopen(req,timeout=30) as r:
            raw=r.read(30000).decode("utf-8","replace")
            status=r.status
        txt=raw.strip()
        try: obj=json.loads(txt)
        except Exception:
            a=txt.find("{"); b=txt.rfind("}")
            if a<0 or b<a: raise
            obj=json.loads(txt[a:b+1])
        assert isinstance(obj,dict)
        reqs=obj.get("material_requirements")
        cands=obj.get("candidates")
        assert isinstance(reqs,list) and reqs
        assert isinstance(cands,list) and cands
        assert all(isinstance(x,dict) for x in cands)
        assert any(x.get("command") and x.get("verify_command") for x in cands)
        out={
          "schema":"PROJECT_BRAIN_TB_SCIENCE_PRODUCTION_PLANNER_PREFLIGHT_V1",
          "status":"PASS",
          "endpoint":ENDPOINT,
          "selected_model_alias":model,
          "http_status":status,
          "response_json_object":True,
          "required_controller_proposal_shape_present":True,
          "duration_s":round(time.monotonic()-t,3),
          "synthetic_prompt_only":True,
          "terminal_task_content_read":0,
          "terminal_trials_executed":0,
          "terminal_results_observed":0,
          "incremental_spend_usd":0,
          "capability_credit_delta":0,
          "family_credit_delta":0,
          "errors_before_success":errors,
        }
        Path("TB_SCIENCE_PRODUCTION_PLANNER_PREFLIGHT_V1.json").write_text(json.dumps(out,indent=2,sort_keys=True)+"\\n")
        print(json.dumps(out,sort_keys=True))
        raise SystemExit(0)
    except SystemExit:
        raise
    except Exception as e:
        errors.append({"model":model,"error":type(e).__name__+":"+str(e),"duration_s":round(time.monotonic()-t,3)})
out={
 "schema":"PROJECT_BRAIN_TB_SCIENCE_PRODUCTION_PLANNER_PREFLIGHT_V1",
 "status":"FAIL",
 "endpoint":ENDPOINT,
 "synthetic_prompt_only":True,
 "terminal_task_content_read":0,
 "terminal_trials_executed":0,
 "terminal_results_observed":0,
 "incremental_spend_usd":0,
 "errors":errors,
}
Path("TB_SCIENCE_PRODUCTION_PLANNER_PREFLIGHT_V1.json").write_text(json.dumps(out,indent=2,sort_keys=True)+"\\n")
print(json.dumps(out,sort_keys=True))
raise SystemExit(1)
