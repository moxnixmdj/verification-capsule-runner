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

SCHEMA = "PROJECT_BRAIN_TB_SCIENCE_RANK15_V5_BARRIER_RUNNER"
SLOT_ID = "terminal-bench-science/protein-active-learning::trial-0"
TASK_DIGEST = "sha256:d7e16b7c468551b468364cf2a86dba2383b007f3f2f01c6d2ce01d99ff30d48f"
BARRIER_REL = Path("RANK15_AGENT_START_BARRIER")
READY_REL = BARRIER_REL / "AGENT_READY.json"
COMMIT_REL = BARRIER_REL / "START_COMMITTED.json"
CAS_RECEIPT = ROOT / "RANK15_START_CAS_V5.json"
RUNNER_RECEIPT = ROOT / "RANK15_V5_BARRIER_RUNNER_RECEIPT.json"
HARBOR_LOG = ROOT / "RANK15_V5_HARBOR_RUN.log"
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
    env["BRAIN_AGENT_START_BARRIER_TIMEOUT_S"] = str(int(READY_TIMEOUT_S))
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
        "canonical.runtime.harbor_science_agent_v4:HarborScienceAgent",
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


def _acquire_start_commit() -> None:
    proc = subprocess.run(
        [sys.executable, str(C / "rank15_start_cas_v5.py"), "--acquire"],
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
        "acceptance_credit_delta": 0,
        "terminal_credit_delta": 0,
    }

    proc = None
    log_handle = None
    try:
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

        rc = int(proc.wait())
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
