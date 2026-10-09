#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

SCHEMA = "PROJECT_BRAIN_TB_SCIENCE_RANK15_START_CAS_V3"
SLOT_ID = "terminal-bench-science/protein-active-learning::trial-0"
TASK_DIGEST = "sha256:d7e16b7c468551b468364cf2a86dba2383b007f3f2f01c6d2ce01d99ff30d48f"
EXPECTED_REPOSITORY = "moxnixmdj/verification-capsule-runner"
EXPECTED_BASE = "terminal-execution-v1"
EXPECTED_HEAD = "execute/tb-science-rank15-20261009-v3"
LOCK_REF = "refs/tags/project-brain-start-locks/tb-science-rank15-protein-active-learning-trial-0-v3"
ACTIVATION_REL = "capsules/tb_science_rank15_20261009_v1/ACTIVATE_RANK15_V3_PR.json"
SURFACE_REL = "execution_guard/CURRENT_TERMINAL_EXECUTION_SURFACE_V1.json"
PREFLIGHT_RECEIPT = "RANK15_PRESTART_GUARD.json"
CHECK_RECEIPT = "RANK15_START_CAS_CHECK_V3.json"
ACQUIRE_RECEIPT = "RANK15_START_CAS_V3.json"


class StartCASError(RuntimeError):
    pass


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise StartCASError("JSON_OBJECT_REQUIRED:" + str(path))
    return value


def _write_output(name: str, value: str) -> None:
    target = os.environ.get("GITHUB_OUTPUT")
    if target:
        with open(target, "a", encoding="utf-8") as fh:
            fh.write(f"{name}={value}\n")


def _api(method: str, path: str, payload: dict[str, Any] | None = None) -> tuple[int, Any]:
    repo = os.environ.get("GITHUB_REPOSITORY") or ""
    if repo != EXPECTED_REPOSITORY:
        raise StartCASError("GITHUB_REPOSITORY_MISMATCH")
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
    url = "https://api.github.com/repos/" + repo + path
    body = None if payload is None else json.dumps(payload, separators=(",", ":")).encode("utf-8")
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "project-brain-rank15-start-cas-v3",
    }
    if token:
        headers["Authorization"] = "Bearer " + token
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read(1_000_000)
            value = json.loads(raw.decode("utf-8")) if raw else None
            return int(getattr(response, "status", 200)), value
    except urllib.error.HTTPError as exc:
        raw = exc.read(1_000_000)
        try:
            value = json.loads(raw.decode("utf-8")) if raw else None
        except Exception:
            value = {"raw": raw.decode("utf-8", "replace")[:2000]}
        return int(exc.code), value


def _event_context(root: Path) -> dict[str, Any]:
    if os.environ.get("GITHUB_EVENT_NAME") != "pull_request":
        raise StartCASError("PULL_REQUEST_EVENT_REQUIRED")
    if os.environ.get("GITHUB_RUN_ATTEMPT") != "1":
        raise StartCASError("FIRST_RUN_ATTEMPT_REQUIRED")
    if os.environ.get("GITHUB_BASE_REF") != EXPECTED_BASE:
        raise StartCASError("BASE_REF_MISMATCH")
    if os.environ.get("GITHUB_HEAD_REF") != EXPECTED_HEAD:
        raise StartCASError("HEAD_REF_MISMATCH")
    if os.environ.get("GITHUB_REPOSITORY") != EXPECTED_REPOSITORY:
        raise StartCASError("REPOSITORY_MISMATCH")
    event_path = Path(os.environ.get("GITHUB_EVENT_PATH") or "")
    if not event_path.is_file():
        raise StartCASError("GITHUB_EVENT_PATH_REQUIRED")
    event = _read_json(event_path)
    pr = event.get("pull_request")
    if not isinstance(pr, dict):
        raise StartCASError("PULL_REQUEST_OBJECT_REQUIRED")
    head = pr.get("head")
    base = pr.get("base")
    if not isinstance(head, dict) or not isinstance(base, dict):
        raise StartCASError("PULL_REQUEST_REFS_REQUIRED")
    head_repo = head.get("repo")
    if not isinstance(head_repo, dict) or head_repo.get("full_name") != EXPECTED_REPOSITORY:
        raise StartCASError("SAME_REPOSITORY_HEAD_REQUIRED")
    if head.get("ref") != EXPECTED_HEAD or base.get("ref") != EXPECTED_BASE:
        raise StartCASError("EVENT_REF_MISMATCH")
    activation = _read_json(root / ACTIVATION_REL)
    if activation.get("schema") != "PROJECT_BRAIN_TB_SCIENCE_RANK15_ACTIVATION_V3":
        raise StartCASError("ACTIVATION_SCHEMA_INVALID")
    if activation.get("activate") is not True:
        raise StartCASError("ACTIVATION_NOT_ARMED")
    if activation.get("slot_id") != SLOT_ID or activation.get("task_digest") != TASK_DIGEST:
        raise StartCASError("ACTIVATION_SLOT_OR_DIGEST_MISMATCH")
    surface = _read_json(root / SURFACE_REL)
    if surface.get("execution_authority") is not True:
        raise StartCASError("EXECUTION_AUTHORITY_NOT_ACTIVE")
    if surface.get("task_started") is not False:
        raise StartCASError("SURFACE_TASK_ALREADY_STARTED")
    if surface.get("slot_id") != SLOT_ID or surface.get("task_digest") != TASK_DIGEST:
        raise StartCASError("SURFACE_SLOT_OR_DIGEST_MISMATCH")
    return {"event": event, "activation": activation, "surface": surface}


