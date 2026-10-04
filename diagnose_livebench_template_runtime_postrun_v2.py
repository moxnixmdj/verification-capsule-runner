#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, os, pathlib, shutil, subprocess, sys, tempfile

ROOT=pathlib.Path(__file__).resolve().parent
BENCHMARK_ID="LIVEBENCH_IF_2026_06_25"
FILES={
 "capsules/root2_livebench_astra_adapter_v1/canonical/runtime/astra_runtime.py":("canonical/runtime/astra_runtime.py","7f5d16b1db69cb620954bc778e0ba6e15e687b75"),
 "capsules/root2_livebench_astra_adapter_v1/canonical/runtime/root2_livebench_if_astra_inference_adapter_v1.py":("canonical/runtime/root2_livebench_if_astra_inference_adapter_v1.py","7e3885fa7a6e56df656c066e0a8f17cfa21424e7"),
 "capsules/root2_livebench_astra_adapter_v1/canonical/runtime/root2_external_task_entrypoint_v1.py":("canonical/runtime/root2_external_task_entrypoint_v1.py","603beefe0db24102b86b7c965e5433bd880392af"),
 "capsules/root2_livebench_astra_adapter_v1/canonical/governance/ROOT2_EXTERNAL_TASK_ADAPTER_REGISTRY_V1.json":("canonical/governance/ROOT2_EXTERNAL_TASK_ADAPTER_REGISTRY_V1.json","afa021a25d2de53e293d10ab6759e55eaabaea21"),
 "canonical/runtime/goal_compiler.py":("canonical/runtime/goal_compiler.py","4b61fe911471854ec15c7900816f61e9e55f602e"),
 "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json":("canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json","7badee4878700f2cd4176beb8319d2a6a0bdf782"),
 "canonical/runtime/capability_planner.py":("canonical/runtime/capability_planner.py","64ff65cb184f50d3336326f33cccfcc0a53301a8"),
 "canonical/runtime/capability_proposal_generators.py":("canonical/runtime/capability_proposal_generators.py","71f2bbfda66a65d8d75e035b9ae073671ebd56e2"),
 "subject/livebench_frozen_generic_closure_v1/canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py":("canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py","46e8e7466479ea298c34e5fa682d49c374510ce9"),
 "subject/livebench_frozen_generic_closure_v1/canonical/runtime/bound_capabilities/broad_objective_decompose.py":("canonical/runtime/bound_capabilities/broad_objective_decompose.py","3ded762075ed222228a14877af631f1e2e6d9e4c"),
 "subject/livebench_frozen_generic_closure_v1/canonical/runtime/bound_capabilities/grounded_executable_composition.py":("canonical/runtime/bound_capabilities/grounded_executable_composition.py","8328e12804f64cab1c0d9509966cb1d2d8fb1f82"),
 "subject/livebench_frozen_generic_closure_v1/canonical/runtime/bound_capabilities/grounded_executable_composition_verify.py":("canonical/runtime/bound_capabilities/grounded_executable_composition_verify.py","ab9f6fc19937d23edb24dc26a2affed96cea0a9a"),
 "subject/livebench_frozen_generic_closure_v1/canonical/runtime/bound_capabilities/open_research_source_frontend.py":("canonical/runtime/bound_capabilities/open_research_source_frontend.py","830fd35c816140cb6ddb2d3dac9f0886e595d993"),
 "canonical/runtime/auto_capability_acquisition.py":("canonical/runtime/auto_capability_acquisition.py","fc80ede8225cc51dac77be6d41aa2a1c757c6ee8"),
 "canonical/runtime/auto_apt_cli_acquisition.py":("canonical/runtime/auto_apt_cli_acquisition.py","0b7c67a2680a3aaa1aa5cf1a8bc8d41d69eee271"),
 "canonical/runtime/auto_pypi_library_acquisition.py":("canonical/runtime/auto_pypi_library_acquisition.py","6387bd7b8f1dba8bb9f66240e3ebb2627085dd2f"),
 "canonical/runtime/auto_npm_library_acquisition.py":("canonical/runtime/auto_npm_library_acquisition.py","b74cdf34a96fc2d591b902e1d582e0381a8a8d08"),
 "canonical/runtime/auto_python_source_codec_acquisition.py":("canonical/runtime/auto_python_source_codec_acquisition.py","65453b2eed5e678def3f0ab1c4d44182fb0b9a78"),
 "canonical/runtime/npm_package_utils.py":("canonical/runtime/npm_package_utils.py","05fd0591083034df48c3ee426d6b3e11e0183555"),
 "canonical/runtime/capability_discovery.py":("canonical/runtime/capability_discovery.py","b9e7423ab24bf2da98869b02d782e791a779892a"),
 "canonical/runtime/apt_cli_probe.py":("canonical/runtime/apt_cli_probe.py","3f3a8f6a0154e1ed3f87fc97b99840598297b119"),
 "canonical/runtime/cli_contract_inference.py":("canonical/runtime/cli_contract_inference.py","009c3c45040178844d84eaa15b0d47ca2e1f259f"),
 "subject/livebench_frozen_generic_closure_v1/canonical/runtime/semantic_authorities.py":("canonical/runtime/semantic_authorities.py","1d74b9c2cdc0e387ab1d64f04c8f38f414f2d80e"),
 "subject/livebench_frozen_generic_closure_v1/canonical/runtime/python_codec_probe.py":("canonical/runtime/python_codec_probe.py","fc8b5005a9888422e3cb61f6cf0bd147c740ec84"),
}
def git_blob_sha(path:pathlib.Path)->str:
 b=path.read_bytes()
 return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
