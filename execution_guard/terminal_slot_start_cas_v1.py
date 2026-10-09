#!/usr/bin/env python3
"""Create-once durable task-start intent for an irreversible terminal slot.

This does not start Harbor. It is the global at-most-one boundary immediately
before terminal execution. A failed/uncertain reservation means NO START.
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from typing import Any, Protocol

from github_ref_store_live import GitHubRefStore

SCHEMA = "PROJECT_BRAIN_TERMINAL_SLOT_START_INTENT_V1"
NAMESPACE = "terminal-start-v1"


class StartAdmissionDenied(RuntimeError):
    pass


class AtomicStore(Protocol):
    def create(self, key: str, value: dict[str, Any]) -> bool: ...
    def read(self, key: str) -> dict[str, Any] | None: ...


def _sha(value: Any, n: int) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{%d}" % n, value) is not None


def _nonempty(value: Any, field: str, maximum: int = 4096) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError("INVALID_" + field.upper())
    return value.strip()


@dataclasses.dataclass(frozen=True)
class StartIntent:
    slot_id: str
    task_digest: str
    logical_attempt_id: str
    workflow_git_blob_sha: str
    authority_git_blob_sha: str
    activation_git_blob_sha: str
    runtime_identity_sha256: str
    prestart_receipt_sha256: str
    github_run_id: str
    github_sha: str

    def validate(self) -> None:
        _nonempty(self.slot_id, "slot_id")
        if not isinstance(self.task_digest, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", self.task_digest):
            raise ValueError("INVALID_TASK_DIGEST")
        for field in (
            "logical_attempt_id",
            "runtime_identity_sha256",
            "prestart_receipt_sha256",
        ):
            if not _sha(getattr(self, field), 64):
                raise ValueError("INVALID_" + field.upper())
        for field in (
            "workflow_git_blob_sha",
            "authority_git_blob_sha",
            "activation_git_blob_sha",
            "github_sha",
        ):
            if not _sha(getattr(self, field), 40):
                raise ValueError("INVALID_" + field.upper())
        _nonempty(self.github_run_id, "github_run_id", 128)


def slot_start_key(slot_id: str, task_digest: str) -> str:
    slot = _nonempty(slot_id, "slot_id")
    if not isinstance(task_digest, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", task_digest):
        raise ValueError("INVALID_TASK_DIGEST")
    material = json.dumps(
        {"slot_id": slot, "task_digest": task_digest},
        sort_keys=True,
        separators=(",", ":"),
    )
    return "terminal-start/" + hashlib.sha256(material.encode()).hexdigest()


def reserve_start_once(store: AtomicStore, intent: StartIntent) -> dict[str, Any]:
    intent.validate()
    key = slot_start_key(intent.slot_id, intent.task_digest)
    record = {
        "schema": SCHEMA,
        "state": "TASK_START_INTENT_COMMITTED__NO_RETRY_IF_START_OUTCOME_UNCERTAIN",
        "slot_id": intent.slot_id,
        "task_digest": intent.task_digest,
        "logical_attempt_id": intent.logical_attempt_id,
        "workflow_git_blob_sha": intent.workflow_git_blob_sha,
        "authority_git_blob_sha": intent.authority_git_blob_sha,
        "activation_git_blob_sha": intent.activation_git_blob_sha,
        "runtime_identity_sha256": intent.runtime_identity_sha256,
        "prestart_receipt_sha256": intent.prestart_receipt_sha256,
        "github_run_id": intent.github_run_id,
        "github_sha": intent.github_sha,
        "replay_authority": False,
        "replacement_carrier_authority": False,
    }
    try:
        created = store.create(key, record)
    except Exception as exc:
        raise StartAdmissionDenied("START_RESERVATION_UNCONFIRMED__NO_START") from exc
    if created is not True:
        try:
            existing = store.read(key)
        except Exception as exc:
            raise StartAdmissionDenied("START_ALREADY_RESERVED_OR_READ_UNCONFIRMED__NO_START") from exc
        existing_run = existing.get("github_run_id") if isinstance(existing, dict) else None
        raise StartAdmissionDenied(
            "START_ALREADY_RESERVED__NO_SECOND_START"
            + (":" + str(existing_run) if existing_run else "")
        )
    return {
        "status": "TASK_START_INTENT_COMMITTED",
        "key": key,
        "slot_id": intent.slot_id,
        "task_digest": intent.task_digest,
        "logical_attempt_id": intent.logical_attempt_id,
        "github_run_id": intent.github_run_id,
        "replay_authority": False,
        "replacement_carrier_authority": False,
    }


def request_factory(token: str, api: str = "https://api.github.com"):
    token = _nonempty(token, "token")
    def req(method: str, path: str, payload: dict[str, Any] | None = None):
        data = None if payload is None else json.dumps(payload, separators=(",", ":")).encode()
        request = urllib.request.Request(
            api + path,
            data=data,
            method=method,
            headers={
                "Authorization": "Bearer " + token,
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "project-brain-terminal-start-cas-v1",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                raw = response.read()
                return response.status, (json.loads(raw) if raw else {}), dict(response.headers.items())
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            try:
                body = json.loads(raw) if raw else {}
            except Exception:
                body = {"message": "non-json HTTP error"}
            return exc.code, body, dict(exc.headers.items())
    return req


def _load_intent(path: str) -> StartIntent:
    value = json.loads(open(path, "r", encoding="utf-8").read())
    if not isinstance(value, dict):
        raise ValueError("INTENT_OBJECT_REQUIRED")
    intent = StartIntent(**value)
    intent.validate()
    return intent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--intent", required=True)
    ap.add_argument("--receipt", default="TERMINAL_SLOT_START_CAS_RECEIPT.json")
    args = ap.parse_args()

    intent = _load_intent(args.intent)
    repo = _nonempty(os.environ.get("GITHUB_REPOSITORY"), "github_repository")
    token = _nonempty(os.environ.get("GH_TOKEN"), "gh_token")
    github_sha = _nonempty(os.environ.get("GITHUB_SHA"), "github_sha")
    if github_sha != intent.github_sha:
        raise StartAdmissionDenied("GITHUB_SHA_INTENT_MISMATCH")

    req = request_factory(token)
    status, commit, _headers = req("GET", f"/repos/{repo}/git/commits/{github_sha}")
    tree = (commit.get("tree") or {}).get("sha") if status == 200 and isinstance(commit, dict) else None
    if not _sha(tree, 40):
        raise StartAdmissionDenied("BASE_TREE_UNCONFIRMED__NO_START")

    store = GitHubRefStore(req, repo, github_sha, tree, NAMESPACE)
    receipt = reserve_start_once(store, intent)
    with open(args.receipt, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
