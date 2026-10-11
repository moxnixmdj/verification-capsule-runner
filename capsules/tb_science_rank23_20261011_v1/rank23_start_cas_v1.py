#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,os,re,sys
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
EG=ROOT/"execution_guard"
for p in (str(ROOT),str(EG)):
    if p not in sys.path: sys.path.insert(0,p)

import terminal_slot_start_cas_v2 as generic_cas
from execution_guard.rank23_claim_bound_identity_v1 import resolve_claim_bound_identity

SCHEMA="PROJECT_BRAIN_TB_SCIENCE_RANK23_START_CAS_V1"
SLOT_ID="terminal-bench-science/dna-storage-codec::trial-0"
TASK_DIGEST="sha256:bde6852289db3f5474aedc96c54aca201d11be6c61f4fef019998b2b689e65ac"
EXPECTED_REPOSITORY="moxnixmdj/verification-capsule-runner"
EXPECTED_BASE="terminal-execution-v1"
SURFACE_REL="execution_guard/CURRENT_TERMINAL_EXECUTION_SURFACE_V1.json"
PREFLIGHT_RECEIPT="RANK23_PRESTART_GUARD.json"
AGENT_READY_REL="RANK23_AGENT_START_BARRIER/AGENT_READY.json"
CHECK_RECEIPT="RANK23_START_CAS_CHECK_V1.json"
ACQUIRE_RECEIPT="RANK23_START_CAS_V1.json"
STATUS_STORE_ANCHOR_SHA="8545e23a3113b2e4aef753799eb71d7c192ae815"
HARBOR_VERSION="0.23.0"

class StartCASError(RuntimeError): pass

def _read(path:Path)->dict[str,Any]:
    value=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value,dict): raise StartCASError("JSON_OBJECT_REQUIRED:"+str(path))
    return value

def _blob(path:Path)->str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def _sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def _canon_sha(value:Any)->str:
    raw=json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()

def _safe(rel:str)->Path:
    if not isinstance(rel,str) or not rel or rel.startswith("/"): raise StartCASError("PATH_INVALID")
    p=(ROOT/rel).resolve()
    if p==ROOT or ROOT not in p.parents or not p.is_file(): raise StartCASError("PATH_INVALID_OR_MISSING:"+rel)
    return p

def _binding(row:Any,label:str)->tuple[Path,str]:
    if not isinstance(row,dict): raise StartCASError("BINDING_REQUIRED:"+label)
    p=_safe(row.get("path"))
    want=row.get("git_blob_sha")
    got=_blob(p)
    if got!=want: raise StartCASError("BINDING_BLOB_MISMATCH:"+label)
    return p,got

