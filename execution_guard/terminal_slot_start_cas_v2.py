#!/usr/bin/env python3
"""Barrier-aware durable terminal start commit over GitHub commit statuses.

The persistent backend is a manifest-last commit-status object store. It is not
a multi-writer CAS by itself: correctness requires the exact terminal workflow
to serialize all candidate writers through one fixed GitHub Actions concurrency
group. Under that proved single-writer premise, durable existence + exact
readback gives create-once terminal-start semantics.

This module preserves the V1 logical slot key so higher layers can prove legacy
V1-ref absence during backend migration before admitting the status-backed V2
record.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys
from pathlib import Path
from typing import Any, Protocol

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import terminal_slot_start_cas_v1 as v1
from github_status_object_store_v1 import SerializedStatusObjectStore

SCHEMA = "PROJECT_BRAIN_TERMINAL_SLOT_START_INTENT_V2"
NAMESPACE = v1.NAMESPACE
STATUS_BACKEND_SCHEMA = "PROJECT_BRAIN_GITHUB_STATUS_OBJECT_STORE_V1"
request_factory = v1.request_factory


class StartAdmissionDenied(RuntimeError):
    pass


class SerializedStore(Protocol):
    def create(self, key: str, value: dict[str, Any]) -> bool: ...
    def read(self, key: str) -> dict[str, Any] | None: ...


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
    agent_ready_receipt_sha256: str
    github_run_id: str
    github_sha: str

    def validate(self) -> None:
        base = v1.StartIntent(
            slot_id=self.slot_id,
            task_digest=self.task_digest,
            logical_attempt_id=self.logical_attempt_id,
            workflow_git_blob_sha=self.workflow_git_blob_sha,
            authority_git_blob_sha=self.authority_git_blob_sha,
            activation_git_blob_sha=self.activation_git_blob_sha,
            runtime_identity_sha256=self.runtime_identity_sha256,
            prestart_receipt_sha256=self.prestart_receipt_sha256,
            github_run_id=self.github_run_id,
            github_sha=self.github_sha,
        )
        base.validate()
        if not v1._sha(self.agent_ready_receipt_sha256, 64):
            raise ValueError("INVALID_AGENT_READY_RECEIPT_SHA256")


def slot_start_key(slot_id: str, task_digest: str) -> str:
    return v1.slot_start_key(slot_id, task_digest)


def _record(intent: StartIntent) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "state": "AGENT_READY_BOUND_START_COMMITTED__NO_RETRY_IF_RELEASE_OUTCOME_UNCERTAIN",
        "slot_id": intent.slot_id,
        "task_digest": intent.task_digest,
        "logical_attempt_id": intent.logical_attempt_id,
        "workflow_git_blob_sha": intent.workflow_git_blob_sha,
        "authority_git_blob_sha": intent.authority_git_blob_sha,
        "activation_git_blob_sha": intent.activation_git_blob_sha,
        "runtime_identity_sha256": intent.runtime_identity_sha256,
        "prestart_receipt_sha256": intent.prestart_receipt_sha256,
        "agent_ready_receipt_sha256": intent.agent_ready_receipt_sha256,
        "github_run_id": intent.github_run_id,
        "github_sha": intent.github_sha,
        "task_started": True,
        "benchmark_trials_consumed": 1,
        "replay_authority": False,
        "replacement_carrier_authority": False,
    }


def _record_matches(record: Any, expected: dict[str, Any]) -> bool:
    return (
        isinstance(record, dict)
        and json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False)
        == json.dumps(expected, sort_keys=True, separators=(",", ":"), allow_nan=False)
    )


def _success(
    *,
    key: str,
    intent: StartIntent,
    persisted: dict[str, Any],
    status: str,
) -> dict[str, Any]:
    return {
        "status": status,
        "key": key,
        "slot_id": intent.slot_id,
        "task_digest": intent.task_digest,
        "logical_attempt_id": intent.logical_attempt_id,
        "agent_ready_receipt_sha256": intent.agent_ready_receipt_sha256,
        "task_started": True,
        "benchmark_trials_consumed": 1,
        "replay_authority": False,
        "replacement_carrier_authority": False,
        "durable_backend_schema": STATUS_BACKEND_SCHEMA,
        "durable_record": persisted,
    }


def reserve_start_once(store: SerializedStore, intent: StartIntent) -> dict[str, Any]:
    """Commit exactly one start under an externally proved single-writer premise."""
    intent.validate()
    key = slot_start_key(intent.slot_id, intent.task_digest)
    record = _record(intent)

    try:
        created = store.create(key, record)
    except Exception as create_exc:
        # A transport failure may happen after the manifest status was accepted.
        # Reconcile durable truth before deciding whether the blocked agent may run.
        try:
            existing = store.read(key)
        except Exception as read_exc:
            raise StartAdmissionDenied(
                "START_COMMIT_OUTCOME_UNCONFIRMED__NO_AGENT_RELEASE"
            ) from read_exc
        if existing is None:
            raise StartAdmissionDenied(
                "START_COMMIT_CONFIRMED_ABSENT__NO_AGENT_RELEASE"
            ) from create_exc
        if not _record_matches(existing, record):
            raise StartAdmissionDenied(
                "START_COMMIT_CONFLICT_AFTER_CREATE_ERROR__NO_AGENT_RELEASE"
            ) from create_exc
        return _success(
            key=key,
            intent=intent,
            persisted=existing,
            status="AGENT_READY_BOUND_START_COMMITTED_RECONCILED_AFTER_CREATE_ERROR",
        )

    if created is not True:
        try:
            existing = store.read(key)
        except Exception as exc:
            raise StartAdmissionDenied(
                "START_ALREADY_COMMITTED_OR_READ_UNCONFIRMED__NO_AGENT_RELEASE"
            ) from exc
        if _record_matches(existing, record):
            return _success(
                key=key,
                intent=intent,
                persisted=existing,
                status="AGENT_READY_BOUND_START_COMMITTED_IDEMPOTENT",
            )
        existing_run = existing.get("github_run_id") if isinstance(existing, dict) else None
        raise StartAdmissionDenied(
            "START_ALREADY_COMMITTED__NO_SECOND_AGENT_RELEASE"
            + (":" + str(existing_run) if existing_run else "")
        )

    try:
        persisted = store.read(key)
    except Exception as exc:
        raise StartAdmissionDenied(
            "START_POSTWRITE_READ_UNCONFIRMED__NO_AGENT_RELEASE"
        ) from exc
    if not _record_matches(persisted, record):
        if persisted is None:
            raise StartAdmissionDenied(
                "START_POSTWRITE_RECORD_MISSING__NO_AGENT_RELEASE"
            )
        raise StartAdmissionDenied(
            "START_POSTWRITE_BINDING_MISMATCH__NO_AGENT_RELEASE"
        )
    return _success(
        key=key,
        intent=intent,
        persisted=persisted,
        status="AGENT_READY_BOUND_START_COMMITTED",
    )


def open_status_store(
    *,
    token: str,
    repo: str,
    commit_sha: str,
    namespace: str = NAMESPACE,
) -> SerializedStatusObjectStore:
    token = v1._nonempty(token, "gh_token")
    repo = v1._nonempty(repo, "github_repository")
    if not v1._sha(commit_sha, 40):
        raise StartAdmissionDenied("GITHUB_SHA_INVALID")
    req = v1.request_factory(token)
    status, _commit, _headers = req("GET", f"/repos/{repo}/git/commits/{commit_sha}")
    if status != 200:
        raise StartAdmissionDenied("BOUND_COMMIT_UNCONFIRMED__NO_AGENT_RELEASE")
    return SerializedStatusObjectStore(req, repo, commit_sha, namespace)


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
    ap.add_argument("--receipt", default="TERMINAL_SLOT_START_CAS_V2_RECEIPT.json")
    args = ap.parse_args()

    if os.environ.get("BRAIN_TERMINAL_SINGLE_WRITER_SERIALIZED") != "1":
        raise StartAdmissionDenied(
            "SINGLE_WRITER_SERIALIZATION_NOT_ASSERTED__NO_AGENT_RELEASE"
        )

    intent = _load_intent(args.intent)
    repo = v1._nonempty(os.environ.get("GITHUB_REPOSITORY"), "github_repository")
    token = v1._nonempty(os.environ.get("GH_TOKEN"), "gh_token")
    github_sha = v1._nonempty(os.environ.get("GITHUB_SHA"), "github_sha")
    if github_sha != intent.github_sha:
        raise StartAdmissionDenied("GITHUB_SHA_INTENT_MISMATCH")

    store = open_status_store(token=token, repo=repo, commit_sha=github_sha)
    receipt = reserve_start_once(store, intent)
    with open(args.receipt, "w", encoding="utf-8") as fh:
        json.dump(receipt, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
