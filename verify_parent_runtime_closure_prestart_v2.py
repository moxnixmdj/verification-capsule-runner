#!/usr/bin/env python3
import hashlib, importlib.util, json, pathlib, sys

ROOT=pathlib.Path(__file__).resolve().parent
MANIFEST_PATH=ROOT/"PARENT_RUNTIME_ADAPTER_CLOSURE_MANIFEST_V1.json"
REGISTRY_PATH=ROOT/"canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"

def blob_sha(path):
    raw=path.read_bytes()
    return hashlib.sha1(("blob "+str(len(raw))+"\0").encode()+raw).hexdigest()

manifest=json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
registry_raw=json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
registry=registry_raw.get("capabilities") or {}
fail=[]

if blob_sha(REGISTRY_PATH)!=manifest["registry_blob"]:
    fail.append("REGISTRY_BLOB_MISMATCH")

verified={k:v for k,v in registry.items() if isinstance(v,dict) and v.get("status")=="VERIFIED_BOUND_CAPABILITY"}
if len(verified)!=manifest["verified_capability_count"]:
    fail.append("VERIFIED_CAPABILITY_COUNT_MISMATCH")

declared_modules=sorted({str(v.get("adapter_module") or "") for v in verified.values() if v.get("adapter_module")})
expected_modules=sorted(list(manifest["file_backed_adapters"])+[manifest["runtime_native_pseudo_adapter"]])
if declared_modules!=expected_modules:
    fail.append("REGISTRY_ADAPTER_SET_MISMATCH")

for rel,want in manifest["core_files"].items():
    p=ROOT/rel
    if not p.is_file():
        fail.append("CORE_FILE_MISSING:"+rel)
    elif blob_sha(p)!=want:
        fail.append("CORE_BLOB_MISMATCH:"+rel)

for module,want in manifest["file_backed_adapters"].items():
    p=ROOT/"canonical/runtime/bound_capabilities"/(module+".py")
    if not p.is_file():
        fail.append("ADAPTER_FILE_MISSING:"+module)
    elif blob_sha(p)!=want:
        fail.append("ADAPTER_BLOB_MISMATCH:"+module)

runtime_text=(ROOT/"canonical/runtime/astra_runtime.py").read_text(encoding="utf-8")
runtime_native_caps=[]
for cid,entry in verified.items():
    module=str(entry.get("adapter_module") or "")
    source=entry.get("source") or {}
    if module==manifest["runtime_native_pseudo_adapter"]:
        if source.get("type")!="runtime_native":
            fail.append("RUNTIME_NATIVE_SOURCE_TYPE_MISMATCH:"+cid)
            continue
        action_type=str(source.get("action_type") or "")
        template_type=str((entry.get("action_template") or {}).get("type") or "")
        if not action_type or action_type!=template_type:
            fail.append("RUNTIME_NATIVE_ACTION_DECLARATION_MISMATCH:"+cid)
            continue
        if ('"'+action_type+'"') not in runtime_text:
            fail.append("RUNTIME_NATIVE_ACTION_HANDLER_NOT_FOUND:"+cid+":"+action_type)
        runtime_native_caps.append(cid)
    else:
        if module not in manifest["file_backed_adapters"]:
            fail.append("UNMANIFESTED_FILE_ADAPTER:"+cid+":"+module)

# Exercise actual loader and compile->ground->compose code paths without any
# external network or parent-task execution.
composition_schema=None
grounded_clause_count=None
composition_verified=False
try:
    spec=importlib.util.spec_from_file_location(
        "project_brain_parent_runtime_closure_prestart",
        ROOT/"canonical/runtime/astra_runtime.py",
    )
    runtime=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=runtime
    spec.loader.exec_module(runtime)

    compiler=runtime._load_goal_compiler()
    planner=runtime._load_capability_planner()
    grounder=runtime._load_plain_goal_bound_grounding()
    composer=runtime._load_grounded_executable_composition()
    verifier=runtime._load_grounded_executable_composition_verifier()
    proposal_binder=runtime._load_runtime_helper("capability_proposal_generators")

    synthetic_registry={
      "synthetic.runtime.closure.audit":{
        "status":"VERIFIED_BOUND_CAPABILITY",
        "incremental_spend_usd":0,
        "cost":1,
        "requires":[],
        "provides":["synthetic.runtime.closure.verified"],
        "result_fields":["content"],
        "keywords":["synthetic","runtime","closure","audit"],
        "action_template":{
          "type":"read_file",
          "args":{"path":"canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"},
          "expect":{"type":"field_nonempty","field":"content"}
        }
      }
    }
    goal="Audit the synthetic runtime closure."
    grounding=grounder.ground(
        goal,synthetic_registry,
        compiler=compiler,
        proposal_binder=proposal_binder,
        root=ROOT,
        enforce_bindability=True,
    )
    grounded_clause_count=int(grounding.get("grounded_clause_count") or 0)
    if grounded_clause_count!=1 or grounding.get("unresolved_clause_indexes"):
        fail.append("SYNTHETIC_GROUNDING_NOT_COMPLETE")
    else:
        composition=composer.compose(
            goal,grounding,synthetic_registry,compiler,ROOT,
            verified_initial_facts=[],
        )
        composition_schema=composition.get("schema")
        ok,reason=verifier.verify(
            goal,composition,grounding,synthetic_registry,
            verified_initial_facts=[],
        )
        composition_verified=bool(ok)
        if not ok:
            fail.append("SYNTHETIC_COMPOSITION_VERIFY_FAILED:"+str(reason))
        problem=composition.get("problem") or {}
        plan=planner.plan_capabilities(problem)
        if plan.get("status")!="SOLVED":
            fail.append("SYNTHETIC_PLANNER_NOT_SOLVED")
except Exception as exc:
    fail.append("CORE_PATH_FAILURE:"+type(exc).__name__+":"+str(exc))

report={
  "schema":"PROJECT_BRAIN_PARENT_RUNTIME_CLOSURE_PRESTART_GATE_V2",
  "status":"PASS" if not fail else "FAIL",
  "brain_base_commit":manifest["brain_base_commit"],
  "verified_capability_count":len(verified),
  "declared_adapter_module_count":len(declared_modules),
  "file_backed_adapter_count":len(manifest["file_backed_adapters"]),
  "runtime_native_capability_count":len(runtime_native_caps),
  "runtime_native_capabilities":sorted(runtime_native_caps),
  "grounded_clause_count":grounded_clause_count,
  "composition_schema":composition_schema,
  "composition_verified":composition_verified,
  "network_task_executed":False,
  "parent_task_executed":False,
  "failures":fail,
}
(ROOT/"parent-runtime-closure-prestart-v2-report.json").write_text(
    json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8"
)
print(json.dumps(report,indent=2,sort_keys=True))
if fail:
    raise SystemExit(1)
