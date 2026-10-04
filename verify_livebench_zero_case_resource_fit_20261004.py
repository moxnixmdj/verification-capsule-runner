from __future__ import annotations
import hashlib, importlib, importlib.metadata, importlib.util, json, sys, types
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SUB=ROOT/"subject"/"livebench_zero_case_resource_fit_20261004"

EXPECTED={
 "astra":("astra_runtime.py","7f5d16b1db69cb620954bc778e0ba6e15e687b75"),
 "inference":("root2_livebench_if_astra_inference_adapter_v1.py","7e3885fa7a6e56df656c066e0a8f17cfa21424e7"),
 "response":("livebench_if_response_adapter.py","eb497ae5585f4f22b06b8088609b6d17714ebc53"),
 "eval":("livebench/if_runner/ifbench/evaluation_lib.py","2c7bd1290031dbe4ae0f016c53255f4af0ec645b"),
 "instructions":("livebench/if_runner/ifbench/instructions.py","02b2dfeb50f036b89bec3df34522c73f756d8f44"),
 "registry":("livebench/if_runner/ifbench/instructions_registry.py","adfed4832877566e62970257b50c6fa32c302fb2"),
 "util":("livebench/if_runner/ifbench/instructions_util.py","21b13c7fcfc2c2de01e80c9e7dd222b9bca81342"),
}

def blob(path: Path) -> str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

for name,(rel,expected) in EXPECTED.items():
    got=blob(SUB/rel)
    assert got==expected,(name,got,expected)

for pkg,version in {
  "nltk":"3.10.3",
  "emoji":"2.16.0",
  "syllapy":"0.7.2",
  "setuptools":"80.9.0",
}.items():
    got=importlib.metadata.version(pkg)
    assert got==version,(pkg,got,version)

canonical=types.ModuleType("canonical")
runtime=types.ModuleType("canonical.runtime")
canonical.runtime=runtime
sys.modules["canonical"]=canonical
sys.modules["canonical.runtime"]=runtime

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    assert spec and spec.loader
    mod=importlib.util.module_from_spec(spec)
    sys.modules[name]=mod
    spec.loader.exec_module(mod)
    return mod

astra=load("canonical.runtime.astra_runtime",SUB/"astra_runtime.py")
runtime.astra_runtime=astra
inference=load("canonical.runtime.root2_livebench_if_astra_inference_adapter_v1",SUB/"root2_livebench_if_astra_inference_adapter_v1.py")
response=load("canonical.runtime.livebench_if_response_adapter",SUB/"livebench_if_response_adapter.py")

# Exercise the real frozen model-independent controller and its checkpoint path.
step={
  "goal_ref":"goal",
  "allow_optional_model_planner":False,
  "max_controller_actions":2,
  "max_cycles":1,
  "controller_actions":[
    {"type":"finish","args":{"summary":"SYNTHETIC_ZERO_CASE_OK"}}
  ],
}
mission={
  "mission_id":"LIVEBENCH-ZERO-CASE-RESOURCE-FIT-SYNTHETIC",
  "goal":"synthetic zero-case resource-fit smoke",
}
result=astra.run_goal(step,mission)
assert result["controller_mode"]=="MODEL_INDEPENDENT_ACTION_PLAN",result
assert result["cognition_dependency_class"]=="MODEL_INDEPENDENT",result
assert result["model_dependency_count"]==0,result
assert result["stdout"]=="SYNTHETIC_ZERO_CASE_OK",result

# Exercise the response ABI without any benchmark prompt content.
adapted=response.adapt_responses(
  [{"question_id":"synthetic-zero-case","response":"SYNTHETIC_ZERO_CASE_OK"}],
  model_id="brain",
)
check=response.validate_against_questions(
  adapted,
  [{"question_id":"synthetic-zero-case"}],
  model_id="brain",
)
assert check=={"status":"PASS","count":1,"content_inspected":False},check

# Import the exact pinned IF scorer module. This intentionally uses the frozen
# environment only; missing undeclared dependencies must fail closed.
sys.path.insert(0,str(SUB))
evaluation_lib=importlib.import_module("livebench.if_runner.ifbench.evaluation_lib")
assert evaluation_lib is not None

print(json.dumps({
  "status":"PASS",
  "exact_blob_count":len(EXPECTED),
  "frozen_declared_package_count":4,
  "astra_model_independent_smoke":True,
  "response_adapter_smoke":True,
  "scorer_import_pass":True,
  "terminal_case_content_read":False,
  "terminal_cases_consumed":0,
  "paid_external_model_or_api_used":False,
},sort_keys=True))
