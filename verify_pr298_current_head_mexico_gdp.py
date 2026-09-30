#!/usr/bin/env python3
import hashlib
import importlib.util
import json
import math
import pathlib
import sys
import urllib.request

ROOT=pathlib.Path(__file__).resolve().parent
RUNTIME=ROOT/"canonical"/"runtime"
REPORT=ROOT/"pr298-current-head-mexico-report.json"

EXPECTED_BLOBS={
  "canonical/runtime/goal_compiler.py":"4d7f94219893400344a258552e1d808b2dc963dd",
  "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json":"23f7b79fca15593eb563bdcdba17c8b972f006db",
  "canonical/runtime/bound_capabilities/numeric_expression_sympy.py":"443e3386f11156e55635556b6e8f8ad7d7733592",
  "canonical/tests/test_numeric_expression_sympy_binding.py":"82af4e1b2a68a63e415c756f121269d89689d7af",
}
BRAIN_BASE="7e4fceab972c4e2c0364ae4b7db934bc319ce2c0"
BRAIN_PR=298
BRAIN_HEAD="4e836d9838fc60eefd092e2ac7da61af3890b746"

def git_blob_sha(path):
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def write(report):
    REPORT.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2,sort_keys=True))

for rel,expected in EXPECTED_BLOBS.items():
    p=ROOT/rel
    got=git_blob_sha(p) if p.is_file() else None
    if got!=expected:
        write({
          "schema":"PROJECT_BRAIN_TYPED_SCALAR_EXPRESSION_CURRENT_HEAD_QUALIFICATION_V1",
          "status":"CANDIDATE_BLOB_MISMATCH",
          "path":rel,"expected_blob":expected,"observed_blob":got,
          "brain_pr":BRAIN_PR,"brain_head":BRAIN_HEAD,
        })
        raise SystemExit(1)

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module

compiler=load("pr298_current_goal_compiler",RUNTIME/"goal_compiler.py")
runtime=load("pr298_current_astra_runtime",RUNTIME/"astra_runtime.py")
registry=json.loads((RUNTIME/"BOUND_CAPABILITY_REGISTRY_V1.json").read_text(encoding="utf-8"))["capabilities"]
entry=registry.get("math.numeric_expression.sympy")
if not isinstance(entry,dict) or entry.get("status")!="CANDIDATE_BOUND_CAPABILITY":
    write({"schema":"PROJECT_BRAIN_TYPED_SCALAR_EXPRESSION_CURRENT_HEAD_QUALIFICATION_V1","status":"CANDIDATE_REGISTRY_STATE_INVALID"})
    raise SystemExit(2)

url_2023="https://api.worldbank.org/v2/country/MEX/indicator/NY.GDP.MKTP.CD?format=json&date=2023"
url_2020="https://api.worldbank.org/v2/country/MEX/indicator/NY.GDP.MKTP.CD?format=json&date=2020"
expression="(gdp_2023 / gdp_2020) ** (1 / 3)"
goal=(
  "Using the authoritative JSON source "+url_2023+", "
  "extract JSON path 1.0.value and save the knowledge evidence to "
  "canonical/astra_runtime/tmp/FRESH_EXPR_GDP_2023.json. "
  "Using the authoritative JSON source "+url_2020+", "
  "extract JSON path 1.0.value and save the knowledge evidence to "
  "canonical/astra_runtime/tmp/FRESH_EXPR_GDP_2020.json. "
  "Calculate the annual compound GDP factor using annual_gdp_factor = "+expression+"."
)

report={
  "schema":"PROJECT_BRAIN_TYPED_SCALAR_EXPRESSION_CURRENT_HEAD_QUALIFICATION_V1",
  "status":"STARTED",
  "brain_pr":BRAIN_PR,
  "brain_head":BRAIN_HEAD,
  "brain_base":BRAIN_BASE,
  "candidate_blobs":EXPECTED_BLOBS,
  "task_id":"FRESH-TYPED-SCALAR-EXPRESSION-WORLD-BANK-MEXICO-GDP-20260930-V1",
  "domain":"MACROECONOMICS_PUBLIC_STATISTICS",
  "source_task_replay":False,
  "prior_child_task_replay":False,
  "model_dependency_count":0,
  "incremental_spend_usd":0,
  "source_urls":[url_2023,url_2020],
  "expression":expression,
}

