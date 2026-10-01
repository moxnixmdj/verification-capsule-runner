#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
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


def fetch_control_text(rel: str):
    cp = git("fetch", "--quiet", "origin", CONFIG["control_branch"], check=False)
    if cp.returncode != 0:
        return None
    cp = git("show", f"FETCH_HEAD:{rel}", check=False)
    if cp.returncode != 0:
        return None
    return cp.stdout


def fetch_command(step: int):
    return fetch_control_text(f"session_bridge/commands/{step:03d}.sh")


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



def _safe_artifact_path(value, field):
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field}_MISSING_OR_INVALID")
    if "\x00" in value or "\n" in value or "\r" in value:
        raise ValueError(f"{field}_CONTROL_CHARACTER")
    p = Path(value)
    if not p.is_absolute() or ".." in p.parts:
        raise ValueError(f"{field}_MUST_BE_ABSOLUTE_NORMALIZED_PATH")
    return str(p)


def _safe_exclude_pattern(value):
    if not isinstance(value, str) or not value:
        raise ValueError("ARTIFACT_EXCLUDE_PATTERN_INVALID")
    if "\x00" in value or "\n" in value or "\r" in value:
        raise ValueError("ARTIFACT_EXCLUDE_PATTERN_CONTROL_CHARACTER")
    p = Path(value)
    if p.is_absolute() or ".." in p.parts:
        raise ValueError("ARTIFACT_EXCLUDE_PATTERN_MUST_BE_RELATIVE")
    return value


def normalize_artifact_contract(entries):
    """Normalize trusted artifact metadata into a safe transport contract.

    Supports path strings and structured single-container artifacts with
    source/destination plus relative tar-exclude patterns. Per-service artifacts
    remain unsupported by this carrier and fail closed before task execution.
    """
    normalized = []
    unsupported = []
    for entry in entries:
        if isinstance(entry, str):
            try:
                path = _safe_artifact_path(entry, "ARTIFACT_SOURCE")
            except ValueError as exc:
                unsupported.append({"entry": entry, "reason": str(exc)})
                continue
            normalized.append({"source": path, "destination": path, "service": None, "exclude": []})
            continue
        if not isinstance(entry, dict):
            unsupported.append({"entry": entry, "reason": "INVALID_ARTIFACT_ENTRY_TYPE"})
            continue
        try:
            source = _safe_artifact_path(entry.get("source"), "ARTIFACT_SOURCE")
            destination = _safe_artifact_path(entry.get("destination") or entry.get("source"), "ARTIFACT_DESTINATION")
        except ValueError as exc:
            unsupported.append({"entry": entry, "reason": str(exc)})
            continue
        service = entry.get("service")
        if service:
            unsupported.append({
                "source": source,
                "destination": destination,
                "service": service,
                "reason": "PER_SERVICE_ARTIFACT_REQUIRES_MULTI_SERVICE_COLLECTOR",
            })
            continue
        raw_exclude = entry.get("exclude") or []
        if not isinstance(raw_exclude, list):
            unsupported.append({
                "source": source,
                "destination": destination,
                "exclude": raw_exclude,
                "reason": "ARTIFACT_EXCLUDE_MUST_BE_LIST",
            })
            continue
        try:
            exclude = [_safe_exclude_pattern(x) for x in raw_exclude]
        except ValueError as exc:
            unsupported.append({
                "source": source,
                "destination": destination,
                "exclude": raw_exclude,
                "reason": str(exc),
            })
            continue
        normalized.append({
            "source": source,
            "destination": destination,
            "service": None,
            "exclude": exclude,
        })
    return normalized, unsupported


def _artifact_entry(value):
    if isinstance(value, str):
        contract, unsupported = normalize_artifact_contract([value])
        if unsupported:
            raise ValueError(unsupported[0]["reason"])
        return contract[0]
    if isinstance(value, dict) and "source" in value:
        # Already-normalized contracts are revalidated so callers cannot bypass
        # the path/exclude safety boundary.
        contract, unsupported = normalize_artifact_contract([value])
        if unsupported:
            raise ValueError(unsupported[0]["reason"])
        return contract[0]
    raise ValueError("INVALID_ARTIFACT_ENTRY_TYPE")


def _rooted_exclude_patterns(source: str, excludes):
    """Translate artifact-root-relative excludes into GNU-tar member patterns."""
    src = source.lstrip("/").rstrip("/")
    patterns = []
    for pattern in excludes:
        # Exact root-relative path plus descendant match. GNU tar exclusion
        # wildcards match slashes, so the second pattern covers nested names.
        patterns.append(f"{src}/{pattern}")
        patterns.append(f"{src}/*/{pattern}")
    return list(dict.fromkeys(patterns))


