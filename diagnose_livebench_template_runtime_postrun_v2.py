#!/usr/bin/env python3
from __future__ import annotations
import json, os, pathlib, shutil, subprocess, sys, tempfile

ROOT=pathlib.Path(__file__).resolve().parent
BENCHMARK_ID="LIVEBENCH_IF_2026_06_25"
FILES={
 "capsules/root2_livebench_astra_adapter_v1/canonical/runtime/astra_runtime.py":"canonical/runtime/astra_runtime.py",
 "capsules/root2_livebench_astra_adapter_v1/canonical/runtime/root2_livebench_if_astra_inference_adapter_v1.py":"canonical/runtime/root2_livebench_if_astra_inference_adapter_v1.py",
 "capsules/root2_livebench_astra_adapter_v1/canonical/runtime/root2_external_task_entrypoint_v1.py":"canonical/runtime/root2_external_task_entrypoint_v1.py",
 "capsules/root2_livebench_astra_adapter_v1/canonical/governance/ROOT2_EXTERNAL_TASK_ADAPTER_REGISTRY_V1.json":"canonical/governance/ROOT2_EXTERNAL_TASK_ADAPTER_REGISTRY_V1.json",
 "canonical/runtime/goal_compiler.py":"canonical/runtime/goal_compiler.py",
 "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json":"canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json",
 "canonical/runtime/capability_planner.py":"canonical/runtime/capability_planner.py",
 "canonical/runtime/capability_proposal_generators.py":"canonical/runtime/capability_proposal_generators.py",
}
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
  for src_rel,dst_rel in FILES.items():
   src=ROOT/src_rel
   if not src.is_file(): raise SystemExit("MISSING_SOURCE:"+src_rel)
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
 return 0

if __name__=="__main__": raise SystemExit(main())