def _event_context()->dict[str,Any]:
    if os.environ.get("GITHUB_EVENT_NAME")!="pull_request": raise StartCASError("PULL_REQUEST_EVENT_REQUIRED")
    if os.environ.get("GITHUB_RUN_ATTEMPT")!="1": raise StartCASError("FIRST_RUN_ATTEMPT_REQUIRED")
    if os.environ.get("GITHUB_BASE_REF")!=EXPECTED_BASE: raise StartCASError("BASE_REF_MISMATCH")
    if os.environ.get("GITHUB_REPOSITORY")!=EXPECTED_REPOSITORY: raise StartCASError("REPOSITORY_MISMATCH")
    surface=_read(ROOT/SURFACE_REL)
    if surface.get("active") is not True or surface.get("execution_authority") is not True:
        raise StartCASError("EXECUTION_AUTHORITY_NOT_ACTIVE")
    if surface.get("task_started") is not False or surface.get("benchmark_trials_consumed")!=0:
        raise StartCASError("SURFACE_ALREADY_CONSUMED")
    if surface.get("slot_id")!=SLOT_ID or surface.get("task_digest")!=TASK_DIGEST:
        raise StartCASError("SURFACE_SLOT_OR_DIGEST_MISMATCH")
    authority_path,_=_binding(surface.get("authority"),"surface.authority")
    authority=_read(authority_path)
    head=authority.get("execution_branch")
    activation_name=authority.get("activation_filename")
    if os.environ.get("GITHUB_HEAD_REF")!=head: raise StartCASError("HEAD_REF_MISMATCH")
    event=_read(Path(os.environ.get("GITHUB_EVENT_PATH") or ""))
    pr=event.get("pull_request") or {}
    if ((pr.get("head") or {}).get("repo") or {}).get("full_name")!=EXPECTED_REPOSITORY:
        raise StartCASError("SAME_REPOSITORY_HEAD_REQUIRED")
    if (pr.get("head") or {}).get("ref")!=head or (pr.get("base") or {}).get("ref")!=EXPECTED_BASE:
        raise StartCASError("EVENT_REF_MISMATCH")
    activation_rel=surface.get("activation_path")
    if not isinstance(activation_rel,str) or Path(activation_rel).name!=activation_name:
        raise StartCASError("ACTIVATION_PATH_MISMATCH")
    activation_path=_safe(activation_rel)
    activation=_read(activation_path)
    if activation.get("schema")!="PROJECT_BRAIN_TB_SCIENCE_RANK23_ACTIVATION_V1" or activation.get("activate") is not True:
        raise StartCASError("ACTIVATION_INVALID")
    if activation.get("slot_id")!=SLOT_ID or activation.get("task_digest")!=TASK_DIGEST:
        raise StartCASError("ACTIVATION_SLOT_OR_DIGEST_MISMATCH")
    identity=resolve_claim_bound_identity(
        root=ROOT,surface_rel=SURFACE_REL,
        expected_slot_id=SLOT_ID,expected_task_digest=TASK_DIGEST,
    )
    if activation.get("logical_attempt_id")!=identity["logical_attempt_id"]:
        raise StartCASError("ACTIVATION_LOGICAL_ATTEMPT_MISMATCH")
    if activation.get("execution_claim_binding_digest")!=identity["execution_claim_binding_digest"]:
        raise StartCASError("ACTIVATION_CLAIM_DIGEST_MISMATCH")
    return {"surface":surface,"authority":authority,"activation_path":activation_path,"identity":identity}

def _open_stores():
    repo=os.environ.get("GITHUB_REPOSITORY") or ""
    token=os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
    sha=os.environ.get("GITHUB_SHA") or ""
    if repo!=EXPECTED_REPOSITORY or not token or not re.fullmatch(r"[0-9a-f]{40}",sha):
        raise StartCASError("STATUS_STORE_ENVIRONMENT_INVALID")
    req=generic_cas.request_factory(token)
    status,commit,_=req("GET",f"/repos/{repo}/git/commits/{sha}")
    tree=(commit.get("tree") or {}).get("sha") if status==200 and isinstance(commit,dict) else None
    if not isinstance(tree,str) or not re.fullmatch(r"[0-9a-f]{40}",tree):
        raise StartCASError("BASE_TREE_UNCONFIRMED__NO_START")
    s,_c,_h=req("GET",f"/repos/{repo}/git/commits/{STATUS_STORE_ANCHOR_SHA}")
    if s!=200: raise StartCASError("STATUS_STORE_ANCHOR_UNCONFIRMED__NO_START")
    status_store=generic_cas.SerializedStatusObjectStore(req,repo,STATUS_STORE_ANCHOR_SHA,generic_cas.NAMESPACE)
    legacy=generic_cas.v1.GitHubRefStore(req,repo,sha,tree,generic_cas.NAMESPACE)
    return status_store,legacy

def _key()->str:
    return generic_cas.slot_start_key(SLOT_ID,TASK_DIGEST)

def _read_record(store):
    try: value=store.read(_key())
    except Exception as exc: raise StartCASError("START_RECORD_READ_UNCONFIRMED__NO_START") from exc
    if value is not None and not isinstance(value,dict): raise StartCASError("START_RECORD_INVALID")
    return value

