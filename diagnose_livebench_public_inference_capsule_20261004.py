from __future__ import annotations
import hashlib, importlib.util, json, sys, types
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SUB=ROOT/"subject"/"livebench_zero_case_resource_fit_20261004"

EXPECTED_RUNTIME_CLOSURE={
  "goal_compiler.py":"4b61fe911471854ec15c7900816f61e9e55f602e",
  "capability_proposal_generators.py":"71f2bbfda66a65d8d75e035b9ae073671ebd56e2",
  "capability_planner.py":"64ff65cb184f50d3336326f33cccfcc0a53301a8",
}

def git_blob_sha(path):
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\x00"+data).hexdigest()

observed_runtime_closure={name:git_blob_sha(SUB/name) for name in EXPECTED_RUNTIME_CLOSURE}
assert observed_runtime_closure==EXPECTED_RUNTIME_CLOSURE,(observed_runtime_closure,EXPECTED_RUNTIME_CLOSURE)

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
adapter=load("canonical.runtime.root2_livebench_if_astra_inference_adapter_v1",SUB/"root2_livebench_if_astra_inference_adapter_v1.py")

request={
  "benchmark_id":"LIVEBENCH_IF_2026_06_25",
  "task_id":"SYNTHETIC_ZERO_CASE_INFERENCE",
  "allowed_tools":[],
  "task_payload":{"instruction":"Reply with exactly SYNTHETIC_OK."},
}

try:
    out=adapter.infer(request)
except Exception as exc:
    result={
      "schema":"PROJECT_BRAIN_LIVEBENCH_PUBLIC_INFERENCE_CAPSULE_DIAGNOSTIC_V1",
      "status":"BLOCKED",
      "error_type":type(exc).__name__,
      "error":str(exc),
      "terminal_case_content_read":False,
      "terminal_cases_consumed":0,
      "paid_external_model_or_api_used":False,
      "runtime_closure_git_blob_shas":observed_runtime_closure,
    }
else:
    result={
      "schema":"PROJECT_BRAIN_LIVEBENCH_PUBLIC_INFERENCE_CAPSULE_DIAGNOSTIC_V1",
      "status":"PASS",
      "adapter_status":out.get("status"),
      "answer":out.get("answer"),
      "cognition_dependency_class":out.get("cognition_dependency_class"),
      "model_dependency_count":out.get("model_dependency_count"),
      "terminal_case_content_read":False,
      "terminal_cases_consumed":0,
      "paid_external_model_or_api_used":False,
      "runtime_closure_git_blob_shas":observed_runtime_closure,
    }

print(json.dumps(result,sort_keys=True))
