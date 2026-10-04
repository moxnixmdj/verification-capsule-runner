#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib, json, os, pathlib, shutil, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent
EXPECTED = {
    "astra_runtime": ("capsules/root2_livebench_astra_adapter_v1/canonical/runtime/astra_runtime.py", "7f5d16b1db69cb620954bc778e0ba6e15e687b75"),
    "adapter": ("capsules/root2_livebench_astra_adapter_v1/canonical/runtime/root2_livebench_if_astra_inference_adapter_v1.py", "7e3885fa7a6e56df656c066e0a8f17cfa21424e7"),
    "entrypoint": ("capsules/root2_livebench_astra_adapter_v1/canonical/runtime/root2_external_task_entrypoint_v1.py", "603beefe0db24102b86b7c965e5433bd880392af"),
    "adapter_registry": ("capsules/root2_livebench_astra_adapter_v1/canonical/governance/ROOT2_EXTERNAL_TASK_ADAPTER_REGISTRY_V1.json", "afa021a25d2de53e293d10ab6759e55eaabaea21"),
    "goal_compiler": ("canonical/runtime/goal_compiler.py", "4b61fe911471854ec15c7900816f61e9e55f602e"),
    "bound_registry": ("canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json", "7badee4878700f2cd4176beb8319d2a6a0bdf782"),
}