def _runtime_identity(surface:dict[str,Any])->tuple[str,dict[str,Any]]:
    behavior_path,behavior_blob=_binding(surface.get("behavior"),"surface.behavior")
    behavior=_read(behavior_path)
    bindings=behavior.get("runtime_bindings")
    if not isinstance(bindings,dict): raise StartCASError("RUNTIME_BINDINGS_INVALID")
    exact={}
    for label in (
        "codec","adapter","agent","prestart_guard","transport","command_policy","codec_test","adapter_test","agent_test",
        "start_cas","generic_start_cas","identity_primitive","claim_bound_identity_resolver",
        "start_barrier","status_runner","finalizer","preflight"
    ):
        _p,b=_binding(bindings.get(label),"runtime."+label)
        exact[label]=b
    material={
        "schema":"PROJECT_BRAIN_TB_SCIENCE_RANK23_DNA_STORAGE_RUNTIME_IDENTITY_V1",
        "behavior_git_blob_sha":behavior_blob,
        "runtime_bindings":exact,
        "harbor_version":HARBOR_VERSION,
        "model_dependency_count":0,
        "external_model_runtime_calls":0,
        "network_dependency_count":0,
    }
    return _canon_sha(material),material

def _intent(context:dict[str,Any])->tuple[generic_cas.StartIntent,dict[str,Any]]:
    guard_path=ROOT/PREFLIGHT_RECEIPT
    guard=_read(guard_path)
    if guard.get("pass") is not True or guard.get("task_read") is not True or guard.get("task_started") is not False:
        raise StartCASError("PRESTART_GUARD_NOT_AUTHORIZED")
    if not str(guard.get("status") or "").startswith("PASS__RANK23_EXACT_DIGEST_TASK_READ__DONOR_FREE_DNA_CONTRACT_QUALIFIED"):
        raise StartCASError("PRESTART_STATUS_INVALID")
    identity=context["identity"]
    logical=identity["logical_attempt_id"]
    if guard.get("logical_attempt_id")!=logical: raise StartCASError("PRESTART_IDENTITY_MISMATCH")
    ready_path=ROOT/AGENT_READY_REL
    ready=_read(ready_path)
    if ready.get("schema")!="PROJECT_BRAIN_AGENT_START_READY_V1":
        raise StartCASError("AGENT_READY_SCHEMA_INVALID")
    if ready.get("slot_id")!=SLOT_ID or ready.get("task_digest")!=TASK_DIGEST or ready.get("logical_attempt_id")!=logical:
        raise StartCASError("AGENT_READY_IDENTITY_MISMATCH")
    ready_sha=_sha(ready_path)
    surface=context["surface"]
    workflow=_safe(surface.get("workflow_path"))
    workflow_blob=_blob(workflow)
    if workflow_blob!=surface.get("workflow_git_blob_sha"): raise StartCASError("WORKFLOW_BLOB_MISMATCH")
    _ap,authority_blob=_binding(surface.get("authority"),"surface.authority")
    activation_blob=_blob(context["activation_path"])
    runtime_id,runtime_material=_runtime_identity(surface)
    intent=generic_cas.StartIntent(
        slot_id=SLOT_ID,task_digest=TASK_DIGEST,logical_attempt_id=logical,
        workflow_git_blob_sha=workflow_blob,authority_git_blob_sha=authority_blob,
        activation_git_blob_sha=activation_blob,runtime_identity_sha256=runtime_id,
        prestart_receipt_sha256=_sha(guard_path),agent_ready_receipt_sha256=ready_sha,
        github_run_id=os.environ.get("GITHUB_RUN_ID") or "",
        github_sha=os.environ.get("GITHUB_SHA") or "",
    )
    intent.validate()
    return intent,{
        "logical_attempt_id":logical,"execution_claim_binding_digest":identity["execution_claim_binding_digest"],
        "workflow_git_blob_sha":workflow_blob,"authority_git_blob_sha":authority_blob,
        "activation_git_blob_sha":activation_blob,"runtime_identity_sha256":runtime_id,
        "runtime_identity_material":runtime_material,"prestart_receipt_sha256":_sha(guard_path),
        "agent_ready_receipt_sha256":ready_sha,
    }