DRIVER=r"""
import json,sys
from canonical.runtime.root2_livebench_if_astra_inference_adapter_v1 import infer
req=json.loads(sys.stdin.read())
out=infer(req)
print(json.dumps(out,sort_keys=True))
"""

def main()->int:
 assert os.environ.get("GITHUB_ACTIONS")=="true"
 assert str(os.environ.get("REPOSITORY_PRIVATE","")).lower()=="false"
 with tempfile.TemporaryDirectory(prefix="lb-template-diag-") as td:
  root=pathlib.Path(td)/"root"
  for src_rel,(dst_rel,expected_blob) in FILES.items():
   src=ROOT/src_rel
   if not src.is_file(): raise SystemExit("MISSING_SOURCE:"+src_rel)
   got=git_blob_sha(src)
   if got!=expected_blob: raise SystemExit("SOURCE_BLOB_DRIFT:"+src_rel+":"+got+":"+expected_blob)
   dst=root/dst_rel; dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dst)
  (root/"canonical/__init__.py").write_text("")
  (root/"canonical/runtime/__init__.py").write_text("")
  (root/"canonical/astra_runtime/state").mkdir(parents=True,exist_ok=True)
  (root/"canonical/astra_runtime/evidence").mkdir(parents=True,exist_ok=True)
  env=os.environ.copy(); env["PYTHONPATH"]=str(root)
  req={"benchmark_id":BENCHMARK_ID,"task_id":"SYNTHETIC_POSTRUN_TEMPLATE_DIAGNOSTIC","task_payload":{"instruction":"Respond with exactly SYNTHETIC_OK."},"allowed_tools":[]}
  cp=subprocess.run([sys.executable,"-c",DRIVER],input=json.dumps(req),text=True,capture_output=True,cwd=root,env=env,timeout=45)
  print("RETURN_CODE="+str(cp.returncode))
  print("STDOUT_BEGIN\n"+cp.stdout+"STDOUT_END")
  print("STDERR_BEGIN\n"+cp.stderr+"STDERR_END")
  print("TERMINAL_CASE_CONTENT_READ=false")
  print("TERMINAL_CASES_CONSUMED=0")
  print("FROZEN_RUNTIME_CLOSURE_FILE_COUNT="+str(len(FILES)))
 return 0

if __name__=="__main__": raise SystemExit(main())
