from __future__ import annotations
import argparse, hashlib, json, os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
C=Path(__file__).resolve().parent
SCHEMA="PROJECT_BRAIN_TB_SCIENCE_RANK15_EXECUTION_PREFLIGHT_V3"
SURFACE_SCHEMA="PROJECT_BRAIN_CURRENT_TERMINAL_EXECUTION_SURFACE_V1"
SLOT="terminal-bench-science/protein-active-learning::trial-0"
DIGEST="sha256:d7e16b7c468551b468364cf2a86dba2383b007f3f2f01c6d2ce01d99ff30d48f"
WORKFLOW=".github/workflows/execute-tb-science-rank15-20261009-v3.yml"
BASE="terminal-execution-v1"
BRANCH="execute/tb-science-rank15-20261009-v3"
ACTIVATION="ACTIVATE_RANK15_V3_PR.json"

def git_blob(path: Path) -> str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def load(path: Path) -> dict:
    value=json.loads(path.read_text())
    if not isinstance(value,dict): raise RuntimeError("JSON_OBJECT_REQUIRED:"+str(path))
    return value

def _verify_binding(surface: dict, key: str, errors: list[str]) -> None:
    row=surface.get(key)
    if not isinstance(row,dict):
        errors.append("SURFACE_BINDING_MISSING:"+key); return
    path=row.get("path"); expected=row.get("git_blob_sha")
    if not isinstance(path,str) or not path or not isinstance(expected,str) or len(expected)!=40:
        errors.append("SURFACE_BINDING_INVALID:"+key); return
    p=ROOT/path
    if not p.is_file():
        errors.append("BOUND_FILE_MISSING:"+key+":"+path); return
    actual=git_blob(p)
    if actual!=expected:
        errors.append("BOUND_FILE_BLOB_MISMATCH:"+key+":"+actual+"!="+expected)

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--require-activation",action="store_true")
    args=ap.parse_args()
    errors=[]
    surface=load(ROOT/"execution_guard/CURRENT_TERMINAL_EXECUTION_SURFACE_V1.json")
    if surface.get("schema")!=SURFACE_SCHEMA: errors.append("SURFACE_SCHEMA_INVALID")
    if surface.get("slot_id")!=SLOT or surface.get("task_digest")!=DIGEST: errors.append("SURFACE_SLOT_IDENTITY_MISMATCH")
    if surface.get("workflow_path")!=WORKFLOW: errors.append("SURFACE_WORKFLOW_PATH_MISMATCH")
    wp=ROOT/WORKFLOW
    if not wp.is_file(): errors.append("WORKFLOW_MISSING")
    elif git_blob(wp)!=surface.get("workflow_git_blob_sha"): errors.append("WORKFLOW_BLOB_MISMATCH")

    for key in (
        "planner","agent","prestart_guard","transport","start_cas",
        "start_intent_builder","finalizer","preflight","behavior","invariant_registry"
    ):
        _verify_binding(surface,key,errors)

    activation_path=C/ACTIVATION
    activation_present=activation_path.is_file()
    if args.require_activation:
        if surface.get("execution_authority") is not True: errors.append("EXECUTION_AUTHORITY_NOT_ACTIVE")
        if surface.get("task_read_authority") is not False: errors.append("TASK_READ_AUTHORITY_MUST_REMAIN_GUARD_SCOPED")
        for key in ("authority","ledger","epoch","execution_claim"):
            _verify_binding(surface,key,errors)
        if not activation_present:
            errors.append("ACTIVATION_FILE_MISSING")
        else:
            try:
                arm=load(activation_path)
                if arm.get("schema")!="PROJECT_BRAIN_TB_SCIENCE_RANK15_ACTIVATION_V3": errors.append("ACTIVATION_SCHEMA_INVALID")
                if arm.get("activate") is not True: errors.append("ACTIVATION_FLAG_NOT_TRUE")
                if arm.get("slot_id")!=SLOT or arm.get("task_digest")!=DIGEST: errors.append("ACTIVATION_SLOT_IDENTITY_MISMATCH")
                for field,key in (
                    ("public_authority_binding_blob","authority"),
                    ("epoch_git_blob_sha","epoch"),
                    ("execution_claim_git_blob_sha","execution_claim"),
                ):
                    expected=(surface.get(key) or {}).get("git_blob_sha")
                    if arm.get(field)!=expected: errors.append("ACTIVATION_BINDING_MISMATCH:"+field)
                if arm.get("attempts_authorized")!=1 or arm.get("retries_authorized")!=0:
                    errors.append("ACTIVATION_ATTEMPT_POLICY_INVALID")
                if os.environ.get("GITHUB_RUN_ATTEMPT")!="1": errors.append("GITHUB_RUN_ATTEMPT_NOT_ONE")
                if os.environ.get("GITHUB_EVENT_NAME")!="pull_request": errors.append("GITHUB_EVENT_NOT_PULL_REQUEST")
                if os.environ.get("GITHUB_BASE_REF")!=BASE: errors.append("GITHUB_BASE_REF_MISMATCH")
                if os.environ.get("GITHUB_HEAD_REF")!=BRANCH: errors.append("GITHUB_HEAD_REF_MISMATCH")
            except Exception as exc:
                errors.append("ACTIVATION_CHECK:"+type(exc).__name__+":"+str(exc))
    elif activation_present:
        errors.append("UNEXPECTED_ACTIVATION_FILE_DURING_STAGING")

    out={
        "schema":SCHEMA,
        "status":"PASS__RANK15_V3_EXECUTION_PREFLIGHT__ZERO_TASK_EXPOSURE" if not errors else "FAIL_CLOSED",
        "pass":not errors,
        "require_activation":args.require_activation,
        "activation_present":activation_present,
        "execution_authority":surface.get("execution_authority"),
        "errors":sorted(set(errors)),
        "task_read":False,
        "task_started":False,
        "benchmark_trials_consumed":0,
        "acceptance_credit_delta":0,
        "terminal_credit_delta":0,
    }
    (ROOT/"RANK15_EXECUTION_PREFLIGHT.json").write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps(out,sort_keys=True))
    return 0 if not errors else 1

if __name__=="__main__":
    raise SystemExit(main())