try:
    compiled=compiler.compile_goal(goal,registry,ROOT)
except Exception as exc:
    report.update({"status":"COMPILE_FAIL","first_causal_blocker":type(exc).__name__+":"+str(exc)})
    write(report)
    raise SystemExit(3)

expr_parts=[p for p in compiled.get("compiled_parts",[]) if p.get("mode")=="VERIFIED_BOUND_NUMERIC_EXPRESSION"]
if len(expr_parts)!=1:
    report.update({"status":"COMPILE_EVIDENCE_INVALID","expression_part_count":len(expr_parts)})
    write(report)
    raise SystemExit(4)
part=expr_parts[0]
expected_bindings={"gdp_2023":0,"gdp_2020":1}
observed_bindings={k:int(v["cycle"]) for k,v in (part.get("variable_bindings") or {}).items()}
if observed_bindings!=expected_bindings:
    report.update({"status":"PROVENANCE_BINDING_FAIL","expected_bindings":expected_bindings,"observed_bindings":observed_bindings})
    write(report)
    raise SystemExit(5)
if part.get("selected_capability")!="math.numeric_expression.sympy":
    report.update({"status":"WRONG_CAPABILITY","selected":part.get("selected_capability")})
    write(report)
    raise SystemExit(6)

mission={"mission_id":report["task_id"],"goal":goal}
step={"id":"fresh_typed_scalar_expression_mexico_gdp","controller_actions":compiled["controller_actions"],"max_controller_actions":16}
try:
    run=runtime._run_model_independent_goal(step,mission,goal)
except Exception as exc:
    report.update({"status":"EXECUTION_FAIL","first_causal_blocker":type(exc).__name__+":"+str(exc)})
    write(report)
    raise SystemExit(7)

result_path=ROOT/str(part["output_path"])
if not result_path.is_file():
    report.update({"status":"RESULT_ARTIFACT_MISSING","path":str(part["output_path"])})
    write(report)
    raise SystemExit(8)
producer=json.loads(result_path.read_text(encoding="utf-8"))

def fetch_value(url):
    req=urllib.request.Request(url,headers={"User-Agent":"ProjectBrain-IndependentOracle/1"})
    with urllib.request.urlopen(req,timeout=20) as resp:
        payload=json.loads(resp.read(1000000).decode("utf-8"))
    value=payload[1][0]["value"]
    if isinstance(value,bool) or not isinstance(value,(int,float)):
        raise RuntimeError("ORACLE_VALUE_NOT_NUMERIC")
    return value

gdp2023=fetch_value(url_2023)
gdp2020=fetch_value(url_2020)
oracle=(gdp2023/gdp2020)**(1/3)
observed=float(producer["value"])
failures=[]
if not math.isfinite(observed): failures.append("PRODUCER_NONFINITE")
if not math.isclose(observed,oracle,rel_tol=1e-12,abs_tol=1e-15): failures.append("VALUE_MISMATCH")
if int(producer.get("model_dependency_count",-1))!=0: failures.append("MODEL_DEPENDENCY_COUNT_MISMATCH")
if producer.get("expression")!=expression: failures.append("EXPRESSION_MISMATCH")

report.update({
  "status":"PASS" if not failures else "FAIL_INDEPENDENT_ORACLE",
  "compiler_clause_coverage_verified":compiled.get("clause_coverage_verified"),
  "selected_capability":part.get("selected_capability"),
  "variable_bindings":part.get("variable_bindings"),
  "controller_cycles":run.get("cycles"),
  "producer":{"value":observed,"symbolic_result":producer.get("symbolic_result"),"output_path":part.get("output_path")},
  "independent_oracle":{
    "method":"fresh direct World Bank refetch plus independent Python arithmetic",
    "producer_adapter_imported":False,
    "gdp_2023":gdp2023,
    "gdp_2020":gdp2020,
    "value":oracle,
  },
  "failures":failures,
})
write(report)
if failures:
    raise SystemExit(9)
