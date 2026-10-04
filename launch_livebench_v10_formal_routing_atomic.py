#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import urllib.error
import urllib.request

EPOCH_DIGEST = "a71f24f79df6b6be6e910efb1299776ac9fede9e78539577695d6e386fc2eb52"
CLAIM_REF = "refs/heads/livebench-v10-claims/" + EPOCH_DIGEST
CANDIDATE_GIT_BLOB = "7d42814e46abda96eed0fb1929bef5a829bd2236"
WRAPPER_GIT_BLOB = "56ea114d59f0309bc14ef0504a44bec1f808e876"
ACTIVATION_FILENAME = "LIVEBENCH_V10_REPLAY72_ACTIVATION_V1.json"


def fail(msg):
    raise SystemExit("FAIL_CLOSED:" + msg)


def git_blob(path: pathlib.Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode() + b"\0" + raw
    ).hexdigest()


def verify_exact_activation() -> str:
    expected_blob = str(os.environ.get("LIVEBENCH_V10_ACTIVATION_BLOB") or "").strip()
    if re.fullmatch(r"[0-9a-f]{40}", expected_blob) is None:
        fail("EXACT_ACTIVATION_BLOB_NOT_BOUND")

    path = pathlib.Path(__file__).resolve().with_name(ACTIVATION_FILENAME)
    if not path.is_file():
        fail("EXACT_ACTIVATION_ARTIFACT_MISSING")

    observed_blob = git_blob(path)
    if observed_blob != expected_blob:
        fail("ACTIVATION_BLOB_DRIFT")

    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        fail("ACTIVATION_JSON_INVALID")

    if doc.get("schema") != "PROJECT_BRAIN_LIVEBENCH_V10_REPLAY72_ACTIVATION_V1":
        fail("ACTIVATION_SCHEMA_MISMATCH")
    if doc.get("target_predicate") != "LIVEBENCH_IF_GE_65_7":
        fail("ACTIVATION_TARGET_MISMATCH")
    if doc.get("epoch_digest_sha256") != EPOCH_DIGEST:
        fail("ACTIVATION_EPOCH_MISMATCH")
    if doc.get("candidate_git_blob_sha") != CANDIDATE_GIT_BLOB:
        fail("ACTIVATION_CANDIDATE_MISMATCH")
    if doc.get("wrapper_git_blob_sha") != WRAPPER_GIT_BLOB:
        fail("ACTIVATION_WRAPPER_MISMATCH")

    self_blob = git_blob(pathlib.Path(__file__).resolve())
    if doc.get("launcher_git_blob_sha") != self_blob:
        fail("ACTIVATION_LAUNCHER_MISMATCH")

    authority = doc.get("authority")
    if not isinstance(authority, dict):
        fail("ACTIVATION_AUTHORITY_MISSING")
    if authority.get("replay72") is not True:
        fail("ACTIVATION_REPLAY72_NOT_TRUE")
    for key in (
        "new_case_exposure",
        "fresh_reality",
        "promotion",
        "acceptance_credit",
    ):
        if authority.get(key) is not False:
            fail("ACTIVATION_FORBIDDEN_AUTHORITY:" + key)

    scope = doc.get("replay_scope")
    if not isinstance(scope, dict):
        fail("ACTIVATION_REPLAY_SCOPE_MISSING")
    if scope.get("already_exposed_prefix_only") is not True:
        fail("ACTIVATION_PREFIX_ONLY_REQUIRED")
    if scope.get("replay_prefix_limit") != 72:
        fail("ACTIVATION_REPLAY_LIMIT_MISMATCH")
    if scope.get("case_73_or_later") is not False:
        fail("ACTIVATION_CASE73_MUST_BE_FALSE")

    return observed_blob


def atomic_claim():
    api = os.environ.get("GITHUB_API_URL")
    repo = os.environ.get("GITHUB_REPOSITORY")
    sha = os.environ.get("GITHUB_SHA")
    token = os.environ.get("GH_TOKEN")
    if not all((api, repo, sha, token)) or os.environ.get("GITHUB_ACTIONS") != "true":
        fail("GITHUB_ATOMIC_CLAIM_ENV_MISSING")
    req = urllib.request.Request(
        f"{api}/repos/{repo}/git/refs",
        data=json.dumps({"ref": CLAIM_REF, "sha": sha}, separators=(",", ":")).encode(),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "project-brain-livebench-v10",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            status = resp.status
            body = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        if exc.code == 422:
            fail("ATOMIC_ONE_USE_CLAIM_ALREADY_EXISTS")
        fail("ATOMIC_ONE_USE_CLAIM_HTTP_" + str(exc.code))
    if status != 201:
        fail("ATOMIC_ONE_USE_CLAIM_NOT_201")
    if body.get("ref") != CLAIM_REF:
        fail("ATOMIC_ONE_USE_CLAIM_RESPONSE_REF_MISMATCH")
    objsha = (body.get("object") or {}).get("sha")
    if not isinstance(objsha, str) or re.fullmatch(r"[0-9a-f]{40}", objsha) is None:
        fail("ATOMIC_ONE_USE_CLAIM_RESPONSE_SHA_INVALID")
    print(
        "LIVEBENCH_V10_ATOMIC_CLAIM="
        + json.dumps(
            {
                "schema": "PROJECT_BRAIN_LIVEBENCH_V10_ATOMIC_ONE_USE_CLAIM_RECEIPT_V1",
                "epoch_digest_sha256": EPOCH_DIGEST,
                "claim_ref": CLAIM_REF,
                "create_http_status": 201,
                "reference_created": True,
                "response_ref": body.get("ref"),
                "response_object_sha": objsha,
                "terminal_dataset_read_before_claim": False,
                "execution_started_before_claim": False,
            },
            sort_keys=True,
        ),
        flush=True,
    )


def main():
    activation_blob = verify_exact_activation()
    atomic_claim()
    import diagnose_livebench_replay72_v10_formal_routing as diagnostic

    return int(diagnostic.main(authorized=True, activation_blob=activation_blob))


if __name__ == "__main__":
    raise SystemExit(main())
