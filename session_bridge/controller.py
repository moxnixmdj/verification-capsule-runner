#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import time
import tomllib

ROOT = Path.cwd()
EVIDENCE = Path("/tmp/bridge-evidence")
TB = Path("/tmp/terminal-bench")
OBS = Path("/tmp/bridge-observations")


def run(cmd, *, cwd=None, check=True, capture=True, timeout=None):
    return subprocess.run(
        cmd,
        cwd=cwd,
        check=check,
        text=True,
        capture_output=capture,
        timeout=timeout,
    )


def git(*args, cwd=ROOT, check=True, capture=True):
    return run(["git", *args], cwd=cwd, check=check, capture=capture)


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def commit_obs(relpath: str, value, message: str):
    path = OBS / relpath
    write_json(path, value)
    git("add", relpath, cwd=OBS)
    cp = git("diff", "--cached", "--quiet", cwd=OBS, check=False)
    if cp.returncode != 0:
        git("commit", "-m", message, cwd=OBS, capture=True)
        git("push", "origin", f"HEAD:refs/heads/{CONFIG['observation_branch']}", cwd=OBS, capture=True)


def init_observation_branch():
    if OBS.exists():
        shutil.rmtree(OBS)
    git("worktree", "add", "-b", "bridge-observation-work", str(OBS), "HEAD")
    git("config", "user.email", "brain-bridge@users.noreply.github.com", cwd=OBS)
    git("config", "user.name", "Brain Session Bridge", cwd=OBS)
    git("push", "origin", f"HEAD:refs/heads/{CONFIG['observation_branch']}", cwd=OBS)


def fetch_command(step: int):
    cp = git("fetch", "--quiet", "origin", CONFIG["control_branch"], check=False)
    if cp.returncode != 0:
        return None
    rel = f"session_bridge/commands/{step:03d}.sh"
    cp = git("show", f"FETCH_HEAD:{rel}", check=False)
    if cp.returncode != 0:
        return None
    return cp.stdout


def clone_task():
    if TB.exists():
        shutil.rmtree(TB)
    run(["git", "clone", "--filter=blob:none", "--no-checkout",
         "https://github.com/harbor-framework/terminal-bench.git", str(TB)],
        timeout=1800)
    git("sparse-checkout", "init", "--no-cone", cwd=TB)
    pattern = f"tasks/{CONFIG['task']}/*\n"
    (TB / ".git/info/sparse-checkout").write_text(pattern, encoding="utf-8")
    git("checkout", "--detach", CONFIG["terminal_bench_ref"], cwd=TB)
    return TB / "tasks" / CONFIG["task"]


def build_runtime(task_dir: Path):
    image = f"brain-bridge-task-{CONFIG['session_id']}"
    run(["docker", "build", "-t", image, str(task_dir / "environment")],
        timeout=int(CONFIG.get("build_timeout_sec", 1800)), capture=False)
    run(["docker", "rm", "-f", "brain-bridge-task"], check=False)
    run([
        "docker", "run", "-d", "--name", "brain-bridge-task",
        "--entrypoint", "/bin/sh", image, "-lc",
        "trap : TERM INT; while :; do sleep 3600; done"
    ])
    return image


def execute_command(step: int, command: str):
    command_bytes = command.encode("utf-8")
    sha = hashlib.sha256(command_bytes).hexdigest()
    local = Path("/tmp/bridge-command.sh")
    local.write_bytes(command_bytes)
    run(["docker", "cp", str(local), "brain-bridge-task:/tmp/bridge-command.sh"])
    started = time.time()
    limit = int(CONFIG.get("command_timeout_sec", 300))
    cp = run([
        "docker", "exec", "-w", "/app", "brain-bridge-task",
        "/bin/sh", "-lc",
        f"if command -v timeout >/dev/null 2>&1; then timeout -k 5 {limit}s /bin/bash /tmp/bridge-command.sh; else /bin/bash /tmp/bridge-command.sh; fi"
    ], check=False, timeout=limit + 15)
    cap = int(CONFIG.get("observation_char_limit", 120000))
    return {
        "schema": "BRAIN_SESSION_MINI_SWE_OBSERVATION_V1",
        "session_id": CONFIG["session_id"],
        "step": step,
        "command_sha256": sha,
        "exit_code": cp.returncode,
        "duration_sec": round(time.time() - started, 3),
        "stdout": (cp.stdout or "")[-cap:],
        "stderr": (cp.stderr or "")[-cap:],
    }


