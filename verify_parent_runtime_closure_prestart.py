#!/usr/bin/env python3
import importlib.util, json, pathlib, sys
ROOT=pathlib.Path(__file__).resolve().parent

EXPECTED={
  "canonical/runtime/astra_runtime.py":"85642a89a0d99c5e6cafa2e116ffdc24f04de32c",
  "canonical/runtime/goal_compiler.py":"b446257ca01ee858ada2fb52d0c7925f2ea4391f",
  "canonical/runtime/capability_planner.py":"64ff65cb184f50d3336326f33cccfcc0a53301a8",
  "canonical/runtime/capability_proposal_generators.py":"71f2bbfda66a65d8d75e035b9ae073671ebd56e2",
  "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json":"b0fb5ccaf73552230dba24f914821d437b1a043d",
  "canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py":"6385b469f1287c971217dcac58af2ffebd81f9fd",
  "canonical/runtime/bound_capabilities/grounded_executable_composition.py":"8328e12804f64cab1c0d9509966cb1d2d8fb1f82",
  "canonical/runtime/bound_capabilities/grounded_executable_composition_verify.py":"ab9f6fc19937d23edb24dc26a2affed96cea0a9a",
}

import hashlib
def blob_sha(path):
    raw=path.read_bytes()
    return hashlib.sha1(("blob "+str(len(raw))+"\0").encode()+raw).hexdigest()

fail=[]
for rel,want in EXPECTED.items():
    p=ROOT/rel
    if not p.is_file():
        fail.append("MISSING:"+rel)
        continue
    got=blob_sha(p)
    if got!=want:
        fail.append("BLOB_MISMATCH:"+rel+":"+got)

runtime=None
if not fail:
    try:
        spec=importlib.util.spec_from_file_location("parent_runtime_closure_preflight",ROOT/"canonical/runtime/astra_runtime.py")
        runtime=importlib.util.module_from_spec(spec)
        sys.modules[spec.name]=runtime
        spec.loader.exec_module(runtime)
        runtime._load_goal_compiler()
        runtime._load_capability_planner()
        runtime._load_plain_goal_bound_grounding()
        runtime._load_grounded_executable_composition()
        runtime._load_grounded_executable_composition_verifier()
    except Exception as exc:
        fail.append("LOADER_FAILURE:"+type(exc).__name__+":"+str(exc))

grounding=None
composition=None
if runtime is not None and not fail:
    goal="Audit the Python tests with unittest and report passed failed and skipped counts."
    mission={"mission_id":"PARENT-RUNTIME-CLOSURE-PREFLIGHT","goal":goal}
    try:
        _,grounding=runtime._ground_plain_goal_to_bound_capabilities(mission,goal)
        if int(grounding.get("grounded_clause_count") or 0)<1:
            fail.append("SYNTHETIC_GROUNDING_EMPTY")
        else:
            _,composition=runtime._compose_grounding_to_capability_problem(
                mission,goal,grounding,verified_initial_facts=[]
            )
            if not isinstance(composition,dict) or not composition.get("problem"):
                fail.append("SYNTHETIC_COMPOSITION_EMPTY")
    except Exception as exc:
        fail.append("SYNTHETIC_PATH_FAILURE:"+type(exc).__name__+":"+str(exc))

report={
  "schema":"PROJECT_BRAIN_PARENT_RUNTIME_CLOSURE_PRESTART_GATE_V1",
  "status":"PASS" if not fail else "FAIL",
  "brain_base_commit":"43476b77a1314988183e3daed5f3f0d603f79877",
  "expected_blobs":EXPECTED,
  "grounded_clause_count":(grounding or {}).get("grounded_clause_count"),
  "composition_schema":(composition or {}).get("schema"),
  "network_task_executed":False,
  "parent_task_executed":False,
  "failures":fail,
}
(ROOT/"parent-runtime-closure-prestart-report.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
print(json.dumps(report,indent=2,sort_keys=True))
if fail: raise SystemExit(1)
