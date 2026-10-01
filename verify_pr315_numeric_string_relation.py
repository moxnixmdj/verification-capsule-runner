#!/usr/bin/env python3
import importlib.util
import json
import math
import pathlib
import subprocess
import sys
import tempfile

ROOT=pathlib.Path(__file__).resolve().parent
TARGET=ROOT/"canonical/runtime/goal_compiler.py"
REPORT=ROOT/"pr315-numeric-string-relation-qualification.json"

def load_compiler():
    spec=importlib.util.spec_from_file_location("pr315_candidate_goal_compiler",TARGET)
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module

def registry():
    return {
      "json.query.jq":{
        "status":"VERIFIED_BOUND_CAPABILITY",
        "incremental_spend_usd":0,
        "provides":["json.query.transform"],
        "requires":["json.file.available"],
        "keywords":["json","query","transform","table","structured"],
        "action_template":{
          "type":"invoke_capability",
          "args":{
            "capability_id":"json.query.jq",
            "input_path":"${input.json_path}",
            "filter":"${input.jq_filter}",
            "output_path":"${input.output_path}",
            "raw_output":True,
            "require_nonempty":True,
            "timeout_s":60
          },
          "expect":{"type":"field_equals","field":"output_verified","value":True}
        }
      }
    }

compiler=load_compiler()
goal=(
  "Using the authoritative JSON source https://fresh.example/a, extract JSON path value "
  "and save the knowledge evidence to canonical/astra_runtime/tmp/PR315_A.json. "
  "Using the authoritative JSON source https://fresh.example/b, extract JSON path value "
  "and save the knowledge evidence to canonical/astra_runtime/tmp/PR315_B.json. "
  "Determine whether the two readings differ by at most 0.1."
)
compiled=compiler.compile_goal(goal,registry(),ROOT)
compute=[a for a in compiled["controller_actions"] if a.get("type")=="invoke_capability"][0]
filt=compute["args"]["filter"]

def run_case(name,payload,expect_success,expected=None):
    raw=json.dumps([payload],separators=(",",":"))
    proc=subprocess.run(["jq","-c",filt],input=raw,text=True,capture_output=True)
    record={"name":name,"returncode":proc.returncode}
    if expect_success:
        if proc.returncode!=0:
            raise RuntimeError(name+": unexpected jq failure: "+proc.stderr[-1000:])
        out=json.loads(proc.stdout)
        record["output"]=out
        if expected is not None:
            for key,value in expected.items():
                if isinstance(value,float):
                    if not math.isclose(float(out[key]),value,rel_tol=1e-12,abs_tol=1e-12):
                        raise RuntimeError(name+": mismatch "+key)
                elif out[key] != value:
                    raise RuntimeError(name+": mismatch "+key)
        for key in ("left","right","threshold","absolute_difference"):
            if isinstance(out[key],bool) or not isinstance(out[key],(int,float)):
                raise RuntimeError(name+": output not numeric: "+key)
    else:
        if proc.returncode==0:
            raise RuntimeError(name+": expected fail-closed rejection")
        if "NUMERIC_RELATION_INPUT_NOT_NUMBER" not in proc.stderr:
            raise RuntimeError(name+": wrong rejection: "+proc.stderr[-1000:])
        record["rejected"]=True
    return record

cases=[]
cases.append(run_case("bounded_decimal_strings",
  {"left":"1.25","right":"1.20","threshold":"0.1"},True,
  {"left":1.25,"right":1.2,"threshold":0.1,"absolute_difference":0.05,"relation":"ABS_DIFF_LTE","predicate":True}))
cases.append(run_case("scientific_numeric_strings",
  {"left":"1e2","right":"9.9e1","threshold":"2"},True,
  {"left":100.0,"right":99.0,"threshold":2.0,"absolute_difference":1.0,"relation":"ABS_DIFF_LTE","predicate":True}))
cases.append(run_case("native_numbers",
  {"left":4.0,"right":5.0,"threshold":0.5},True,
  {"left":4.0,"right":5.0,"threshold":0.5,"absolute_difference":1.0,"relation":"ABS_DIFF_LTE","predicate":False}))
for name,value in [
  ("whitespace_string"," 1.25 "),
  ("nonnumeric_string","molecule"),
  ("nan_string","NaN"),
  ("underscore_string","1_000"),
  ("too_long_numeric_string","1"*97),
  ("boolean",True),
  ("null",None),
  ("object",{"x":1}),
  ("array",[1])
]:
    cases.append(run_case(name,{"left":value,"right":1,"threshold":1},False))

report={
  "schema":"PROJECT_BRAIN_PR315_NUMERIC_STRING_RELATION_QUALIFICATION_V1",
  "status":"PASS",
  "brain_pr":315,
  "brain_head":"6248cf494e275fcfeb3c77d90a4b6061d098d5b0",
  "candidate_compiler_blob":"e0949611f35b8c8f6fe6b4933d21bc9c5bdfb874",
  "candidate_test_blob":"2f19c6ec003d2fca54eca17804e50bcaef56b713",
  "fresh_parent_task_consumed":False,
  "model_dependency_count":0,
  "incremental_spend_usd":0,
  "compiled_clause_coverage_verified":compiled.get("clause_coverage_verified"),
  "cases":cases
}
REPORT.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(report,indent=2,sort_keys=True))