def _output(name:str,value:str)->None:
    p=os.environ.get("GITHUB_OUTPUT")
    if p:
        with open(p,"a",encoding="utf-8") as fh: fh.write(f"{name}={value}\n")

def main()->int:
    ap=argparse.ArgumentParser(); g=ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check-absent",action="store_true"); g.add_argument("--acquire",action="store_true")
    args=ap.parse_args(); mode="check-absent" if args.check_absent else "acquire"
    result={
        "schema":SCHEMA,"mode":mode,"slot_id":SLOT_ID,"task_digest":TASK_DIGEST,
        "pass":False,"lock_absent":False,"acquired":False,"task_started":False,
        "benchmark_trials_consumed":0,"replay_authority":False,"replacement_carrier_authority":False,
        "model_dependency_count":0,"incremental_spend_usd":0,
    }
    rc=1
    try:
        context=_event_context()
        store,legacy=_open_stores()
        legacy_existing=_read_record(legacy); current=_read_record(store)
        absent=legacy_existing is None and current is None
        result["legacy_ref_absent"]=legacy_existing is None
        result["status_record_absent"]=current is None
        result["lock_absent"]=absent
        if args.check_absent:
            result["pass"]=absent
            result["status"]="PASS__LEGACY_REF_AND_STATUS_START_RECORD_ABSENT__NO_TASK_START" if absent else "FAIL_CLOSED__START_RECORD_ALREADY_EXISTS"
            rc=0 if absent else 1
        elif not absent:
            result["status"]="FAIL_CLOSED__START_ALREADY_EXISTS"
        else:
            intent,binding=_intent(context)
            receipt=generic_cas.reserve_start_once(store,intent)
            persisted=_read_record(store)
            if not isinstance(persisted,dict): raise StartCASError("START_RECORD_POSTWRITE_MISSING")
            expected={
                "slot_id":intent.slot_id,"task_digest":intent.task_digest,"logical_attempt_id":intent.logical_attempt_id,
                "workflow_git_blob_sha":intent.workflow_git_blob_sha,"authority_git_blob_sha":intent.authority_git_blob_sha,
                "activation_git_blob_sha":intent.activation_git_blob_sha,"runtime_identity_sha256":intent.runtime_identity_sha256,
                "prestart_receipt_sha256":intent.prestart_receipt_sha256,
                "agent_ready_receipt_sha256":intent.agent_ready_receipt_sha256,
                "github_run_id":intent.github_run_id,"github_sha":intent.github_sha,
                "replay_authority":False,"replacement_carrier_authority":False,
            }
            for k,v in expected.items():
                if persisted.get(k)!=v: raise StartCASError("START_RECORD_BINDING_MISMATCH:"+k)
            result.update(binding); result.update({
                "pass":True,"acquired":True,"task_started":True,"benchmark_trials_consumed":1,
                "status":"PASS__AGENT_READY_BOUND_START_COMMITTED__IRREVERSIBLE_SLOT_START",
                "generic_cas_receipt":receipt,"durable_record_sha256":_canon_sha(persisted),
            }); rc=0
    except Exception as exc:
        result["status"]="FAIL_CLOSED__START_CAS_ERROR"; result["error_type"]=type(exc).__name__; result["error"]=str(exc)
    out=ROOT/(CHECK_RECEIPT if args.check_absent else ACQUIRE_RECEIPT)
    out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    _output("lock_absent","true" if result.get("lock_absent") else "false")
    _output("acquired","true" if result.get("acquired") else "false")
    print(json.dumps(result,sort_keys=True))
    return rc

if __name__=="__main__":
    raise SystemExit(main())
