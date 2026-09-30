#!/usr/bin/env python3
import importlib.util
import json
import math
import pathlib
import sys
import urllib.request

ROOT=pathlib.Path(__file__).resolve().parent
RUNTIME=ROOT/"canonical"/"runtime"

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module

compiler=load("numeric_relation_candidate_goal_compiler",RUNTIME/"goal_compiler.py")
runtime=load("numeric_relation_candidate_astra_runtime",RUNTIME/"astra_runtime.py")
registry=json.loads((RUNTIME/"BOUND_CAPABILITY_REGISTRY_V1.json").read_text(encoding="utf-8"))["capabilities"]

url_a="https://api.worldbank.org/v2/country/FRA/indicator/SP.POP.TOTL?format=json&date=2023"
url_b="https://api.worldbank.org/v2/country/DEU/indicator/SP.POP.TOTL?format=json&date=2023"
threshold=20000000

goal=(
    "Using the authoritative JSON source "+url_a+", "
    "extract JSON path 1.0.value and save the knowledge evidence to "
    "canonical/astra_runtime/tmp/FRESH_NUMREL_FRANCE.json. "
    "Using the authoritative JSON source "+url_b+", "
    "extract JSON path 1.0.value and save the knowledge evidence to "
    "canonical/astra_runtime/tmp/FRESH_NUMREL_GERMANY.json. "
    "Determine whether the two population readings differ by at most 20000000."
)

compiled=compiler.compile_goal(goal,registry,ROOT)
parts=compiled.get("compiled_parts") or []
relation_parts=[p for p in parts if p.get("mode")=="VERIFIED_BOUND_NUMERIC_RELATION"]
if len(relation_parts)!=1:
    raise SystemExit("RELATION_PART_COUNT_INVALID:"+str(len(relation_parts)))
relation=relation_parts[0]
if relation.get("selected_capability")!="json.query.jq":
    raise SystemExit("WRONG_SELECTED_CAPABILITY")
if relation.get("producer_result_cycles")!=[0,1]:
    raise SystemExit("CAUSAL_RESULT_CYCLES_INVALID")
if relation.get("model_dependency_count")!=0:
    raise SystemExit("MODEL_DEPENDENCY_PRESENT")

mission={"mission_id":"FRESH-NUMERIC-RELATION-WORLD-BANK-20260930-V1","goal":goal}
step={
    "id":"fresh_numeric_relation",
    "controller_actions":compiled["controller_actions"],
    "max_controller_actions":16,
}
run=runtime._run_model_independent_goal(step,mission,goal)
if run.get("returncode")!=0 or run.get("final_summary")!="COMPOUND_GOAL_COMPLETE":
    raise SystemExit("CANDIDATE_RUNTIME_DID_NOT_COMPLETE")

producer_path=ROOT/relation["output_path"]
producer=json.loads(producer_path.read_text(encoding="utf-8"))

def fetch_world_bank_value(url):
    req=urllib.request.Request(url,headers={"User-Agent":"ProjectBrain-IndependentOracle/1"})
    with urllib.request.urlopen(req,timeout=20) as resp:
        raw=resp.read(1000000)
    payload=json.loads(raw.decode("utf-8"))
    value=payload[1][0]["value"]
    if isinstance(value,bool) or not isinstance(value,(int,float)):
        raise RuntimeError("ORACLE_VALUE_NOT_NUMERIC")
    return value

a=fetch_world_bank_value(url_a)
b=fetch_world_bank_value(url_b)
delta=abs(a-b)
predicate=delta<=threshold

failures=[]
if producer.get("left")!=a: failures.append("LEFT_MISMATCH")
if producer.get("right")!=b: failures.append("RIGHT_MISMATCH")
if producer.get("threshold")!=threshold: failures.append("THRESHOLD_MISMATCH")
if not math.isclose(float(producer.get("absolute_difference")),float(delta),rel_tol=0,abs_tol=0):
    failures.append("DELTA_MISMATCH")
if producer.get("predicate") is not predicate: failures.append("PREDICATE_MISMATCH")
if producer.get("relation")!="ABS_DIFF_LTE": failures.append("RELATION_MISMATCH")

report={
    "schema":"PROJECT_BRAIN_FRESH_NUMERIC_RELATION_JQ_REUSE_VERIFICATION_V1",
    "status":"PASS" if not failures else "FAIL",
    "task_id":"FRESH-NUMERIC-RELATION-WORLD-BANK-20260930-V1",
    "domain":"DEMOGRAPHY_PUBLIC_STATISTICS",
    "source_task_replay":False,
    "producer_route":"EXACT_PR293_GOAL_COMPILER__NATIVE_RESULT_REFS__WRITE_JSON_RECORDS__BOUND_JSON_QUERY_JQ",
    "selected_capability":"json.query.jq",
    "source_urls":[url_a,url_b],
    "threshold":threshold,
    "producer":producer,
    "independent_oracle":{
        "left":a,
        "right":b,
        "absolute_difference":delta,
        "predicate":predicate,
        "method":"fresh direct World Bank refetch plus independent Python arithmetic",
        "producer_adapter_imported":False,
    },
    "model_dependency_count":0,
    "failures":failures,
    "controller_cycles":run.get("cycles"),
    "compiler_clause_coverage_verified":compiled.get("clause_coverage_verified"),
}
path=ROOT/"numeric-relation-fresh-report.json"
path.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(report,indent=2,sort_keys=True))
if failures:
    raise SystemExit(1)
