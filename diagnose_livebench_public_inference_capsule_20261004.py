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

EXPECTED_BOUND_CAPABILITIES={
  "broad_objective_decompose.py":"3ded762075ed222228a14877af631f1e2e6d9e4c",
  "plain_goal_bound_grounding.py":"46e8e7466479ea298c34e5fa682d49c374510ce9",
}
observed_bound_capabilities={
  name:git_blob_sha(SUB/"bound_capabilities"/name)
  for name in EXPECTED_BOUND_CAPABILITIES
}
assert observed_bound_capabilities==EXPECTED_BOUND_CAPABILITIES,(observed_bound_capabilities,EXPECTED_BOUND_CAPABILITIES)

EXPECTED_ACQUISITION_CLOSURE={
  "auto_capability_acquisition.py":"fc80ede8225cc51dac77be6d41aa2a1c757c6ee8",
  "auto_apt_cli_acquisition.py":"0b7c67a2680a3aaa1aa5cf1a8bc8d41d69eee271",
  "auto_pypi_library_acquisition.py":"6387bd7b8f1dba8bb9f66240e3ebb2627085dd2f",
  "auto_npm_library_acquisition.py":"b74cdf34a96fc2d591b902e1d582e0381a8a8d08",
  "auto_python_source_codec_acquisition.py":"65453b2eed5e678def3f0ab1c4d44182fb0b9a78",
  "apt_cli_probe.py":"3f3a8f6a0154e1ed3f87fc97b99840598297b119",
  "capability_discovery.py":"b9e7423ab24bf2da98869b02d782e791a779892a",
  "cli_contract_inference.py":"009c3c45040178844d84eaa15b0d47ca2e1f259f",
  "npm_package_utils.py":"05fd0591083034df48c3ee426d6b3e11e0183555",
  "semantic_authorities.py":"1d74b9c2cdc0e387ab1d64f04c8f38f414f2d80e",
}
observed_acquisition_closure={
  name:git_blob_sha(SUB/name) for name in EXPECTED_ACQUISITION_CLOSURE
}
assert observed_acquisition_closure==EXPECTED_ACQUISITION_CLOSURE,(observed_acquisition_closure,EXPECTED_ACQUISITION_CLOSURE)

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
  "task_id":"SYNTHETIC_ZERO_CASE_OWNED_CAPABILITY_V2",
  "allowed_tools":[],
  "task_payload":{"instruction":"Calculate the numeric scalar expression 2 + 2."},
}

try:
    out=adapter.infer(request)
except Exception as exc:
    result={
      "schema":"PROJECT_BRAIN_LIVEBENCH_PUBLIC_INFERENCE_CAPSULE_DIAGNOSTIC_V1",
      "synthetic_probe_semantics":"VERIFIED_ALREADY_OWNED_ZERO_COST_CAPABILITY__NOT_ACQUISITION",
      "status":"BLOCKED",
      "error_type":type(exc).__name__,
      "error":str(exc),
      "terminal_case_content_read":False,
      "terminal_cases_consumed":0,
      "paid_external_model_or_api_used":False,
      "runtime_closure_git_blob_shas":observed_runtime_closure,
      "bound_capabilities_git_blob_shas":observed_bound_capabilities,
      "acquisition_closure_git_blob_shas":observed_acquisition_closure,
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