def load_artifacts(task_dir: Path):
    payload = tomllib.loads((task_dir / "task.toml").read_text(encoding="utf-8"))
    return list(payload.get("artifacts") or []), str((payload.get("verifier") or {}).get("environment_mode") or "")


def stream_artifact(src_path: str, target_container: str):
    relative = src_path.lstrip("/")
    exists = run(["docker", "exec", "brain-bridge-task", "test", "-e", src_path], check=False)
    if exists.returncode != 0:
        return False
    producer = subprocess.Popen(
        ["docker", "exec", "brain-bridge-task", "tar", "-C", "/", "-cf", "-", relative],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    consumer = subprocess.Popen(
        ["docker", "exec", "-i", target_container, "tar", "-C", "/", "-xf", "-"],
        stdin=producer.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if producer.stdout:
        producer.stdout.close()
    cout, cerr = consumer.communicate(timeout=600)
    _, perr = producer.communicate(timeout=600)
    if producer.returncode != 0 or consumer.returncode != 0:
        raise RuntimeError(
            f"ARTIFACT_TRANSFER_FAILED:{src_path}:producer={producer.returncode}:consumer={consumer.returncode}:"
            + (perr or b"").decode(errors="replace")[-2000:]
            + (cerr or b"").decode(errors="replace")[-2000:]
        )
    return True


def archive_candidate(artifacts):
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    existing = []
    for path in artifacts:
        if run(["docker", "exec", "brain-bridge-task", "test", "-e", path], check=False).returncode == 0:
            existing.append(path.lstrip("/"))
    if not existing:
        return None
    out = EVIDENCE / "candidate_artifacts.tar.gz"
    with out.open("wb") as fh:
        cp = subprocess.run(
            ["docker", "exec", "brain-bridge-task", "tar", "-C", "/", "-czf", "-", *existing],
            stdout=fh,
            stderr=subprocess.PIPE,
            check=False,
        )
    if cp.returncode != 0:
        raise RuntimeError("CANDIDATE_ARCHIVE_FAILED:" + (cp.stderr or b"").decode(errors="replace")[-4000:])
    return str(out)


def verify(task_dir: Path):
    artifacts, mode = load_artifacts(task_dir)
    archive = archive_candidate(artifacts)
    result = {
        "schema": "BRAIN_SESSION_MINI_SWE_FINAL_VERIFICATION_V1",
        "session_id": CONFIG["session_id"],
        "task": CONFIG["task"],
        "terminal_bench_ref": CONFIG["terminal_bench_ref"],
        "environment_mode": mode,
        "artifact_paths": artifacts,
        "candidate_archive": archive,
        "incremental_spend_usd": 0,
    }
    if mode != "separate":
        result.update(status="UNSUPPORTED_VERIFIER_MODE", reward=None)
        return result

    verifier_image = f"brain-bridge-verifier-{CONFIG['session_id']}"
    run(["docker", "build", "-t", verifier_image, str(task_dir / "tests")],
        timeout=int(CONFIG.get("verifier_build_timeout_sec", 1800)), capture=False)
    run(["docker", "rm", "-f", "brain-bridge-verifier"], check=False)
    run([
        "docker", "create", "--name", "brain-bridge-verifier", "--user", "0",
        "--entrypoint", "/bin/sh", verifier_image, "-lc",
        "trap : TERM INT; while :; do sleep 3600; done"
    ])
    run(["docker", "start", "brain-bridge-verifier"])
    run(["docker", "exec", "brain-bridge-verifier", "mkdir", "-p", "/logs/verifier", "/logs/agent"])

    missing = []
    for path in artifacts:
        if not stream_artifact(path, "brain-bridge-verifier"):
            missing.append(path)

    limit = int(CONFIG.get("verifier_timeout_sec", 1200))
    cp = run([
        "docker", "exec", "-w", "/app", "brain-bridge-verifier",
        "/bin/sh", "-lc",
        f"if command -v timeout >/dev/null 2>&1; then timeout -k 5 {limit}s /bin/bash /tests/test.sh; else /bin/bash /tests/test.sh; fi"
    ], check=False, timeout=limit + 20)
    reward = None
    for path in ("/logs/verifier/reward.txt", "/logs/verifier/reward.json"):
        rp = run(["docker", "exec", "brain-bridge-verifier", "cat", path], check=False)
        if rp.returncode == 0:
            reward = (rp.stdout or "").strip()
            break
    cap = int(CONFIG.get("verifier_output_char_limit", 120000))
    result.update(
        status="VERIFIER_COMPLETED",
        verifier_exit_code=cp.returncode,
        reward=reward,
        missing_artifacts=missing,
        verifier_stdout=(cp.stdout or "")[-cap:],
        verifier_stderr=(cp.stderr or "")[-cap:],
    )
    write_json(EVIDENCE / "final_verification.json", result)
    return result


def main():
    global CONFIG
    ap = argparse.ArgumentParser()
    ap.add_argument("--session-config", default="session_bridge/session.json")
    args = ap.parse_args()
    CONFIG = json.loads(Path(args.session_config).read_text(encoding="utf-8"))
    CONFIG.setdefault("control_branch", os.environ.get("GITHUB_HEAD_REF", ""))
    if not CONFIG.get("control_branch"):
        raise SystemExit("CONTROL_BRANCH_REQUIRED")
    if not CONFIG.get("observation_branch"):
        CONFIG["observation_branch"] = f"bridge-observations/{CONFIG['session_id']}"

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    init_observation_branch()
    commit_obs("session_bridge/status.json", {
        "status": "BUILDING_RUNTIME",
        "session_id": CONFIG["session_id"],
        "task": CONFIG["task"],
        "terminal_bench_ref": CONFIG["terminal_bench_ref"],
    }, "bridge: initialize session")

    task_dir = clone_task()
    build_runtime(task_dir)
    commit_obs("session_bridge/status.json", {
        "status": "READY_FOR_COMMAND",
        "session_id": CONFIG["session_id"],
        "task": CONFIG["task"],
        "next_step": 0,
        "runtime_boundary": "COMMANDS_EXECUTE_ONLY_INSIDE_BUILT_TASK_CONTAINER",
    }, "bridge: runtime ready")

    deadline = time.time() + int(CONFIG.get("session_timeout_sec", 7200))
    max_steps = int(CONFIG.get("max_steps", 80))
    for step in range(max_steps):
        while time.time() < deadline:
            command = fetch_command(step)
            if command is not None:
                break
            time.sleep(int(CONFIG.get("poll_interval_sec", 5)))
        else:
            commit_obs("session_bridge/status.json", {
                "status": "SESSION_TIMEOUT",
                "session_id": CONFIG["session_id"],
                "next_step": step,
            }, "bridge: session timeout")
            return 0

        if command.strip() == "echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT":
            blocked_reason = None
            auth = None
            # Authorization is deliberately fetched from the live control branch,
            # just like commands. The session may only be authorized after its
            # runtime evidence exists; the initial checkout must not freeze a
            # permanently-missing authorization file.
            cp = git("fetch", "--quiet", "origin", CONFIG["control_branch"], check=False)
            if cp.returncode != 0:
                blocked_reason = "TERMINAL_AUTHORIZATION_CONTROL_FETCH_FAILED"
            else:
                rel = "session_bridge/terminal_authorization.json"
                cp = git("show", f"FETCH_HEAD:{rel}", check=False)
                if cp.returncode != 0:
                    blocked_reason = "TERMINAL_AUTHORIZATION_MISSING"
                else:
                    try:
                        auth = json.loads(cp.stdout)
                    except Exception:
                        blocked_reason = "TERMINAL_AUTHORIZATION_INVALID_JSON"

            if blocked_reason is None:
                if auth.get("schema") != "BRAIN_SESSION_TERMINAL_AUTHORIZATION_V1":
                    blocked_reason = "TERMINAL_AUTHORIZATION_SCHEMA_INVALID"
                elif auth.get("session_id") != CONFIG["session_id"]:
                    blocked_reason = "TERMINAL_AUTHORIZATION_SESSION_MISMATCH"
                elif auth.get("submission_authorized") is not True:
                    blocked_reason = "TERMINAL_AUTHORIZATION_FALSE"
                elif auth.get("known_relevant_failures") not in ([], None):
                    blocked_reason = "KNOWN_RELEVANT_FAILURES_REMAIN"
                else:
                    criteria = auth.get("acceptance_criteria")
                    checks = auth.get("verification_commands")
                    if not isinstance(criteria, list) or not criteria:
                        blocked_reason = "ACCEPTANCE_CRITERIA_EVIDENCE_MISSING"
                    elif any(not isinstance(x, dict) or x.get("status") != "PASS" or not x.get("evidence") for x in criteria):
                        blocked_reason = "ACCEPTANCE_CRITERIA_NOT_ALL_PASS"
                    elif not isinstance(checks, list) or not checks:
                        blocked_reason = "VERIFICATION_COMMANDS_MISSING"
                    elif any(not isinstance(x, dict) or x.get("exit_code") != 0 or not x.get("command") for x in checks):
                        blocked_reason = "VERIFICATION_COMMANDS_NOT_ALL_PASS"

            if blocked_reason is not None:
                commit_obs(f"session_bridge/observations/{step:03d}.json", {
                    "schema": "BRAIN_SESSION_MINI_SWE_OBSERVATION_V1",
                    "session_id": CONFIG["session_id"],
                    "step": step,
                    "command_sha256": hashlib.sha256(command.encode()).hexdigest(),
                    "exit_code": 1,
                    "stdout": "",
                    "stderr": "SUBMISSION_BLOCKED__" + blocked_reason + "\n",
                }, f"bridge: block premature submission step {step}")
                commit_obs("session_bridge/status.json", {
                    "status": "READY_FOR_COMMAND",
                    "session_id": CONFIG["session_id"],
                    "task": CONFIG["task"],
                    "next_step": step + 1,
                    "last_submission_blocker": blocked_reason,
                }, f"bridge: continue after blocked submission step {step}")
                continue

            commit_obs(f"session_bridge/observations/{step:03d}.json", {
                "schema": "BRAIN_SESSION_MINI_SWE_OBSERVATION_V1",
                "session_id": CONFIG["session_id"],
                "step": step,
                "command_sha256": hashlib.sha256(command.encode()).hexdigest(),
                "exit_code": 0,
                "stdout": "SUBMISSION_ACCEPTED_FOR_INDEPENDENT_VERIFICATION\n",
                "stderr": "",
                "completion_authorization": auth,
            }, f"bridge: accept authorized submission step {step}")
            final = verify(task_dir)
            commit_obs("session_bridge/final_verification.json", final, "bridge: independent verifier result")
            commit_obs("session_bridge/status.json", {
                "status": "COMPLETE",
                "session_id": CONFIG["session_id"],
                "final_step": step,
                "verifier_status": final.get("status"),
                "reward": final.get("reward"),
            }, "bridge: session complete")
            return 0

        obs = execute_command(step, command)
        commit_obs(f"session_bridge/observations/{step:03d}.json", obs, f"bridge: observation step {step}")
        commit_obs("session_bridge/status.json", {
            "status": "READY_FOR_COMMAND",
            "session_id": CONFIG["session_id"],
            "task": CONFIG["task"],
            "next_step": step + 1,
        }, f"bridge: ready step {step + 1}")

    commit_obs("session_bridge/status.json", {
        "status": "STEP_LIMIT",
        "session_id": CONFIG["session_id"],
        "max_steps": max_steps,
    }, "bridge: step limit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
