from __future__ import annotations
import hashlib, importlib.util, json, sys, types
from pathlib import Path

ROOT=Path(__file__).resolve().parent
ASTRA=ROOT/"canonical/runtime/astra_runtime.py"
ADAPTER=ROOT/"subject/livebench_zero_case_resource_fit_20261004/root2_livebench_if_astra_inference_adapter_v1.py"

def blob(p:Path)->str:
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

assert blob(ASTRA)=="7f5d16b1db69cb620954bc778e0ba6e15e687b75"
assert blob(ADAPTER)=="7e3885fa7a6e56df656c066e0a8f17cfa21424e7"
for p,sha in [
 (ROOT/"canonical/runtime/goal_compiler.py","4b61fe911471854ec15c7900816f61e9e55f602e"),
 (ROOT/"canonical/runtime/capability_proposal_generators.py","71f2bbfda66a65d8d75e035b9ae073671ebd56e2"),
 (ROOT/"canonical/runtime/capability_planner.py","64ff65cb184f50d3336326f33cccfcc0a53301a8"),
 (ROOT/"canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json","7badee4878700f2cd4176beb8319d2a6a0bdf782"),
 (ROOT/"canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py","da42f0615380027f963044f80e55ddfa1d73ced1"),
]:
    assert blob(p)==sha,(p,blob(p),sha)

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

astra=load("canonical.runtime.astra_runtime",ASTRA)
runtime.astra_runtime=astra
adapter=load("canonical.runtime.root2_livebench_if_astra_inference_adapter_v1",ADAPTER)

request={
  "benchmark_id":"LIVEBENCH_IF_2026_06_25",
  "task_id":"SYNTHETIC_ZERO_CASE_INFERENCE_CANONICAL_LAYOUT_V2",
  "allowed_tools":[],
  "task_payload":{"instruction":"Reply with exactly SYNTHETIC_OK."},
}

try:
    out=adapter.infer(request)
except Exception as exc:
    result={
      "schema":"PROJECT_BRAIN_LIVEBENCH_PUBLIC_INFERENCE_CANONICAL_LAYOUT_V2",
      "status":"BLOCKED",
      "error_type":type(exc).__name__,
      "error":str(exc),
      "terminal_case_content_read":False,
      "terminal_cases_consumed":0,
      "paid_external_model_or_api_used":False,
      "frozen_candidate_mutated":False,
    }
    print(json.dumps(result,sort_keys=True))
    raise SystemExit(1)

answer=str(out.get("answer") or "").strip()
result={
  "schema":"PROJECT_BRAIN_LIVEBENCH_PUBLIC_INFERENCE_CANONICAL_LAYOUT_V2",
  "status":"PASS",
  "adapter_status":out.get("status"),
  "answer":answer,
  "answer_exact_synthetic_ok":answer=="SYNTHETIC_OK",
  "cognition_dependency_class":out.get("cognition_dependency_class"),
  "model_dependency_count":out.get("model_dependency_count"),
  "terminal_case_content_read":False,
  "terminal_cases_consumed":0,
  "paid_external_model_or_api_used":False,
  "frozen_candidate_mutated":False,
  "astra_git_blob_sha":blob(ASTRA),
  "adapter_git_blob_sha":blob(ADAPTER),
}
print(json.dumps(result,sort_keys=True))
assert out.get("status")=="PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE",result
assert out.get("cognition_dependency_class")=="MODEL_INDEPENDENT",result
assert int(out.get("model_dependency_count") or 0)==0,result
assert answer=="SYNTHETIC_OK",result
