from __future__ import annotations

import asyncio
import hashlib
import json
import os
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

from harbor.job import Job
from harbor.models.job.plugin import BaseJobPlugin
from harbor.models.job.result import JobResult
from harbor.trial.hooks import TrialEvent, TrialHookEvent

SCHEMA = "PROJECT_BRAIN_TB_SCIENCE_RANK15_AGENT_START_CAS_PLUGIN_V1"
EXPECTED_SLOT = "terminal-bench-science/protein-active-learning::trial-0"
EXPECTED_DIGEST = "sha256:d7e16b7c468551b468364cf2a86dba2383b007f3f2f01c6d2ce01d99ff30d48f"
DEFAULT_RECEIPT = "RANK15_AGENT_START_CAS_PLUGIN_V1.json"


class AgentStartCASError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AgentStartCASError("JSON_OBJECT_REQUIRED:" + str(path))
    return value


class Rank15AgentStartCASPlugin(BaseJobPlugin):
    """Acquire the irreversible Rank15 start CAS at Harbor AGENT_START.

    Harbor emits AGENT_START only after Trial._prepare() has completed. The
    callback is awaited before the agent run proceeds. This plugin therefore
    moves the irreversible accounting boundary after environment setup while
    keeping repository credentials outside the task sandbox.
    """

    def __init__(
        self,
        token_path: str,
        cas_script: str,
        receipt_path: str = DEFAULT_RECEIPT,
        expected_task_name: str = "terminal-bench-science/protein-active-learning",
    ) -> None:
        super().__init__()
        self.token_path = Path(token_path)
        self.cas_script = Path(cas_script)
        self.receipt_path = Path(receipt_path)
        self.expected_task_name = expected_task_name
        self._registered = False
        self._fired = False
        self._job_end_seen = False

    @staticmethod
    def _assert_host_token_env_absent() -> None:
        leaked = [key for key in ("GH_TOKEN", "GITHUB_TOKEN") if os.environ.get(key)]
        if leaked:
            raise AgentStartCASError(
                "REPOSITORY_WRITE_TOKEN_PRESENT_IN_HARBOR_HOST_ENV:" + ",".join(leaked)
            )

    def _consume_token_file(self) -> str:
        path = self.token_path
        if not path.is_absolute():
            raise AgentStartCASError("TOKEN_PATH_MUST_BE_ABSOLUTE")
        runner_temp_raw = os.environ.get("RUNNER_TEMP")
        if not runner_temp_raw:
            raise AgentStartCASError("RUNNER_TEMP_REQUIRED")
        runner_temp = Path(runner_temp_raw).resolve()
        parent = path.parent.resolve()
        if parent != runner_temp and runner_temp not in parent.parents:
            raise AgentStartCASError("TOKEN_PATH_MUST_BE_UNDER_RUNNER_TEMP")
        workspace_raw = os.environ.get("GITHUB_WORKSPACE")
        if workspace_raw:
            workspace = Path(workspace_raw).resolve()
            if parent == workspace or workspace in parent.parents:
                raise AgentStartCASError("TOKEN_PATH_MUST_BE_OUTSIDE_WORKSPACE")
        try:
            info = path.lstat()
        except FileNotFoundError as exc:
            raise AgentStartCASError("TOKEN_FILE_MISSING") from exc
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
            raise AgentStartCASError("TOKEN_FILE_MUST_BE_NONSYMLINK_REGULAR_FILE")
        if info.st_uid != os.getuid():
            raise AgentStartCASError("TOKEN_FILE_OWNER_MISMATCH")
        if stat.S_IMODE(info.st_mode) & 0o077:
            raise AgentStartCASError("TOKEN_FILE_PERMISSIONS_TOO_BROAD")
        token = path.read_text(encoding="utf-8").strip()
        if not token:
            raise AgentStartCASError("TOKEN_FILE_EMPTY")
        path.unlink()
        if path.exists():
            raise AgentStartCASError("TOKEN_FILE_DELETE_UNCONFIRMED")
        return token

    def _run_cas_subprocess(self, token: str) -> tuple[int, str, str]:
        script = self.cas_script.resolve()
        if not script.is_file():
            raise AgentStartCASError("CAS_SCRIPT_MISSING")
        env = os.environ.copy()
        env.pop("GH_TOKEN", None)
        env.pop("GITHUB_TOKEN", None)
        env["GH_TOKEN"] = token
        proc = subprocess.run(
            [sys.executable, str(script), "--acquire"],
            cwd=Path(os.environ.get("GITHUB_WORKSPACE") or ".").resolve(),
            env=env,
            text=True,
            capture_output=True,
            timeout=60,
            check=False,
        )
        return int(proc.returncode), proc.stdout, proc.stderr

    async def on_job_start(self, job: Job) -> None:
        self._assert_host_token_env_absent()
        if self._registered:
            raise AgentStartCASError("PLUGIN_REGISTERED_TWICE")
        self._registered = True
        job.on_agent_started(self._on_agent_started)

    async def _on_agent_started(self, event: TrialHookEvent) -> None:
        self._assert_host_token_env_absent()
        if event.event != TrialEvent.AGENT_START:
            raise AgentStartCASError("WRONG_HOOK_EVENT")
        if self._fired:
            raise AgentStartCASError("AGENT_START_HOOK_FIRED_MORE_THAN_ONCE")
        if event.task_name != self.expected_task_name:
            raise AgentStartCASError(
                f"TASK_NAME_MISMATCH:{event.task_name}!={self.expected_task_name}"
            )
        self._fired = True

        token = self._consume_token_file()
        try:
            returncode, stdout, stderr = await asyncio.to_thread(
                self._run_cas_subprocess, token
            )
        finally:
            token = ""

        workspace = Path(os.environ.get("GITHUB_WORKSPACE") or ".").resolve()
        cas_receipt_path = workspace / "RANK15_START_CAS_V3.json"
        cas_receipt = _load_json(cas_receipt_path) if cas_receipt_path.is_file() else {}
        success = (
            returncode == 0
            and cas_receipt.get("pass") is True
            and cas_receipt.get("acquired") is True
            and cas_receipt.get("task_started") is True
            and cas_receipt.get("slot_id") == EXPECTED_SLOT
            and cas_receipt.get("task_digest") == EXPECTED_DIGEST
            and cas_receipt.get("replay_authority") is False
            and cas_receipt.get("replacement_carrier_authority") is False
        )

        receipt = {
            "schema": SCHEMA,
            "status": (
                "PASS__CAS_COMMITTED_AT_HARBOR_AGENT_START"
                if success
                else "FAIL_CLOSED__CAS_NOT_CONFIRMED_AT_AGENT_START"
            ),
            "pass": success,
            "trial_name": event.trial_name,
            "trial_id": str(event.trial_id),
            "task_name": event.task_name,
            "hook_event": event.event.value,
            "token_file_deleted_before_cas_subprocess": not self.token_path.exists(),
            "host_repository_token_env_absent": not any(
                os.environ.get(k) for k in ("GH_TOKEN", "GITHUB_TOKEN")
            ),
            "cas_subprocess_returncode": returncode,
            "cas_receipt_sha256": (
                _sha256(cas_receipt_path) if cas_receipt_path.is_file() else None
            ),
            "cas_generic_key": cas_receipt.get("generic_cas_key"),
            "logical_attempt_id": cas_receipt.get("logical_attempt_id"),
            "runtime_identity_sha256": cas_receipt.get("runtime_identity_sha256"),
            "prestart_receipt_sha256": cas_receipt.get("prestart_receipt_sha256"),
            "durable_record_sha256": cas_receipt.get("durable_record_sha256"),
            "replay_authority": False,
            "replacement_carrier_authority": False,
            "task_started": success,
            "benchmark_trials_consumed": 1 if success else 0,
            "acceptance_credit_delta": 0,
            "terminal_credit_delta": 0,
            "incremental_spend_usd": 0,
            "stderr_sha256": hashlib.sha256(stderr.encode()).hexdigest(),
            "stdout_sha256": hashlib.sha256(stdout.encode()).hexdigest(),
        }
        target = self.receipt_path
        if not target.is_absolute():
            target = workspace / target
        target.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if not success:
            raise AgentStartCASError(
                "DURABLE_START_CAS_NOT_CONFIRMED_BEFORE_AGENT_EXECUTION"
            )

    async def on_job_end(self, job_result: JobResult) -> None:
        self._job_end_seen = True
