from __future__ import annotations
import hashlib, importlib, json, pathlib, shutil, sys, tempfile

HERE = pathlib.Path(__file__).resolve().parent
SRC = HERE / "source"

def blob_bytes(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def blob(path: pathlib.Path) -> str:
    return blob_bytes(path.read_bytes())

def dump(path: pathlib.Path, obj) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw=(json.dumps(obj, indent=2, sort_keys=False)+"\n").encode()
    path.write_bytes(raw)
    return blob_bytes(raw)

with tempfile.TemporaryDirectory() as td:
    root=pathlib.Path(td)
    rt=root/"canonical/runtime"; gov=root/"canonical/governance"; ver=root/"canonical/verification"
    for p in (rt,gov,ver): p.mkdir(parents=True,exist_ok=True)
    (root/"canonical/__init__.py").write_text("")
    (rt/"__init__.py").write_text("")

    shutil.copy2(SRC/"r2_direct_route_registry_v1.py", rt/"r2_direct_route_registry_v1.py")
    shutil.copy2(SRC/"r2_direct_route_dynamic_admission_v1.py", rt/"r2_direct_route_dynamic_admission_v1.py")

    (rt/"raw_goal_archive_acceptance_v1.py").write_text("import re\nGRAMMAR=re.compile(r'(?!)')\n")
    (rt/"raw_goal_exact_literal_acceptance_v1.py").write_text("def preflight(goal): return {'matched':False}\n")
    (rt/"raw_goal_literal_json_acceptance_v1.py").write_text("def preflight(goal): return {'matched':False}\n")
    (rt/"r2_direct_end_to_end_adequacy_v1.py").write_text("def run(request): return {'pass':True,'route_id':'INLINE'}\n")

    world_src="""def preflight(request, repo_root=None):
    g=request.get('goal')
    if g=='ambiguous':
        return {'matched':False,'direct_route_semantic_open':True,'status':'OPEN__WORLDSET','route_id':'WORLD'}
    return {'matched': g=='world', 'route_id':'WORLD' if g=='world' else None}
def run(request, repo_root=None): return {'pass':True,'route_id':'WORLD'}
"""
    effect_src="""def preflight(request, repo_root=None):
    g=request.get('goal')
    if g=='ambiguous': raise RuntimeError('FALLTHROUGH_BUG')
    return {'matched': g in ('effect','overlap'), 'route_id':'EFFECT' if g in ('effect','overlap') else None}
def run(request, repo_root=None): return {'pass':True,'route_id':'EFFECT'}
"""
    dyn_src="""def preflight(request, repo_root=None):
    g=request.get('goal')
    return {'matched': g in ('dynamic','overlap'), 'route_id':'DYNAMIC' if g in ('dynamic','overlap') else None}
def run(request, repo_root=None): return {'pass':True,'route_id':'DYNAMIC'}
"""
    for name,src in [("route_world.py",world_src),("route_effect.py",effect_src),("route_dynamic.py",dyn_src)]:
        (rt/name).write_text(src)

    vshas={}
    for rid in ("WORLD","EFFECT","DYNAMIC"):
        vshas[rid]=dump(ver/(rid.lower()+".json"), {"status":"PASS","route_id":rid})

    activation={"schema":"SYNTHETIC","current_routes":[]}
    for rid,file in [("WORLD","route_world.py"),("EFFECT","route_effect.py"),("DYNAMIC","route_dynamic.py")]:
        activation["current_routes"].append({
            "route_id":rid,
            "capability_id":"cap."+rid.lower(),
            "runtime":"canonical/runtime/"+file,
            "runtime_git_blob_sha":blob(rt/file),
            "verification":{"path":"canonical/verification/"+rid.lower()+".json","git_blob_sha":vshas[rid]},
            "scope":"scope://"+rid.lower()
        })
    act_path=gov/"ACTIVATION.json"; act_sha=dump(act_path,activation)

    registry={
      "schema":"PROJECT_BRAIN_R2_DIRECT_ROUTE_REGISTRY_V1",
      "status":"ACTIVE_SYNTHETIC",
      "selection_role":"LEGACY_PRECEDENCE_OVERLAY_ONLY__CURRENT_R2_ACTIVATION_IS_DEPLOYABLE_ROUTE_UNIVERSE",
      "route_count":2,
      "routes":[
        {"route_id":"WORLD","priority":0,"active":True,"capability_id":"cap.world",
         "runtime_path":"canonical/runtime/route_world.py","runtime_git_blob_sha":blob(rt/"route_world.py"),
         "preflight_callable":"preflight","run_callable":"run",
         "verification_path":"canonical/verification/world.json","verification_git_blob_sha":vshas["WORLD"],
         "selection_class":"LEGACY_ORDERED_MIGRATION","scope":"scope://world","semantic_open_stops_fallback":True},
        {"route_id":"EFFECT","priority":1,"active":True,"capability_id":"cap.effect",
         "runtime_path":"canonical/runtime/route_effect.py","runtime_git_blob_sha":blob(rt/"route_effect.py"),
         "preflight_callable":"preflight","run_callable":"run",
         "verification_path":"canonical/verification/effect.json","verification_git_blob_sha":vshas["EFFECT"],
         "selection_class":"LEGACY_ORDERED_MIGRATION","scope":"scope://effect","semantic_open_stops_fallback":False}
      ]}
    reg_path=gov/"REGISTRY.json"; reg_sha=dump(reg_path,registry)
    dump(gov/"CURRENT_R2_DIRECT_ROUTE_REGISTRY.json",{
      "schema":"PROJECT_BRAIN_CURRENT_R2_DIRECT_ROUTE_REGISTRY_V1",
      "status":"ACTIVE_CURRENT_R2_DIRECT_ROUTE_SELECTION_METADATA_POINTER",
      "binding_semantics":"MUTABLE_CURRENT_POINTER_PATH_IDENTITY__IMMUTABLE_TARGET_GIT_BLOB_BOUND",
      "target":{"path":"canonical/governance/REGISTRY.json","git_blob_sha":reg_sha,"schema":"PROJECT_BRAIN_R2_DIRECT_ROUTE_REGISTRY_V1"}
    })

    adm={"schema":"PROJECT_BRAIN_R2_DIRECT_ROUTE_DYNAMIC_ADMISSIONS_V1",
         "status":"ACTIVE_DYNAMIC_ADMISSIONS__SYNTHETIC","selection_class":"UNIQUE_MATCH_REQUIRED",
         "collision_policy":"FAIL_CLOSED_ON_ANY_OTHER_DYNAMIC_OR_LEGACY_MATCH",
         "admission_count":0,"admissions":[]}
    adm_path=gov/"ADMISSIONS.json"; adm_sha=dump(adm_path,adm)
    dump(gov/"CURRENT_R2_DIRECT_ROUTE_ADMISSIONS.json",{
      "schema":"PROJECT_BRAIN_CURRENT_R2_DIRECT_ROUTE_DYNAMIC_ADMISSIONS_POINTER_V1",
      "status":"ACTIVE_CURRENT_R2_DYNAMIC_ADMISSIONS_POINTER",
      "binding_semantics":"MUTABLE_CURRENT_POINTER_PATH_IDENTITY__IMMUTABLE_TARGET_GIT_BLOB_BOUND",
      "target":{"path":"canonical/governance/ADMISSIONS.json","git_blob_sha":adm_sha,"schema":"PROJECT_BRAIN_R2_DIRECT_ROUTE_DYNAMIC_ADMISSIONS_V1"}
    })
    dump(gov/"CURRENT_R2_DECISION_INTELLIGENCE.json",{
      "direct_adequacy":{"activation_path":"canonical/governance/ACTIVATION.json",
      "activation_git_blob_sha":act_sha,"current_route_count":3}
    })

    sys.path.insert(0,str(root))
    router=importlib.import_module("canonical.runtime.r2_direct_route_registry_v1")
    admission=importlib.import_module("canonical.runtime.r2_direct_route_dynamic_admission_v1")

    cat=router.catalog(repo_root=root)
    assert cat["pass"] and cat["route_count"]==3, cat
    assert cat["activation_auto_admitted_route_count"]==1, cat
    a=router.preflight({"task_id":"t","goal":"ambiguous"},repo_root=root)
    assert a.get("direct_route_semantic_open") is True and a.get("route_id")=="WORLD", a
    d=router.preflight({"task_id":"t","goal":"dynamic"},repo_root=root)
    assert d.get("matched") is True and d.get("route_id")=="DYNAMIC", d
    c=router.preflight({"task_id":"t","goal":"overlap"},repo_root=root)
    assert c["status"]=="FAIL_CLOSED__DIRECT_ROUTE_COLLISION", c

    candidate={
      "schema":"PROJECT_BRAIN_R2_DIRECT_ROUTE_DEPLOYMENT_CANDIDATE_V1",
      "route_id":"NEW","capability_id":"cap.new","deployment_requested":True,
      "selection_class":"UNIQUE_MATCH_REQUIRED","incremental_spend_usd":0,"terminal_authority":False,
      "runtime_path":"canonical/runtime/route_dynamic.py","runtime_git_blob_sha":blob(rt/"route_dynamic.py"),
      "route_verification_path":"canonical/verification/dynamic.json",
      "route_verification_git_blob_sha":vshas["DYNAMIC"],
      "preflight_callable":"preflight","run_callable":"run","scope":"scope://new"
    }
    cand_path=gov/"candidate.json"; cand_sha=dump(cand_path,candidate)
    receipt={
      "schema":"PROJECT_BRAIN_R2_DIRECT_ROUTE_DEPLOYMENT_INDEPENDENT_RECEIPT_V1",
      "status":"INDEPENDENT_PASS__R2_DIRECT_ROUTE_DEPLOYMENT",
      "candidate_path":"canonical/governance/candidate.json","candidate_git_blob_sha":cand_sha,
      "route_id":"NEW","runtime_path":"canonical/runtime/route_dynamic.py",
      "runtime_git_blob_sha":blob(rt/"route_dynamic.py"),
      "route_verification_path":"canonical/verification/dynamic.json",
      "route_verification_git_blob_sha":vshas["DYNAMIC"],
      "selection_class":"UNIQUE_MATCH_REQUIRED","independent_verified":True,
      "preflight_pure_no_effect":True,"matched_route_failure_no_fallthrough":True,
      "producer_independent_acceptance":True,"exact_raw_obligation_acceptance":True,
      "deployment_eligible":True,"verification_authority_mutated":False,
      "promotion_authority":False,"terminal_authority":False,"incremental_spend_usd":0
    }
    rec_path=ver/"receipt.json"; dump(rec_path,receipt)
    compiled=admission.compile_admission(repo_root=root,current_manifest=adm,
      candidate_path="canonical/governance/candidate.json",receipt_path="canonical/verification/receipt.json")
    assert compiled["manifest"]["admission_count"]==1 and compiled["manifest"]["admissions"][0]["route_id"]=="NEW", compiled

    reg_path.write_text(reg_path.read_text()+"\n")
    try:
        router.load_registry(repo_root=root)
    except Exception as exc:
        assert "BLOB_MISMATCH" in str(exc), exc
    else:
        raise AssertionError("pointer hash drift did not fail closed")

    print("PASS__PR3514_CORE_EXECUTION_CAPSULE")
    print(json.dumps({
      "dispatcher_source_git_blob_sha":"151641160bb6623a89e2584f2b3cd5cb62050bd4",
      "dynamic_admission_source_git_blob_sha":"65fc5bdb5283944d058c6c6a2ff1fe360aa17489",
      "synthetic_deployable_routes":3,
      "activation_auto_admitted":1,
      "semantic_open_barrier":"PASS",
      "dynamic_unique_match":"PASS",
      "dynamic_legacy_collision":"FAIL_CLOSED_AS_REQUIRED",
      "pointer_hash_drift":"FAIL_CLOSED_AS_REQUIRED",
      "admission_compile":"PASS"
    },sort_keys=True))
