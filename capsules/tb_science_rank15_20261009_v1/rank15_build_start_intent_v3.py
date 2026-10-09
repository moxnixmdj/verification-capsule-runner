from __future__ import annotations
import hashlib, json, os, re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
C=Path(__file__).resolve().parent
SLOT="terminal-bench-science/protein-active-learning::trial-0"
DIGEST="sha256:d7e16b7c468551b468364cf2a86dba2383b007f3f2f01c6d2ce01d99ff30d48f"
ACTIVATION="ACTIVATE_RANK15_V3_PR.json"

def _load(path: Path) -> dict:
    value=json.loads(path.read_text())
    if not isinstance(value,dict): raise RuntimeError("JSON_OBJECT_REQUIRED:"+str(path))
    return value

def _git_blob(path: Path) -> str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def main() -> int:
    guard=_load(ROOT/"RANK15_PRESTART_GUARD.json")
    surface=_load(ROOT/"execution_guard/CURRENT_TERMINAL_EXECUTION_SURFACE_V1.json")
    activation_path=C/ACTIVATION
    activation=_load(activation_path)

    if guard.get("pass") is not True or guard.get("task_read") is not True:
        raise RuntimeError("PRESTART_GUARD_NOT_PASS__NO_START_INTENT")
    if surface.get("execution_authority") is not True:
        raise RuntimeError("EXECUTION_AUTHORITY_NOT_ACTIVE__NO_START_INTENT")
    if surface.get("slot_id")!=SLOT or surface.get("task_digest")!=DIGEST:
        raise RuntimeError("SURFACE_SLOT_IDENTITY_MISMATCH")
    if activation.get("activate") is not True or activation.get("slot_id")!=SLOT or activation.get("task_digest")!=DIGEST:
        raise RuntimeError("ACTIVATION_IDENTITY_MISMATCH")

    logical=str(guard.get("logical_attempt_id") or "")
    if not re.fullmatch(r"[0-9a-f]{64}",logical):
        raise RuntimeError("LOGICAL_ATTEMPT_ID_INVALID")

    runtime_identity={
        "workflow":surface.get("workflow_git_blob_sha"),
        "planner":surface.get("planner"),
        "agent":surface.get("agent"),
        "prestart_guard":surface.get("prestart_guard"),
        "start_cas":surface.get("start_cas"),
        "transport":surface.get("transport"),
        "behavior":surface.get("behavior"),
        "invariant_registry":surface.get("invariant_registry"),
    }
    runtime_sha=hashlib.sha256(json.dumps(runtime_identity,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    prestart_sha=hashlib.sha256((ROOT/"RANK15_PRESTART_GUARD.json").read_bytes()).hexdigest()
    workflow_blob=str(surface.get("workflow_git_blob_sha") or "")
    authority_blob=str((surface.get("authority") or {}).get("git_blob_sha") or "")
    activation_blob=_git_blob(activation_path)
    github_sha=str(os.environ.get("GITHUB_SHA") or "")
    run_id=str(os.environ.get("GITHUB_RUN_ID") or "")
    for name,value in [("workflow",workflow_blob),("authority",authority_blob),("activation",activation_blob),("github_sha",github_sha)]:
        if not re.fullmatch(r"[0-9a-f]{40}",value):
            raise RuntimeError(name.upper()+"_GIT_BLOB_INVALID")
    if not run_id:
        raise RuntimeError("GITHUB_RUN_ID_REQUIRED")

    intent={
        "slot_id":SLOT,
        "task_digest":DIGEST,
        "logical_attempt_id":logical,
        "workflow_git_blob_sha":workflow_blob,
        "authority_git_blob_sha":authority_blob,
        "activation_git_blob_sha":activation_blob,
        "runtime_identity_sha256":runtime_sha,
        "prestart_receipt_sha256":prestart_sha,
        "github_run_id":run_id,
        "github_sha":github_sha,
    }
    out=ROOT/"RANK15_START_INTENT_V3.json"
    out.write_text(json.dumps(intent,indent=2,sort_keys=True)+"\n")
    print(json.dumps(intent,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
