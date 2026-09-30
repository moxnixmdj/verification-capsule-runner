#!/usr/bin/env python3
import importlib.util
import json
import math
import pathlib
import subprocess
import sys
import urllib.request

ROOT=pathlib.Path(__file__).resolve().parent
RUNTIME=ROOT/"canonical"/"runtime"/"astra_runtime.py"

def load_runtime():
    spec=importlib.util.spec_from_file_location("project_brain_pr296_runtime",RUNTIME)
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module

def world_bank_population():
    url="https://api.worldbank.org/v2/country/FRA/indicator/SP.POP.TOTL?format=json&date=2023"
    req=urllib.request.Request(url,headers={"User-Agent":"ProjectBrain-PR296-Verifier/1"})
    with urllib.request.urlopen(req,timeout=30) as resp:
        raw=resp.read(2_000_000)
    payload=json.loads(raw.decode("utf-8"))
    value=payload[1][0]["value"]
    if not isinstance(value,(int,float)) or isinstance(value,bool):
        raise RuntimeError("WORLD_BANK_VALUE_NOT_NUMERIC")
    return url,value

def main():
    test=subprocess.run(
      [sys.executable,"canonical/tests/test_numeric_expression_sympy_binding.py"],
      cwd=ROOT,text=True,capture_output=True,timeout=120
    )
    if test.returncode!=0:
        raise RuntimeError("COMPILER_REGRESSION_FAILED:"+test.stdout[-1500:]+test.stderr[-1500:])
    runtime=load_runtime()
    source_url,pop=world_bank_population()
    expression="population * (1.01 ** 2)"
    producer=runtime._invoke_bound_capability({
      "capability_id":"math.numeric_expression.sympy",
      "expression":expression,
      "variables":{"population":pop},
      "output_path":"numeric-expression-fresh-output.json",
    })
    oracle=float(pop)*(1.01**2)
    observed=float(producer["value"])
    abs_error=abs(observed-oracle)
    tolerance=max(1e-8,abs(oracle)*1e-12)
    positive_pass=math.isfinite(observed) and abs_error<=tolerance and producer.get("model_dependency_count")==0

    attacks=[
      "__import__('os').system('id')",
      "x.real",
      "x[0]",
      "x ** 100",
      "(lambda: 1)()",
    ]
    rejected={}
    for expr in attacks:
        try:
            runtime._invoke_bound_capability({
              "capability_id":"math.numeric_expression.sympy",
              "expression":expr,
              "variables":{"x":4},
              "output_path":"numeric-expression-attack-output.json",
            })
            rejected[expr]=False
        except Exception:
            rejected[expr]=True

    string_case=runtime._invoke_bound_capability({
      "capability_id":"math.numeric_expression.sympy",
      "expression":"x * (2 ** 3)",
      "variables":{"x":"1.25e2"},
      "output_path":"numeric-expression-string-output.json",
    })
    string_oracle=125.0*(2**3)
    string_pass=abs(float(string_case["value"])-string_oracle)<=1e-10

    report={
      "schema":"PROJECT_BRAIN_TYPED_SCALAR_NUMERIC_EXPRESSION_QUALIFICATION_V1",
      "capability_id":"MODEL_INDEPENDENT_TYPED_SCALAR_NUMERIC_EXPRESSION_EXECUTION_V1",
      "producer_capability":"math.numeric_expression.sympy",
      "fresh_domain":"DEMOGRAPHY_PUBLIC_STATISTICS",
      "source_url":source_url,
      "source_value":pop,
      "expression":expression,
      "producer_value":observed,
      "independent_python_value":oracle,
      "absolute_error":abs_error,
      "tolerance":tolerance,
      "positive_pass":positive_pass,
      "numeric_string_pass":string_pass,
      "unsafe_cases_rejected":rejected,
      "unsafe_rejection_pass":all(rejected.values()),
      "compiler_regression_tests_pass":True,
      "producer_adapter_imported_by_oracle":False,
      "model_dependency_count":0,
      "incremental_spend_usd":0,
      "dependency":producer.get("dependency"),
    }
    report["pass"]=bool(positive_pass and string_pass and all(rejected.values()))
    pathlib.Path("typed-scalar-expression-qualification.json").write_text(
      json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8"
    )
    print(json.dumps(report,indent=2,sort_keys=True))
    if not report["pass"]:
        raise SystemExit(1)

if __name__=="__main__":
    main()
