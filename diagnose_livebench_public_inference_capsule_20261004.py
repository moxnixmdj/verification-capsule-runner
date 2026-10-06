from __future__ import annotations
import hashlib, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SUB=ROOT/"subject"/"livebench_zero_case_resource_fit_20261004"

EXPECTED_BLOBS={
  "astra_runtime.py":"7f5d16b1db69cb620954bc778e0ba6e15e687b75",
  "goal_compiler.py":"c895df9898bc97e4017f9e42bf6b27357ab1f315",
  "root2_livebench_if_astra_inference_adapter_v1.py":"7e3885fa7a6e56df656c066e0a8f17cfa21424e7",
}

def git_blob(path: Path) -> str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

observed={}
for name,want in EXPECTED_BLOBS.items():
    got=git_blob(SUB/name)
    assert got==want,(name,got,want)
    observed[name]=got

# These were the old crash-discovered dependencies. The isolated capsule must
# prove they are no longer required by the exact synthetic request path.
for forbidden in ("capability_planner.py","capability_proposal_generators.py"):
    assert not (SUB/forbidden).exists(), forbidden

RUNNER=r'''
from __future__ import annotations
import importlib.util, json, sys, types
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SUB=ROOT/"subject"/"livebench_zero_case_resource_fit_20261004"

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
adapter=load(
    "canonical.runtime.root2_livebench_if_astra_inference_adapter_v1",
    SUB/"root2_livebench_if_astra_inference_adapter_v1.py",
)

request={
  "benchmark_id":"LIVEBENCH_IF_2026_06_25",
  "task_id":"SYNTHETIC_ZERO_CASE_INFERENCE",
  "allowed_tools":[],
  "task_payload":{"instruction":"Reply with exactly SYNTHETIC_OK."},
}
out=adapter.infer(request)
assert out["status"]=="PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE",out
assert out["answer"]=="SYNTHETIC_OK",out
assert out["cognition_dependency_class"]=="MODEL_INDEPENDENT",out
assert out["model_dependency_count"]==0,out
assert out["tool_trace"] and out["tool_trace"][-1]["plan"]["type"]=="finish",out
assert out["tool_trace"][-1]["result"]["summary"]=="SYNTHETIC_OK",out
print(json.dumps({
  "status":"PASS",
  "answer":out["answer"],
  "cognition_dependency_class":out["cognition_dependency_class"],
  "model_dependency_count":out["model_dependency_count"],
  "planning_mode":out["tool_trace"] and "DETERMINISTIC_NATIVE_FINISH",
  "terminal_cases_consumed":0,
  "terminal_case_content_read":False,
  "paid_external_model_or_api_used":False,
},sort_keys=True))
'''

with tempfile.TemporaryDirectory(prefix="livebench-minimal-closure-") as td:
    capsule=Path(td)
    dst=capsule/"subject"/"livebench_zero_case_resource_fit_20261004"
    dst.mkdir(parents=True)
    for name in EXPECTED_BLOBS:
        shutil.copyfile(SUB/name,dst/name)

    # Astra reads the registry before invoking compile_goal. For the exact-literal
    # branch the registry's contents are semantically irrelevant: compile_goal
    # returns before any registry-dependent selection. Supplying the smallest
    # schema-valid empty registry therefore proves path-equivalent closure.
    registry=capsule/"canonical"/"runtime"/"BOUND_CAPABILITY_REGISTRY_V1.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(json.dumps({
      "schema":"PROJECT_BRAIN_BOUND_CAPABILITY_REGISTRY_V1",
      "capabilities":{},
    },sort_keys=True)+"\n",encoding="utf-8")

    runner=capsule/"run_isolated.py"
    runner.write_text(RUNNER,encoding="utf-8")

    env={"PATH":os.environ.get("PATH",""),"PYTHONIOENCODING":"utf-8"}
    proc=subprocess.run(
        [sys.executable,"-I",str(runner)],
        cwd=capsule,
        env=env,
        text=True,
        capture_output=True,
        timeout=60,
    )
    assert proc.returncode==0,{"stdout":proc.stdout,"stderr":proc.stderr}
    lines=[x for x in proc.stdout.splitlines() if x.strip()]
    assert lines,proc.stdout
    child=json.loads(lines[-1])
    assert child["status"]=="PASS",child

    project_files=sorted(
        p.relative_to(capsule).as_posix()
        for p in capsule.rglob("*")
        if p.is_file() and p.name!="run_isolated.py"
    )
    expected_project_files=sorted([
      "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json",
      "subject/livebench_zero_case_resource_fit_20261004/astra_runtime.py",
      "subject/livebench_zero_case_resource_fit_20261004/goal_compiler.py",
      "subject/livebench_zero_case_resource_fit_20261004/root2_livebench_if_astra_inference_adapter_v1.py",
    ])
    # __pycache__ is interpreter output, not an input dependency.
    inputs=[p for p in project_files if "/__pycache__/" not in p and not p.endswith(".pyc")]
    assert inputs==expected_project_files,(inputs,expected_project_files)

result={
  "schema":"PROJECT_BRAIN_LIVEBENCH_MINIMAL_TRANSITIVE_RUNTIME_CLOSURE_PUBLIC_VERIFICATION_V1",
  "status":"PASS__ISOLATED_MINIMAL_PROJECT_CLOSURE",
  "exact_code_git_blobs":observed,
  "project_input_file_count":4,
  "project_input_files":expected_project_files,
  "registry_binding":"SCHEMA_VALID_EMPTY__PATH_EQUIVALENT_FOR_EXACT_LITERAL_BRANCH",
  "old_crash_dependencies_absent":[
    "capability_planner.py",
    "capability_proposal_generators.py",
  ],
  "answer":child["answer"],
  "cognition_dependency_class":child["cognition_dependency_class"],
  "model_dependency_count":child["model_dependency_count"],
  "terminal_case_content_read":False,
  "terminal_cases_consumed":0,
  "paid_external_model_or_api_used":False,
  "fresh_reality_authority":False,
  "acceptance_credit":False,
}
print(json.dumps(result,sort_keys=True))