def _tar_transform(source: str, destination: str):
    src = source.lstrip("/").rstrip("/")
    dst = destination.lstrip("/").rstrip("/")
    if src == dst:
        return None
    # GNU tar's transform uses a sed expression. Escape the delimiter,
    # backslash, regex metacharacters in the source, and replacement '&'.
    regex = src
    for ch in ("\\", "|", ".", "[", "]", "^", "$", "*"):
        regex = regex.replace(ch, "\\" + ch)
    replacement = dst.replace("\\", "\\\\").replace("|", "\\|").replace("&", "\\&")
    return f"s|^{regex}|{replacement}|"


def stage_missing_artifacts(artifacts):
    """Stage a uniquely matching output into each required builder source path.

    This remains conservative: it never guesses among multiple candidates and
    copies directories recursively only when exactly one fallback exists.
    """
    roots = list(CONFIG.get("artifact_fallback_roots") or ["/app", "/workspace"])
    staged = []
    unresolved = []
    for raw in artifacts:
        try:
            entry = _artifact_entry(raw)
        except ValueError as exc:
            unresolved.append({"required": raw, "reason": str(exc)})
            continue
        dst = entry["source"]
        exists = run(["docker", "exec", "brain-bridge-task", "test", "-e", dst], check=False)
        if exists.returncode == 0:
            continue
        basename = Path(dst).name
        candidates = []
        for root in roots:
            src = str(Path(root) / basename)
            # Preserve historical fallback staging semantics: fallback
            # discovery is for uniquely named files only. Directory artifacts
            # must be written at their contractual source path by the builder.
            probe = run(["docker", "exec", "brain-bridge-task", "test", "-f", src], check=False)
            if probe.returncode == 0:
                candidates.append(src)
        candidates = sorted(set(candidates))
        if len(candidates) != 1:
            unresolved.append({"required": dst, "candidates": candidates})
            continue
        src = candidates[0]
        parent = str(Path(dst).parent)
        script = (
            f"mkdir -p {shlex.quote(parent)} && "
            f"cp -a -- {shlex.quote(src)} {shlex.quote(dst)}"
        )
        cp = run(["docker", "exec", "brain-bridge-task", "/bin/sh", "-lc", script], check=False)
        if cp.returncode != 0:
            unresolved.append({"required": dst, "candidates": candidates, "copy_error": (cp.stderr or "")[-2000:]})
            continue
        staged.append({"source": src, "required": dst})
    return {"staged": staged, "unresolved": unresolved}

def stream_artifact(artifact, target_container: str):
    entry = _artifact_entry(artifact)
    src_path = entry["source"]
    dst_path = entry["destination"]
    relative = src_path.lstrip("/")
    exists = run(["docker", "exec", "brain-bridge-task", "test", "-e", src_path], check=False)
    if exists.returncode != 0:
        return False

    tar_cmd = ["docker", "exec", "brain-bridge-task", "tar", "-C", "/"]
    for pattern in _rooted_exclude_patterns(src_path, entry.get("exclude") or []):
        tar_cmd.append("--exclude=" + pattern)
    transform = _tar_transform(src_path, dst_path)
    if transform:
        tar_cmd.append("--transform=" + transform)
    tar_cmd += ["-cf", "-", relative]

    producer = subprocess.Popen(
        tar_cmd,
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
            f"ARTIFACT_TRANSFER_FAILED:{src_path}->{dst_path}:producer={producer.returncode}:consumer={consumer.returncode}:"
            + (perr or b"").decode(errors="replace")[-2000:]
            + (cerr or b"").decode(errors="replace")[-2000:]
        )
    return True

def archive_candidate(artifacts):
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    entries = []
    for raw in artifacts:
        entry = _artifact_entry(raw)
        if run(["docker", "exec", "brain-bridge-task", "test", "-e", entry["source"]], check=False).returncode == 0:
            entries.append(entry)
    if not entries:
        return None
    out = EVIDENCE / "candidate_artifacts.tar.gz"
    tar_cmd = ["docker", "exec", "brain-bridge-task", "tar", "-C", "/"]
    for entry in entries:
        for pattern in _rooted_exclude_patterns(entry["source"], entry.get("exclude") or []):
            tar_cmd.append("--exclude=" + pattern)
    tar_cmd += ["-czf", "-"] + [entry["source"].lstrip("/") for entry in entries]
    with out.open("wb") as fh:
        cp = subprocess.run(
            tar_cmd,
            stdout=fh,
            stderr=subprocess.PIPE,
            check=False,
        )
    if cp.returncode != 0:
        raise RuntimeError("CANDIDATE_ARCHIVE_FAILED:" + (cp.stderr or b"").decode(errors="replace")[-4000:])
    return str(out)

