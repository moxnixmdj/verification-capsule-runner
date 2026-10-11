#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,os
from pathlib import Path
from typing import Any,Mapping

ROOT=Path(__file__).resolve().parents[2]
SURFACE=ROOT/"execution_guard/CURRENT_TERMINAL_EXECUTION_SURFACE_V1.json"
SLOT_ID="terminal-bench-science/rv-astrometry-fitting::trial-0"
TASK_DIGEST="sha256:8e086e1f7245067eaa9a67c259c1519204fa058d8664983066cd582ef258a1ea"
WORKFLOW=".github/workflows/execute-tb-science-rank22-20261011-v1.yml"
OUT=ROOT/"RANK22_EXECUTION_PREFLIGHT_V1.json"
SCHEMA="PROJECT_BRAIN_TB_SCIENCE_RANK22_ZERO_MODEL_EXECUTION_PREFLIGHT_V1"

def _blob(path:Path)->str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def _read(path:Path)->dict[str,Any]:
    value=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value,dict): raise RuntimeError("JSON_OBJECT_REQUIRED:"+str(path))
    return value

def _safe(rel:str)->Path:
    if not isinstance(rel,str) or not rel or rel.startswith("/"): raise RuntimeError("PATH_INVALID")
    p=(ROOT/rel).resolve()
    if p==ROOT or ROOT not in p.parents or not p.is_file(): raise RuntimeError("PATH_INVALID_OR_MISSING:"+rel)
    return p

