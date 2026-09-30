#!/usr/bin/env python3
import importlib.util, json, math, pathlib, sys, urllib.request

ROOT=pathlib.Path(__file__).resolve().parent
RUNTIME=ROOT/"canonical"/"runtime"

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module

compiler=load("pr298_goal_compiler",RUNTIME/"goal_compiler.py")
runtime=load("pr298_astra_runtime",RUNTIME/"astra_runtime.py")
registry=json.loads((RUNTIME/"BOUND_CAPABILITY_REGISTRY_V1.json").read_text(encoding="utf-8"))["capabilities"]

url_2010="https://api.worldbank.org/v2/country/NGA/indicator/SP.POP.TOTL?format=json&date=2010"
url_2010="https://api.worldbank.org/v2/country/NGA/indicator/SP.POP.TOTL?format=json&date=2020"
goal=(
    "Using the authoritative JSON source "+url_2020+", "
    "extract JSON path 1.0.value and save the knowledge evidence to "
    "canonical/astra_runtime/tmp/NIGERIA_POP_2010.json. "
    "Using the authoritative JSON source "+url_2020+", "
    "extract JSON path 1.0.value and save the knowledge evidence to "
    "canonical/astra_runtime/tmp/NIGERIA_POP_2020.json. "
    "Calculate the annualized growth factor using annual_factor = "
    "(pop_2020 / pop_2010) ** (1 / 10)."
)

compiled=compiler.compile_goal(goal,registry,ROOT)
parts=compiled.get("compiled_parts") or []
exprs=[p for p in parts if p.get("mode")=="VERIFIED_BOUND_NUMERIC_EXPRESSION"]
if len(exprs)!=1:
    raise SystemExit("EXPRESSION_PART_COUNT_INVALID:"+str(len(exprs)))
expr=exprs[0]
if expr.get("selected_capability")!="math.numeric_expression.sympy":
    raise SystemExit("WRONG_SELECTED_CAPABILITY:"+str(expr.get("selected_capability")))
if set(expr.get("variable_names") or [])!={"pop_2010","pop_2020"}:
    raise SystemExit("VARIABLE_NAMES_INVALID:"+repr(expr.get("variable_names")))
if expr.get("model_dependency_count")!=0:
    raise SystemExit("MODEL_DEPENDENCY_PRESENT")

mission={"mission_id":"FRESH-DEMOGRAPHY-TYPED-SCALAR-EXPRESSION-20260930-V2","goal":goal}
step={"id":"fresh_economic_expression","controller_actions":compiled["controller_actions"],"max_controller_actions":16}
run=runtime._run_model_independent_goal(step,mission,goal)
if run.get("returncode")!=0 or run.get("final_summary")!="COMPOUND_GOAL_COMPLETE":
    raise SystemExit("CANDIDATE_RUNTIME_DID_NOT_COMPLETE:"+json.dumps(run,sort_keys=True))

producer_path=ROOT/expr["output_path"]
producer=json.loads(producer_path.read_text(encoding="utf-8"))

def fetch_value(url):
    req=urllib.request.Request(url,headers={"User-Agent":"ProjectBrain-PR298-IndependentOracle/1"})
    with urllib.request.urlopen(req,timeout=25) as resp:
        payload=json.loads(resp.read(1000000).decode("utf-8"))
    value=payload[1][0]["value"]
    if isinstance(value,bool) or not isinstance(value,(int,float)):
        raise RuntimeError("ORACLE_VALUE_NOT_NUMERIC")
    return float(value)

v2020=fetch_value(url_2010)
v2023=fetch_value(url_2010)
expected=(v2023/v2020)**(1.0/3.0)
failures=[]
observed=float(producer["value"])
if not math.isclose(observed,expected,rel_tol=1e-12,abs_tol=1e-12):
    failures.append("ANNUAL_FACTOR_MISMATCH")
if producer.get("model_dependency_count")!=0:
    failures.append("PRODUCER_MODEL_DEPENDENCY")
if not compiled.get("clause_coverage_verified"):
    failures.append("COMPILER_CLAUSE_COVERAGE_NOT_VERIFIED")

# Adversarial adapter checks. These must fail without evaluating arbitrary code.
adapter=load("pr298_numeric_expression_adapter",RUNTIME/"bound_capabilities"/"numeric_expression_sympy.py")
negative={}
for name,expression,variables in [
    ("call","__import__('os').system('id')",{}),
    ("attribute","x.real",{"x":2}),
    ("exponent_limit","x ** 100",{"x":2}),
    ("unbound","x + y",{"x":2}),
]:
    try:
        adapter.run({"expression":expression,"variables":variables,"output_path":"canonical/astra_runtime/tmp/NEGATIVE_"+name+".json"},ROOT)
        negative[name]="UNEXPECTED_PASS"
        failures.append("NEGATIVE_"+name+"_UNEXPECTED_PASS")
    except Exception as exc:
        negative[name]=type(exc).__name__+":"+str(exc)

report={
  "schema":"PROJECT_BRAIN_PR298_TYPED_SCALAR_SYMPY_FRESH_VERIFICATION_V2",
  "status":"PASS" if not failures else "FAIL",
  "task_id":"FRESH-DEMOGRAPHY-TYPED-SCALAR-EXPRESSION-20260930-V2",
  "domain":"ECONOMICS_PUBLIC_STATISTICS",
  "source_task_replay":False,
  "selected_capability":"math.numeric_expression.sympy",
  "expression":"(pop_2020 / pop_2010) ** (1 / 10)",
  "source_urls":[url_2010,url_2010],
  "producer":producer,
  "compiler_expression_part":expr,
  "independent_oracle":{
    "pop_2010":v2020,
    "pop_2020":v2023,
    "annual_factor":expected,
    "method":"fresh distinct World Bank demography refetch plus independent Python arithmetic",
    "producer_adapter_imported_for_oracle":False
  },
  "negative_unsafe_expression_checks":negative,
  "model_dependency_count":0,
  "incremental_spend_usd":0,
  "compiler_clause_coverage_verified":compiled.get("clause_coverage_verified"),
  "controller_cycles":run.get("cycles"),
  "failures":failures
}
path=ROOT/"pr298-typed-scalar-sympy-fresh-report.json"
path.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(report,indent=2,sort_keys=True))
if failures:
    raise SystemExit(1)
