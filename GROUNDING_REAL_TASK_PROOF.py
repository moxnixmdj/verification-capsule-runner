#!/usr/bin/env python3
import importlib.util, json, pathlib, sys

ROOT=pathlib.Path(__file__).resolve().parent
RUNTIME=ROOT/"canonical"/"runtime"

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module

grounding=load("grounding_real_task_producer",RUNTIME/"bound_capabilities"/"plain_goal_bound_grounding.py")
verifier=load("grounding_real_task_verifier",RUNTIME/"bound_capabilities"/"plain_goal_bound_grounding_verify.py")
registry=json.loads((RUNTIME/"BOUND_CAPABILITY_REGISTRY_V1.json").read_text())["capabilities"]

tasks=[
  {
    "task_id":"GROUNDING-REAL-TASK-A-SOFTWARE-QUALITY",
    "domain":"SOFTWARE_QUALITY",
    "goal":"Audit the current Project Brain Python tests with unittest and report passed failed and skipped counts before merging capability changes.",
    "required_capability":"python.tests.audit.unittest",
  },
  {
    "task_id":"GROUNDING-REAL-TASK-B-BROWSER",
    "domain":"BROWSER_AUTOMATION",
    "goal":"Open the rendered browser page at https://example.com and capture a screenshot for independent visual verification.",
    "required_capability":"web.browser.rendered.capture.chromedriver",
  },
]
evidence=[]
for task in tasks:
    result=grounding.ground(task["goal"],registry)
    ok,reason=verifier.verify(task["goal"],result,registry)
    passed=bool(ok) and task["required_capability"] in set(result.get("candidate_capability_ids") or [])
    record={**task,"result":result,"independent_verifier":{"verified":bool(ok),"reason":reason},"task_pass":passed}
    evidence.append(record)
    print(json.dumps(record,sort_keys=True))
    if not passed:
        raise SystemExit("REAL_GROUNDING_TASK_FAILED:"+task["task_id"])
out={
  "schema":"PROJECT_BRAIN_PLAIN_GOAL_BOUND_GROUNDING_REAL_TASK_EVIDENCE_V1",
  "producer":"plain_goal_bound_grounding.py",
  "verifier":"plain_goal_bound_grounding_verify.py",
  "model_dependency_count":0,
  "incremental_spend_usd":0,
  "real_task_count":len(evidence),
  "fresh_reuse_pass":len(evidence)>=2 and len({x["domain"] for x in evidence})>=2,
  "tasks":evidence,
}
path=ROOT/"GROUNDING_REAL_TASK_EVIDENCE.json"
path.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
print(json.dumps({"status":"PASS","evidence_path":str(path.name),"fresh_reuse_pass":out["fresh_reuse_pass"]},sort_keys=True))