def _lock_api_path() -> str:
    short = LOCK_REF.removeprefix("refs/")
    return "/git/ref/" + urllib.parse.quote(short, safe="/")


def _lock_absent() -> tuple[bool, int, Any]:
    status, body = _api("GET", _lock_api_path())
    if status == 404:
        return True, status, body
    if status == 200:
        return False, status, body
    raise StartCASError("LOCK_LOOKUP_HTTP_STATUS:" + str(status))


def _result(mode: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "mode": mode,
        "slot_id": SLOT_ID,
        "task_digest": TASK_DIGEST,
        "lock_ref": LOCK_REF,
        "pass": False,
        "lock_absent": False,
        "acquired": False,
        "task_started": False,
        "benchmark_trials_consumed": 0,
        "acceptance_credit_delta": 0,
        "terminal_credit_delta": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check-absent", action="store_true")
    group.add_argument("--acquire", action="store_true")
    args = parser.parse_args()

    mode = "check-absent" if args.check_absent else "acquire"
    result = _result(mode)
    root = Path(os.environ.get("GITHUB_WORKSPACE") or ".").resolve()
    output = root / (CHECK_RECEIPT if args.check_absent else ACQUIRE_RECEIPT)
    rc = 1
    try:
        _event_context(root)
        absent, status, body = _lock_absent()
        result["lookup_status"] = status
        result["lock_absent"] = absent
        if args.check_absent:
            result["pass"] = absent
            result["status"] = "PASS__START_CAS_ABSENT__NO_TASK_START" if absent else "FAIL_CLOSED__START_CAS_ALREADY_EXISTS"
            rc = 0 if absent else 1
        else:
            if not absent:
                result["status"] = "FAIL_CLOSED__START_CAS_ALREADY_EXISTS"
            else:
                guard = _read_json(root / PREFLIGHT_RECEIPT)
                if (
                    guard.get("pass") is not True
                    or guard.get("task_read") is not True
                    or guard.get("task_started") is not False
                    or guard.get("task_digest") != TASK_DIGEST
                    or not str(guard.get("status") or "").startswith("PASS__RANK15_V3_")
                ):
                    raise StartCASError("PRESTART_GUARD_NOT_AUTHORIZED")
                sha = os.environ.get("GITHUB_SHA") or ""
                if len(sha) != 40 or any(ch not in "0123456789abcdef" for ch in sha.lower()):
                    raise StartCASError("GITHUB_SHA_INVALID")
                status, body = _api("POST", "/git/refs", {"ref": LOCK_REF, "sha": sha})
                result["create_status"] = status
                if status == 201:
                    result.update({
                        "pass": True,
                        "acquired": True,
                        "task_started": True,
                        "benchmark_trials_consumed": 1,
                        "status": "PASS__DURABLE_START_CAS_ACQUIRED__IRREVERSIBLE_SLOT_START",
                        "lock_commit_sha": sha,
                    })
                    rc = 0
                elif status == 422:
                    result["status"] = "FAIL_CLOSED__START_CAS_RACE_LOST_OR_ALREADY_EXISTS"
                else:
                    raise StartCASError("LOCK_CREATE_HTTP_STATUS:" + str(status))
    except Exception as exc:
        result["status"] = "FAIL_CLOSED__START_CAS_ERROR"
        result["error_type"] = type(exc).__name__
        result["error"] = str(exc)

    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_output("lock_absent", "true" if result.get("lock_absent") else "false")
    _write_output("acquired", "true" if result.get("acquired") else "false")
    _write_output("receipt", str(output))
    print(json.dumps(result, sort_keys=True))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