def verify(task_dir: Path, artifact_contract=None):
    raw_artifacts, mode = load_artifacts(task_dir)
    if artifact_contract is None:
        artifact_contract, unsupported = normalize_artifact_contract(raw_artifacts)
        if unsupported:
            return {
                "schema": "BRAIN_SESSION_MINI_SWE_FINAL_VERIFICATION_V1",
                "session_id": CONFIG["session_id"],
                "task": CONFIG["task"],
                "terminal_bench_ref": CONFIG["terminal_bench_ref"],
                "environment_mode": mode,
                "status": "UNSUPPORTED_ARTIFACT_CONTRACT",
                "unsupported_artifacts": unsupported,
                "reward": None,
                "incremental_spend_usd": 0,
            }
    artifact_staging = stage_missing_artifacts(artifact_contract)
    archive = archive_candidate(artifact_contract)
    result = {
        "schema": "BRAIN_SESSION_MINI_SWE_FINAL_VERIFICATION_V1",
        "session_id": CONFIG["session_id"],
        "task": CONFIG["task"],
        "terminal_bench_ref": CONFIG["terminal_bench_ref"],
        "environment_mode": mode,
        "artifact_paths": [x["destination"] for x in artifact_contract],
        "artifact_contract": artifact_contract,
        "candidate_archive": archive,
        "artifact_staging": artifact_staging,
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
    for entry in artifact_contract:
        if not stream_artifact(entry, "brain-bridge-verifier"):
            missing.append(entry["destination"])

    limit = int(CONFIG.get("verifier_timeout_sec", 1200))
    # Verifier images are not required to contain /app. Choose a valid cwd
    # before starting the hidden verifier so an OCI chdir failure cannot burn
    # a clean submission without executing the verifier at all.
    wd_probe = run([
        "docker", "exec", "brain-bridge-verifier",
        "/bin/sh", "-lc", "if [ -d /app ]; then printf /app; else printf /; fi"
    ], check=False)
    verifier_workdir = (wd_probe.stdout or "").strip() or "/"
    cp = run([
        "docker", "exec", "-w", verifier_workdir, "brain-bridge-verifier",
        "/bin/sh", "-lc",
        f"if command -v timeout >/dev/null 2>&1; then timeout -k 5 {limit}s /bin/bash /tests/test.sh; else /bin/bash /tests/test.sh; fi"
    ], check=False, timeout=limit + 20)
    reward = None
    for path in ("/logs/verifier/reward.txt", "/logs/verifier/reward.json"):
        rp = run(["docker", "exec", "brain-bridge-verifier", "cat", path], check=False)
        if rp.returncode == 0:
            reward = (rp.stdout or "").strip()
            break
    # Preserve the verifier's structured test report in the durable evidence
    # artifact. A reward/exit code without the failed-test identities is not
    # sufficient to distinguish a capability failure from verifier bootstrap
    # or evidence-transport failure.
    ctrf_payload = None
    ctrf_probe = run(
        ["docker", "exec", "brain-bridge-verifier", "cat", "/logs/verifier/ctrf.json"],
        check=False,
    )
    if ctrf_probe.returncode == 0 and (ctrf_probe.stdout or "").strip():
        ctrf_text = ctrf_probe.stdout or ""
        (EVIDENCE / "verifier_ctrf.json").write_text(ctrf_text, encoding="utf-8")
        try:
            ctrf_payload = json.loads(ctrf_text)
        except json.JSONDecodeError:
            ctrf_payload = {"parse_error": True, "raw_tail": ctrf_text[-4000:]}

    cap = int(CONFIG.get("verifier_output_char_limit", 120000))
    result.update(
        status="VERIFIER_COMPLETED",
        verifier_exit_code=cp.returncode,
        reward=reward,
        missing_artifacts=missing,
        verifier_stdout=(cp.stdout or "")[-cap:],
        verifier_stderr=(cp.stderr or "")[-cap:],
        verifier_ctrf=ctrf_payload,
        verifier_ctrf_evidence_path=str(EVIDENCE / "verifier_ctrf.json") if ctrf_payload is not None else None,
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
            auth_text = fetch_control_text("session_bridge/terminal_authorization.json")
            if auth_text is None:
                blocked_reason = "TERMINAL_AUTHORIZATION_MISSING"
            else:
                try:
                    auth = json.loads(auth_text)
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
