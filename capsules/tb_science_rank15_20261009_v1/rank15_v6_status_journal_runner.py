#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
C = ROOT / "capsules/tb_science_rank15_20261009_v1"
EXECUTION_GUARD = ROOT / "execution_guard"
for value in (str(ROOT), str(C), str(EXECUTION_GUARD)):
    if value not in sys.path:
        sys.path.insert(0, value)

from execution_guard import terminal_agent_start_barrier_v1 as start_barrier
from execution_guard import terminal_causal_journal_filebridge_v1 as journal_bridge
from execution_guard.github_status_object_store_v1 import SerializedStatusObjectStore
from execution_guard import terminal_slot_start_cas_v1 as legacy_cas
from execution_guard.logical_attempt_identity_v1 import logical_attempt_id as canonical_logical_attempt_id

SCHEMA = "PROJECT_BRAIN_TB_SCIENCE_RANK15_V6_STATUS_JOURNAL_RUNNER"
SLOT_ID = "terminal-bench-science/protein-active-learning::trial-0"
TASK_DIGEST = "sha256:d7e16b7c468551b468364cf2a86dba2383b007f3f2f01c6d2ce01d99ff30d48f"
BARRIER_REL = Path("RANK15_AGENT_START_BARRIER")
READY_REL = BARRIER_REL / "AGENT_READY.json"
COMMIT_REL = BARRIER_REL / "START_COMMITTED.json"
JOURNAL_REL = Path("RANK15_CAUSAL_JOURNAL_BRIDGE")
JOURNAL_NAMESPACE = "terminal-journal-v1"
QUALIFY_NAMESPACE = "terminal-status-qualify-v1"
CAS_RECEIPT = ROOT / "RANK15_START_CAS_V6.json"
RUNNER_RECEIPT = ROOT / "RANK15_V6_STATUS_JOURNAL_RUNNER_RECEIPT.json"
HARBOR_LOG = ROOT / "RANK15_V6_HARBOR_RUN.log"
READY_TIMEOUT_S = 3600.0
POLL_S = 0.2


class BarrierRunnerError(RuntimeError):
    pass


def _write_receipt(value: dict[str, Any]) -> None:
    RUNNER_RECEIPT.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _child_env() -> dict[str, str]:
    env = dict(os.environ)
    env.pop("GH_TOKEN", None)
    env.pop("GITHUB_TOKEN", None)
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + str(C)
    env["BRAIN_AGENT_START_BARRIER_DIR"] = str(ROOT / BARRIER_REL)
    env["BRAIN_SLOT_ID"] = SLOT_ID
    env["BRAIN_TASK_DIGEST"] = TASK_DIGEST
    carried = str(os.environ.get("BRAIN_LOGICAL_ATTEMPT_ID") or "").strip()
    expected = canonical_logical_attempt_id(slot_id=SLOT_ID, task_digest=TASK_DIGEST)
    if carried != expected:
        raise BarrierRunnerError("LOGICAL_ATTEMPT_ID_NOT_CANONICAL")
    env["BRAIN_LOGICAL_ATTEMPT_ID"] = carried
    env["BRAIN_AGENT_START_BARRIER_TIMEOUT_S"] = str(int(READY_TIMEOUT_S))
    env["BRAIN_CAUSAL_JOURNAL_DIR"] = str(ROOT / JOURNAL_REL)
    return env


def _harbor_command() -> list[str]:
    task_path = os.environ.get("TASK_PATH")
    safe_id = os.environ.get("SAFE_ID") or "protein-active-learning-trial-0"
    if not isinstance(task_path, str) or not task_path.strip():
        raise BarrierRunnerError("TASK_PATH_REQUIRED")
    jobs = ROOT / "jobs" / safe_id
    jobs.mkdir(parents=True, exist_ok=True)
    return [
        "harbor",
        "run",
        "-p",
        task_path,
        "-a",
        "canonical.runtime.harbor_science_agent_v8:HarborScienceAgent",
        "-k",
        "1",
        "-n",
        "1",
        "-r",
        "0",
        "--agent-timeout-multiplier",
        "0.48",
        "--environment-build-timeout-multiplier",
        "1.0",
        "--verifier-timeout-multiplier",
        "1.0",
        "--job-name",
        safe_id,
        "--jobs-dir",
        str(jobs),
    ]


