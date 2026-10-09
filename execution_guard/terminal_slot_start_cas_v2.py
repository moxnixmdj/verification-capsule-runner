#!/usr/bin/env python3
"""Barrier-aware durable terminal start commit.

This is a strict refinement of terminal_slot_start_cas_v1. It deliberately
reuses the same namespace and slot key so V1 and V2 records are mutually
exclusive globally. The additional binding proves that the agent reached its
pre-action READY barrier before irreversible start was committed.
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

SCHEMA = "PROJECT_BRAIN_TERMINAL_SLOT_START_INTENT_V2"
NAMESPACE = v1.NAMESPACE
GitHubRefStore = v1.GitHubRefStore
request_factory = v1.request_factory


class StartAdmissionDenied(RuntimeError):
    pass


class AtomicStore(Protocol):
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


def reserve_start_once(store: AtomicStore, intent: StartIntent) -> dict[str, Any]:
    intent.validate()
    key = slot_start_key(intent.slot_id, intent.task_digest)
    record = {
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
    try:
        created = store.create(key, record)
    except Exception as exc:
        raise StartAdmissionDenied("START_COMMIT_UNCONFIRMED__NO_AGENT_RELEASE") from exc
    if created is not True:
        try:
            existing = store.read(key)
        except Exception as exc:
            raise StartAdmissionDenied(
                "START_ALREADY_COMMITTED_OR_READ_UNCONFIRMED__NO_AGENT_RELEASE"
            ) from exc
        existing_run = existing.get("github_run_id") if isinstance(existing, dict) else None
        raise StartAdmissionDenied(
            "START_ALREADY_COMMITTED__NO_SECOND_AGENT_RELEASE"
            + (":" + str(existing_run) if existing_run else "")
        )
    try:
        persisted = store.read(key)
    except Exception as exc:
        raise StartAdmissionDenied("START_POSTWRITE_READ_UNCONFIRMED__NO_AGENT_RELEASE") from exc
    if not isinstance(persisted, dict):
        raise StartAdmissionDenied("START_POSTWRITE_RECORD_MISSING__NO_AGENT_RELEASE")
    for field, expected in record.items():
        if persisted.get(field) != expected:
            raise StartAdmissionDenied(
                "START_POSTWRITE_BINDING_MISMATCH__NO_AGENT_RELEASE:" + field
            )
    return {
        "status": "AGENT_READY_BOUND_START_COMMITTED",
        "key": key,
        "slot_id": intent.slot_id,
        "task_digest": intent.task_digest,
        "logical_attempt_id": intent.logical_attempt_id,
        "agent_ready_receipt_sha256": intent.agent_ready_receipt_sha256,
        "task_started": True,
        "benchmark_trials_consumed": 1,
        "replay_authority": False,
        "replacement_carrier_authority": False,
        "durable_record": persisted,
    }


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

    intent = _load_intent(args.intent)
    repo = v1._nonempty(os.environ.get("GITHUB_REPOSITORY"), "github_repository")
    token = v1._nonempty(os.environ.get("GH_TOKEN"), "gh_token")
    github_sha = v1._nonempty(os.environ.get("GITHUB_SHA"), "github_sha")
    if github_sha != intent.github_sha:
        raise StartAdmissionDenied("GITHUB_SHA_INTENT_MISMATCH")

    req = v1.request_factory(token)
    status, commit, _headers = req("GET", f"/repos/{repo}/git/commits/{github_sha}")
    tree = (commit.get("tree") or {}).get("sha") if status == 200 and isinstance(commit, dict) else None
    if not v1._sha(tree, 40):
        raise StartAdmissionDenied("BASE_TREE_UNCONFIRMED__NO_AGENT_RELEASE")

    store = v1.GitHubRefStore(req, repo, github_sha, tree, NAMESPACE)
    receipt = reserve_start_once(store, intent)
    with open(args.receipt, "w", encoding="utf-8") as fh:
        json.dump(receipt, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