def _binding(row:Any,label:str,errors:list[str])->Path|None:
    if not isinstance(row,Mapping):
        errors.append("BINDING_MISSING:"+label); return None
    rel,sha=row.get("path"),row.get("git_blob_sha")
    if not isinstance(rel,str) or not isinstance(sha,str):
        errors.append("BINDING_INVALID:"+label); return None
    try: p=_safe(rel)
    except Exception as exc:
        errors.append(type(exc).__name__+":"+str(exc)); return None
    if _blob(p)!=sha: errors.append("BINDING_BLOB_MISMATCH:"+label)
    return p

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--require-activation",action="store_true")
    ap.add_argument("--allow-staged",action="store_true")
    args=ap.parse_args()
    errors=[]
    try:
        surface=_read(SURFACE)
        if surface.get("schema")!="PROJECT_BRAIN_CURRENT_TERMINAL_EXECUTION_SURFACE_V1": errors.append("SURFACE_SCHEMA_INVALID")
        if surface.get("slot_id")!=SLOT_ID or surface.get("task_digest")!=TASK_DIGEST: errors.append("SURFACE_SLOT_OR_DIGEST_MISMATCH")
        if surface.get("workflow_path")!=WORKFLOW: errors.append("SURFACE_WORKFLOW_MISMATCH")
        if surface.get("task_started") is not False or surface.get("benchmark_trials_consumed")!=0: errors.append("SURFACE_ALREADY_CONSUMED")
        if not args.allow_staged:
            if surface.get("active") is not True: errors.append("SURFACE_NOT_ACTIVE")
            if surface.get("execution_authority") is not True: errors.append("EXECUTION_AUTHORITY_NOT_ACTIVE")
            if surface.get("task_read_authority") is not True: errors.append("TASK_READ_AUTHORITY_NOT_ACTIVE")
        workflow=_safe(WORKFLOW)
        if _blob(workflow)!=surface.get("workflow_git_blob_sha"): errors.append("WORKFLOW_BLOB_MISMATCH")

        behavior_path=_binding(surface.get("behavior"),"surface.behavior",errors)
        authority_path=_binding(surface.get("authority"),"surface.authority",errors)
        _binding(surface.get("ledger"),"surface.ledger",errors)
        _binding(surface.get("logical_attempt_claim_binding"),"surface.logical_attempt_claim_binding",errors)
        if behavior_path:
            behavior=_read(behavior_path)
            if behavior.get("scope")!="TB_SCIENCE_ZERO_MODEL_DETERMINISTIC_SCIENTIFIC_V1": errors.append("BEHAVIOR_SCOPE_INVALID")
            if behavior.get("slot_id")!=SLOT_ID or behavior.get("task_digest")!=TASK_DIGEST: errors.append("BEHAVIOR_SLOT_OR_DIGEST_MISMATCH")
            if behavior.get("workflow_path")!=WORKFLOW: errors.append("BEHAVIOR_WORKFLOW_MISMATCH")
            facts=behavior.get("behavior")
            if not isinstance(facts,Mapping): errors.append("BEHAVIOR_FACTS_INVALID")
            else:
                required_true=(
                    "execution_claim_bound_logical_attempt_identity","execution_claim_binding_digest_required",
                    "durable_start_cas_required","task_start_defined_by_cas_acquisition",
                    "agent_ready_precedes_start_cas","child_github_credentials_stripped",
                    "producer_dependency_inventory_complete","producer_external_model_cognition_free",
                    "aggregate_acceptance_credit_from_single_slot_forbidden",
                )
                for key in required_true:
                    if facts.get(key) is not True: errors.append("BEHAVIOR_REQUIRED_FALSE:"+key)
                if facts.get("producer_model_cognition_dependency_count")!=0: errors.append("MODEL_COGNITION_DEPENDENCY_COUNT_NONZERO")
                if facts.get("producer_model_cognition_dependencies")!=[]: errors.append("MODEL_COGNITION_DEPENDENCIES_PRESENT")
            bindings=behavior.get("runtime_bindings")
            if not isinstance(bindings,Mapping): errors.append("RUNTIME_BINDINGS_INVALID")
            else:
                for key in (
                    "kernel","agent","prestart_guard","transport","command_policy","qualification_test",
                    "start_cas","generic_start_cas","identity_primitive","claim_bound_identity_resolver",
                    "start_barrier","status_runner","finalizer","preflight"
                ):
                    _binding(bindings.get(key),"runtime."+key,errors)

        if authority_path:
            authority=_read(authority_path)
            if authority.get("slot_id")!=SLOT_ID or authority.get("task_digest")!=TASK_DIGEST: errors.append("AUTHORITY_SLOT_OR_DIGEST_MISMATCH")
            if authority.get("execution_branch")!="execute/tb-science-rank22-20261011-v1": errors.append("AUTHORITY_EXECUTION_BRANCH_INVALID")
            if authority.get("activation_filename")!="ACTIVATE_RANK22_V1_PR.json": errors.append("AUTHORITY_ACTIVATION_FILENAME_INVALID")

        from execution_guard.rank22_claim_bound_identity_v1 import resolve_claim_bound_identity
        identity=resolve_claim_bound_identity(root=ROOT,surface_rel="execution_guard/CURRENT_TERMINAL_EXECUTION_SURFACE_V1.json",expected_slot_id=SLOT_ID,expected_task_digest=TASK_DIGEST)
        if surface.get("logical_attempt_id")!=identity["logical_attempt_id"]: errors.append("LOGICAL_ATTEMPT_ID_MISMATCH")

        text=workflow.read_text(encoding="utf-8")
        low=text.casefold()
        for marker in ("llama-server",".gguf","/v1/chat/completions","ollama","vllm","litellm","anthropic.","transformers","openai.chat"):
            if marker in low: errors.append("WORKFLOW_MODEL_RUNTIME_MARKER:"+marker)
        if "persist-credentials: false" not in text: errors.append("WORKFLOW_CREDENTIAL_STRIP_MISSING")
        phases=[
            "Qualify exact zero-model scientific runtime before any task read",
            'rank22_start_cas_v1.py" --check-absent',
            "rank22_prestart_guard_v1.py",
            "rank22_zero_model_runner_v1.py",
            "rank22_finalize_receipt_v1.py",
        ]
        pos=[text.find(x) for x in phases]
        if any(x<0 for x in pos) or pos!=sorted(pos): errors.append("WORKFLOW_PHASE_ORDER_INVALID")

        if args.require_activation:
            rel=surface.get("activation_path")
            if not isinstance(rel,str): errors.append("ACTIVATION_PATH_MISSING")
            else:
                try:
                    activation=_read(_safe(rel))
                    if activation.get("schema")!="PROJECT_BRAIN_TB_SCIENCE_RANK22_ACTIVATION_V1": errors.append("ACTIVATION_SCHEMA_INVALID")
                    if activation.get("activate") is not True: errors.append("ACTIVATION_NOT_ARMED")
                    if activation.get("slot_id")!=SLOT_ID or activation.get("task_digest")!=TASK_DIGEST: errors.append("ACTIVATION_SLOT_OR_DIGEST_MISMATCH")
                    if activation.get("logical_attempt_id")!=identity["logical_attempt_id"]: errors.append("ACTIVATION_LOGICAL_ATTEMPT_MISMATCH")
                    if activation.get("execution_claim_binding_digest")!=identity["execution_claim_binding_digest"]: errors.append("ACTIVATION_CLAIM_DIGEST_MISMATCH")
                except Exception as exc: errors.append(type(exc).__name__+":"+str(exc))
            if os.environ.get("GITHUB_EVENT_NAME")!="pull_request": errors.append("PULL_REQUEST_EVENT_REQUIRED")
            if os.environ.get("GITHUB_RUN_ATTEMPT")!="1": errors.append("FIRST_RUN_ATTEMPT_REQUIRED")
            if os.environ.get("GITHUB_BASE_REF")!="terminal-execution-v1": errors.append("BASE_REF_MISMATCH")
            if os.environ.get("GITHUB_HEAD_REF")!="execute/tb-science-rank22-20261011-v1": errors.append("HEAD_REF_MISMATCH")
    except Exception as exc:
        errors.append(type(exc).__name__+":"+str(exc))
    row={
        "schema":SCHEMA,"status":"PASS" if not errors else "FAIL_CLOSED","pass":not errors,
        "errors":sorted(set(errors)),"slot_id":SLOT_ID,"task_digest":TASK_DIGEST,
        "task_read":False,"task_started":False,"benchmark_trials_consumed":0,
        "model_dependency_count":0,"external_model_runtime_calls":0,
        "acceptance_credit_delta":0,"terminal_credit_delta":0,
    }
    OUT.write_text(json.dumps(row,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(row,sort_keys=True))
    return 0 if not errors else 1

if __name__=="__main__":
    raise SystemExit(main())