def _open_status_store(namespace: str) -> SerializedStatusObjectStore:
    repo = os.environ.get("GITHUB_REPOSITORY") or ""
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
    sha = os.environ.get("GITHUB_SHA") or ""
    if not repo or not token or len(sha) != 40:
        raise BarrierRunnerError("STATUS_STORE_ENVIRONMENT_INVALID")
    req = legacy_cas.request_factory(token)
    status, _body, _headers = req("GET", f"/repos/{repo}/git/commits/{sha}")
    if status != 200:
        raise BarrierRunnerError("STATUS_STORE_BOUND_COMMIT_UNCONFIRMED")
    return SerializedStatusObjectStore(req, repo, sha, namespace)


def _qualify_status_store() -> dict[str, Any]:
    store = _open_status_store(QUALIFY_NAMESPACE)
    run_id = os.environ.get("GITHUB_RUN_ID") or ""
    sha = os.environ.get("GITHUB_SHA") or ""
    if not run_id:
        raise BarrierRunnerError("GITHUB_RUN_ID_REQUIRED")
    key = "rank15-v5-prestart-qualify/" + run_id
    value = {
        "schema": "PROJECT_BRAIN_RANK15_V5_STATUS_STORE_QUALIFICATION_V1",
        "github_run_id": run_id,
        "github_sha": sha,
        "task_started": False,
        "benchmark_trials_consumed": 0,
    }
    created = store.create(key, value)
    persisted = store.read(key)
    if persisted != value:
        raise BarrierRunnerError("STATUS_STORE_QUALIFICATION_READBACK_MISMATCH")
    return {
        "created": bool(created),
        "key": key,
        "qualified": True,
    }


def _journal_store() -> SerializedStatusObjectStore:
    return _open_status_store(JOURNAL_NAMESPACE)


def _process_journal_pending(store: Any) -> int:
    return journal_bridge.process_pending_once(store, ROOT / JOURNAL_REL)


def _acquire_start_commit() -> None:
    proc = subprocess.run(
        [sys.executable, str(C / "rank15_start_cas_v6.py"), "--acquire"],
        cwd=ROOT,
        env=dict(os.environ),
        check=False,
    )
    if proc.returncode != 0:
        raise BarrierRunnerError("START_CAS_ACQUIRE_FAILED")


def _release_agent() -> None:
    start_barrier.release_from_cas(
        ready_path=ROOT / READY_REL,
        cas_receipt_path=CAS_RECEIPT,
        output_path=ROOT / COMMIT_REL,
    )


def _cas_acquired() -> bool:
    if not CAS_RECEIPT.is_file():
        return False
    try:
        value = json.loads(CAS_RECEIPT.read_text(encoding="utf-8"))
    except Exception:
        return False
    return (
        isinstance(value, dict)
        and value.get("acquired") is True
        and value.get("task_started") is True
    )


def _terminate(proc: Any) -> None:
    try:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except Exception:
                proc.kill()
                proc.wait(timeout=10)
    except Exception:
        pass


