#!/usr/bin/env python3
from __future__ import annotations
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import subprocess
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
DIAG = ROOT / "diagnose_livebench_replay72_v7_sanitized.py"
VERIFIER = ROOT / "verify_livebench_v7_sanitized_diagnostic.py"

EXPECTED_DIAG_BLOB = "55d4b961f58dc45c1513f9c9282a63773444773d"
EXPECTED_VERIFIER_BLOB = "0c63704ba4e462c957516bc0f1ee0bdbdea8465c"
EPOCH_DIGEST = "5ea710ae6d8b64c9ae990da5bd3ae747806e12843b8c2566bbb1be83d09ab53d"
CLAIM_REF = "refs/heads/livebench-v7-claims/" + EPOCH_DIGEST
REPO = "moxnixmdj/verification-capsule-runner"
HEX40 = re.compile(r"^[0-9a-f]{40}$")

class LauncherError(RuntimeError):
    pass

def git_blob_sha(path: pathlib.Path) -> str:
    b = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()

def verify_exact_subjects() -> None:
    if git_blob_sha(DIAG) != EXPECTED_DIAG_BLOB:
        raise LauncherError("DIAGNOSTIC_BLOB_DRIFT")
    if git_blob_sha(VERIFIER) != EXPECTED_VERIFIER_BLOB:
        raise LauncherError("POINT_OF_USE_VERIFIER_BLOB_DRIFT")

def run_point_of_use_zero_case_verifier() -> None:
    cp = subprocess.run([sys.executable, str(VERIFIER)], cwd=ROOT, text=True)
    if cp.returncode != 0:
        raise LauncherError("POINT_OF_USE_ZERO_CASE_VERIFIER_FAILED")

def create_atomic_claim(token: str, commit_sha: str) -> dict:
    if not token:
        raise LauncherError("GITHUB_TOKEN_REQUIRED")
    if not HEX40.fullmatch(commit_sha or ""):
        raise LauncherError("GITHUB_SHA_INVALID")
    url = f"https://api.github.com/repos/{REPO}/git/refs"
    body = json.dumps({"ref": CLAIM_REF, "sha": commit_sha}).encode()
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            status = int(resp.status)
            payload = json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as exc:
        status = int(exc.code)
        payload = json.loads(exc.read().decode() or "{}")
    if status != 201:
        raise LauncherError("ATOMIC_CLAIM_CREATE_NON_201:" + str(status))
    if payload.get("ref") != CLAIM_REF:
        raise LauncherError("ATOMIC_CLAIM_RESPONSE_REF_MISMATCH")
    return {"status": status, "ref": payload.get("ref"), "object_sha": ((payload.get("object") or {}).get("sha"))}

def run_sanitized_replay(activation_blob: str) -> int:
    if not HEX40.fullmatch(activation_blob or ""):
        raise LauncherError("ACTIVATION_BLOB_INVALID")
    spec = importlib.util.spec_from_file_location("livebench_v7_diag", DIAG)
    if spec is None or spec.loader is None:
        raise LauncherError("DIAGNOSTIC_IMPORT_FAILED")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return int(mod.main(authorized=True, activation_blob=activation_blob))

def execute(*, token: str, commit_sha: str, activation_blob: str) -> dict:
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise LauncherError("PUBLIC_GITHUB_ACTIONS_REQUIRED")
    if str(os.environ.get("REPOSITORY_PRIVATE", "")).lower() != "false":
        raise LauncherError("PUBLIC_REPOSITORY_REQUIRED")
    verify_exact_subjects()
    run_point_of_use_zero_case_verifier()
    claim = create_atomic_claim(token, commit_sha)
    replay_rc = run_sanitized_replay(activation_blob)
    if replay_rc != 0:
        raise LauncherError("SANITIZED_REPLAY_NONZERO")
    return {
        "schema": "PROJECT_BRAIN_LIVEBENCH_V7_ATOMIC_LAUNCH_RESULT_V1",
        "status": "PASS__ATOMIC_CLAIM_CREATED__REPLAY72_COMPLETE",
        "claim_ref": CLAIM_REF,
        "claim_create_http_status": claim["status"],
        "activation_blob_sha": activation_blob,
        "replay_prefix_limit": 72,
        "new_case_exposure": False,
        "acceptance_credit_delta": 0,
    }

def main() -> int:
    out = execute(
        token=os.environ.get("GITHUB_TOKEN", ""),
        commit_sha=os.environ.get("GITHUB_SHA", ""),
        activation_blob=os.environ.get("LIVEBENCH_V7_ACTIVATION_BLOB", ""),
    )
    print("LIVEBENCH_V7_ATOMIC_LAUNCH=" + json.dumps(out, sort_keys=True), flush=True)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