def git_blob_sha(path:pathlib.Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def memory_mb()->int|None:
    try:
        for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                return int(line.split()[1])//1024
    except Exception:
        return None
    return None

def main()->int:
    errors=[]
    actual={}
    for key,(rel,expected) in EXPECTED.items():
        p=ROOT/rel
        if not p.is_file():
            errors.append("MISSING:"+key+":"+rel); continue
        sha=git_blob_sha(p)
        actual[key]={"path":rel,"git_blob_sha":sha,"size":p.stat().st_size}
        if sha!=expected:
            errors.append("BLOB_MISMATCH:"+key+":"+sha+":"+expected)

    repo_private=str(os.environ.get("REPOSITORY_PRIVATE","")).lower()
    if repo_private!="false":
        errors.append("PUBLIC_REPOSITORY_CONTEXT_NOT_PROVED:"+repo_private)
    if os.environ.get("GITHUB_ACTIONS")!="true":
        errors.append("NOT_GITHUB_ACTIONS")

    result=None
    preflight=None
    with tempfile.TemporaryDirectory(prefix="brain-livebench-carrier-") as td:
        temp=pathlib.Path(td)
        (temp/"canonical/runtime").mkdir(parents=True)
        (temp/"canonical/governance").mkdir(parents=True)
        (temp/"canonical/astra_runtime/state").mkdir(parents=True)
        (temp/"canonical/astra_runtime/evidence").mkdir(parents=True)
        (temp/"canonical/__init__.py").write_text("",encoding="utf-8")
        (temp/"canonical/runtime/__init__.py").write_text("",encoding="utf-8")
        mapping={
          EXPECTED["astra_runtime"][0]:"canonical/runtime/astra_runtime.py",
          EXPECTED["adapter"][0]:"canonical/runtime/root2_livebench_if_astra_inference_adapter_v1.py",
          EXPECTED["entrypoint"][0]:"canonical/runtime/root2_external_task_entrypoint_v1.py",
          EXPECTED["adapter_registry"][0]:"canonical/governance/ROOT2_EXTERNAL_TASK_ADAPTER_REGISTRY_V1.json",
          EXPECTED["goal_compiler"][0]:"canonical/runtime/goal_compiler.py",
          EXPECTED["bound_registry"][0]:"canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json",
        }
        for src_rel,dst_rel in mapping.items():
            dst=temp/dst_rel
            dst.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(ROOT/src_rel,dst)

        old_path=list(sys.path)
        try:
            sys.path.insert(0,str(temp))
            for name in list(sys.modules):
                if name=="canonical" or name.startswith("canonical."):
                    sys.modules.pop(name,None)
            ep=importlib.import_module("canonical.runtime.root2_external_task_entrypoint_v1")
            adapter=importlib.import_module("canonical.runtime.root2_livebench_if_astra_inference_adapter_v1")
            preflight=ep.preflight("LIVEBENCH_IF_2026_06_25")
            if preflight.get("inference_ready") is not True:
                errors.append("ENTRYPOINT_PREFLIGHT_FAILED:"+json.dumps(preflight,sort_keys=True))
            request={
              "benchmark_id":"LIVEBENCH_IF_2026_06_25",
              "task_id":"SYNTHETIC_ZERO_REALITY_CARRIER_PROBE",
              "task_payload":{"instruction":"Read canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json."},
              "allowed_tools":[],
            }
            result=adapter.infer(request)
            if result.get("status")!="PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE":
                errors.append("ADAPTER_STATUS:"+str(result.get("status")))
            if result.get("cognition_dependency_class")!="MODEL_INDEPENDENT":
                errors.append("COGNITION_DEPENDENCY:"+str(result.get("cognition_dependency_class")))
            if int(result.get("model_dependency_count",-1))!=0:
                errors.append("MODEL_DEPENDENCY_COUNT:"+str(result.get("model_dependency_count")))
            trace=result.get("tool_trace") or []
            if not trace:
                errors.append("EMPTY_TOOL_TRACE")
            else:
                plan_types=[str((x.get("plan") or {}).get("type") or "") for x in trace if isinstance(x,dict)]
                if "read_file" not in plan_types:
                    errors.append("NATIVE_READ_NOT_EXECUTED:"+json.dumps(plan_types))
                if "finish" not in plan_types:
                    errors.append("FINISH_NOT_EXECUTED:"+json.dumps(plan_types))
            answer=str(result.get("answer") or "")
            if not answer.strip():
                errors.append("EMPTY_ANSWER")
        except Exception as exc:
            errors.append("EXECUTION_EXCEPTION:"+type(exc).__name__+":"+str(exc))
        finally:
            sys.path[:]=old_path

        stat=os.statvfs(temp)
        capacity={
          "cpu_count":os.cpu_count(),
          "memory_mb":memory_mb(),
          "free_disk_mb":(stat.f_bavail*stat.f_frsize)//(1024*1024),
          "github_actions":os.environ.get("GITHUB_ACTIONS"),
          "runner_os":os.environ.get("RUNNER_OS"),
          "repository_private":repo_private,
        }

    verdict={
      "schema":"PROJECT_BRAIN_LIVEBENCH_IF_ZERO_SPEND_CARRIER_PUBLIC_RUNNER_PROBE_V1",
      "status":"PASS__EXACT_BLOBS_SYNTHETIC_FULL_ADAPTER_PATH__PUBLIC_GITHUB_RUNNER" if not errors else "FAIL_CLOSED",
      "exact_blobs":actual,
      "synthetic_probe":{
        "benchmark_case_exposed":False,
        "fresh_reality_consumed":False,
        "instruction":"Read canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json.",
        "preflight":preflight,
        "result_status":(result or {}).get("status") if isinstance(result,dict) else None,
        "cognition_dependency_class":(result or {}).get("cognition_dependency_class") if isinstance(result,dict) else None,
        "model_dependency_count":(result or {}).get("model_dependency_count") if isinstance(result,dict) else None,
        "trace_types":[str((x.get("plan") or {}).get("type") or "") for x in ((result or {}).get("tool_trace") or []) if isinstance(x,dict)] if isinstance(result,dict) else [],
      },
      "carrier":capacity,
      "errors":errors,
      "hard_nonclaims":[
        "NO_LIVEBENCH_SCORE",
        "NO_LIVEBENCH_CASE_EXPOSURE",
        "NO_FRESH_REALITY_AUTHORITY",
        "NO_ACCEPTANCE_OR_PROMOTION_CREDIT",
        "THIS_PROBE_PROVES_ONLY_EXACT_RUNTIME_ADAPTER_COMPILER_REGISTRY_EXECUTABILITY_ON_THE_PUBLIC_STANDARD_RUNNER",
      ],
      "incremental_spend_usd":0,
      "new_reality_units_consumed":0,
      "terminal_cases_consumed":0,
      "acceptance_credit_delta":0,
    }
    print(json.dumps(verdict,indent=2,sort_keys=True))
    return 0 if not errors else 1

if __name__=="__main__":
    raise SystemExit(main())