def run_once(
    *,
    popen_factory: Callable[..., Any] = subprocess.Popen,
    acquire_start: Callable[[], None] = _acquire_start_commit,
    release_agent: Callable[[], None] = _release_agent,
    qualify_status: Callable[[], dict[str, Any]] = _qualify_status_store,
    journal_store_factory: Callable[[], Any] = _journal_store,
    process_journal: Callable[[Any], int] = _process_journal_pending,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    barrier_dir = ROOT / BARRIER_REL
    barrier_dir.mkdir(parents=True, exist_ok=True)
    for path in (ROOT / READY_REL, ROOT / COMMIT_REL):
        if path.exists():
            path.unlink()

    receipt: dict[str, Any] = {
        "schema": SCHEMA,
        "slot_id": SLOT_ID,
        "task_digest": TASK_DIGEST,
        "status": "PRESTART",
        "harbor_launched": False,
        "agent_ready": False,
        "start_cas_acquired": False,
        "agent_released": False,
        "task_started": False,
        "benchmark_trials_consumed": 0,
        "github_credentials_exposed_to_harbor": False,
        "status_store_qualified": False,
        "journal_requests_committed": 0,
        "acceptance_credit_delta": 0,
        "terminal_credit_delta": 0,
    }

    proc = None
    log_handle = None
    try:
        qualification = qualify_status()
        if not isinstance(qualification, dict) or qualification.get("qualified") is not True:
            raise BarrierRunnerError("STATUS_STORE_QUALIFICATION_FAILED")
        receipt["status_store_qualified"] = True
        receipt["status_store_qualification"] = qualification
        journal_store = journal_store_factory()

        child_env = _child_env()
        if "GH_TOKEN" in child_env or "GITHUB_TOKEN" in child_env:
            raise BarrierRunnerError("CHILD_GITHUB_CREDENTIAL_STRIP_FAILED")
        log_handle = open(HARBOR_LOG, "wb")
        proc = popen_factory(
            _harbor_command(),
            cwd=ROOT,
            env=child_env,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
        )
        receipt["harbor_launched"] = True

        ready_path = ROOT / READY_REL
        deadline = monotonic() + READY_TIMEOUT_S
        while not ready_path.is_file():
            rc = proc.poll()
            if rc is not None:
                raise BarrierRunnerError(
                    "HARBOR_EXITED_BEFORE_AGENT_READY:" + str(rc)
                )
            if monotonic() >= deadline:
                raise BarrierRunnerError("AGENT_READY_TIMEOUT__NO_START_COMMIT")
            sleep(POLL_S)

        receipt["agent_ready"] = True
        acquire_start()
        receipt["start_cas_acquired"] = _cas_acquired()
        if not receipt["start_cas_acquired"]:
            raise BarrierRunnerError("START_CAS_RECEIPT_NOT_ACQUIRED")
        receipt["task_started"] = True
        receipt["benchmark_trials_consumed"] = 1

        release_agent()
        if not (ROOT / COMMIT_REL).is_file():
            raise BarrierRunnerError("START_COMMIT_RELEASE_FILE_MISSING")
        receipt["agent_released"] = True

        # Parent owns durable credentials and services journal requests while
        # the credential-free Harbor child runs. The child cannot cross an
        # effect boundary until its exact intent receives a durable ACK.
        while proc.poll() is None:
            receipt["journal_requests_committed"] += int(process_journal(journal_store))
            sleep(POLL_S)
        receipt["journal_requests_committed"] += int(process_journal(journal_store))
        rc = int(proc.wait())
        receipt["journal_request_files"] = len(list((ROOT / JOURNAL_REL).glob("request-*.json")))
        receipt["journal_ack_files"] = len(list((ROOT / JOURNAL_REL).glob("ack-*.json")))
        receipt["harbor_returncode"] = rc
        receipt["status"] = "HARBOR_COMPLETE" if rc == 0 else "POSTSTART_HARBOR_NONZERO"
        _write_receipt(receipt)
        return rc
    except Exception as exc:
        committed = bool(receipt.get("start_cas_acquired")) or _cas_acquired()
        if committed:
            receipt["start_cas_acquired"] = True
            receipt["task_started"] = True
            receipt["benchmark_trials_consumed"] = 1
            receipt["status"] = "POSTSTART_ABORT__IRREVERSIBLE"
        else:
            receipt["task_started"] = False
            receipt["benchmark_trials_consumed"] = 0
            receipt["status"] = "PRESTART_ABORT__NONCONSUMING"
        receipt["error_type"] = type(exc).__name__
        receipt["error"] = str(exc)
        if proc is not None:
            _terminate(proc)
        _write_receipt(receipt)
        return 1
    finally:
        if log_handle is not None:
            log_handle.close()


def main() -> int:
    return run_once()


if __name__ == "__main__":
    raise SystemExit(main())
