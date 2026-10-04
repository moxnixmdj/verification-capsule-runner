#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib, json, pathlib, shutil, sys, tempfile, traceback

ROOT=pathlib.Path(__file__).resolve().parent
EXPECTED={
 "astra_runtime":("capsules/root2_livebench_astra_adapter_v1/canonical/runtime/astra_runtime.py","7f5d16b1db69cb620954bc778e0ba6e15e687b75"),
 "adapter":("capsules/root2_livebench_astra_adapter_v1/canonical/runtime/root2_livebench_if_astra_inference_adapter_v1.py","7e3885fa7a6e56df656c066e0a8f17cfa21424e7"),
 "entrypoint":("capsules/root2_livebench_astra_adapter_v1/canonical/runtime/root2_external_task_entrypoint_v1.py","603beefe0db24102b86b7c965e5433bd880392af"),
 "adapter_registry":("capsules/root2_livebench_astra_adapter_v1/canonical/governance/ROOT2_EXTERNAL_TASK_ADAPTER_REGISTRY_V1.json","afa021a25d2de53e293d10ab6759e55eaabaea21"),
 "goal_compiler":("canonical/runtime/goal_compiler.py","4b61fe911471854ec15c7900816f61e9e55f602e"),
 "bound_registry":("canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json","7badee4878700f2cd4176beb8319d2a6a0bdf782"),
 "capability_planner":("canonical/runtime/capability_planner.py","64ff65cb184f50d3336326f33cccfcc0a53301a8"),
 "capability_proposal_generators":("canonical/runtime/capability_proposal_generators.py","71f2bbfda66a65d8d75e035b9ae073671ebd56e2"),
}
INSTRUCTION="Reply with exactly SYNTHETIC_OK."

def blob_sha(p):
 b=p.read_bytes(); return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def main():
 errors=[]; exact={}
 for k,(rel,expected) in EXPECTED.items():
  p=ROOT/rel
  if not p.is_file(): errors.append("MISSING:"+k+":"+rel); continue
  got=blob_sha(p); exact[k]={"path":rel,"git_blob_sha":got}
  if got!=expected: errors.append("BLOB_MISMATCH:"+k+":"+got+":"+expected)
 result=None; exc_info=None
 with tempfile.TemporaryDirectory(prefix="brain-livebench-exact-reply-") as td:
  temp=pathlib.Path(td)
  for d in ("canonical/runtime","canonical/governance","canonical/astra_runtime/state","canonical/astra_runtime/evidence"):
   (temp/d).mkdir(parents=True,exist_ok=True)
  (temp/"canonical/__init__.py").write_text("")
  (temp/"canonical/runtime/__init__.py").write_text("")
  mapping={
   EXPECTED["astra_runtime"][0]:"canonical/runtime/astra_runtime.py",
   EXPECTED["adapter"][0]:"canonical/runtime/root2_livebench_if_astra_inference_adapter_v1.py",
   EXPECTED["entrypoint"][0]:"canonical/runtime/root2_external_task_entrypoint_v1.py",
   EXPECTED["adapter_registry"][0]:"canonical/governance/ROOT2_EXTERNAL_TASK_ADAPTER_REGISTRY_V1.json",
   EXPECTED["goal_compiler"][0]:"canonical/runtime/goal_compiler.py",
   EXPECTED["bound_registry"][0]:"canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json",
   EXPECTED["capability_planner"][0]:"canonical/runtime/capability_planner.py",
   EXPECTED["capability_proposal_generators"][0]:"canonical/runtime/capability_proposal_generators.py",
  }
  for src,dst in mapping.items():
   q=temp/dst; q.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(ROOT/src,q)
  old=list(sys.path)
  try:
   sys.path.insert(0,str(temp))
   for n in list(sys.modules):
    if n=="canonical" or n.startswith("canonical."): sys.modules.pop(n,None)
   adapter=importlib.import_module("canonical.runtime.root2_livebench_if_astra_inference_adapter_v1")
   request={"benchmark_id":"LIVEBENCH_IF_2026_06_25","task_id":"SYNTHETIC_ZERO_CASE_EXACT_REPLY","task_payload":{"instruction":INSTRUCTION},"allowed_tools":[]}
   result=adapter.infer(request)
   if result.get("status")!="PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE":
    errors.append("ADAPTER_STATUS:"+str(result.get("status")))
   if result.get("cognition_dependency_class")!="MODEL_INDEPENDENT":
    errors.append("COGNITION_DEPENDENCY:"+str(result.get("cognition_dependency_class")))
   if int(result.get("model_dependency_count",-1))!=0:
    errors.append("MODEL_DEPENDENCY_COUNT:"+str(result.get("model_dependency_count")))
   answer=str(result.get("answer") or "")
   if answer.strip()!="SYNTHETIC_OK":
    errors.append("EXACT_REPLY_MISMATCH:"+repr(answer))
  except Exception as exc:
   exc_info={"type":type(exc).__name__,"message":str(exc),"traceback":traceback.format_exc()[-12000:]}
   errors.append("EXECUTION_EXCEPTION:"+type(exc).__name__+":"+str(exc))
  finally:
   sys.path[:]=old
 verdict={
  "schema":"PROJECT_BRAIN_LIVEBENCH_IF_EXACT_REPLY_ZERO_CASE_PROBE_V1",
  "status":"PASS__EXACT_REPLY_ZERO_CASE_FULL_ADAPTER_PATH" if not errors else "FAIL_CLOSED",
  "exact_blobs":exact,
  "instruction":INSTRUCTION,
  "result_status":result.get("status") if isinstance(result,dict) else None,
  "answer":result.get("answer") if isinstance(result,dict) else None,
  "trace_types":[str((x.get("plan") or {}).get("type") or "") for x in ((result or {}).get("tool_trace") or []) if isinstance(x,dict)] if isinstance(result,dict) else [],
  "exception":exc_info,
  "errors":errors,
  "terminal_cases_consumed":0,
  "new_reality_units_consumed":0,
  "incremental_spend_usd":0,
  "fresh_reality_authority":False,
  "acceptance_credit_delta":0,
  "promotion_authority":False,
  "hard_nonclaims":["NO_LIVEBENCH_SCORE","NO_TERMINAL_CASE_EXPOSURE","NO_FRESH_REALITY_AUTHORITY","NO_ACCEPTANCE_OR_PROMOTION_CREDIT"]
 }
 print(json.dumps(verdict,indent=2,sort_keys=True))
 return 0 if not errors else 1

if __name__=="__main__": raise SystemExit(main())
