#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.request

import controller as legacy

EVIDENCE = Path("/tmp/bridge-evidence")
COMMAND_MARKER = "<!-- BRAIN_FAST_BURST_COMMAND_V2 -->"
OBS_MARKER = "<!-- BRAIN_FAST_BURST_OBSERVATION_V2 -->"
READY_MARKER = "<!-- BRAIN_FAST_BURST_READY_V2 -->"
TERMINAL_MARKER = "<!-- BRAIN_FAST_BURST_TERMINAL_V2 -->"
FINAL_MARKER = "<!-- BRAIN_FAST_BURST_FINAL_V2 -->"


def gh_api(method: str, path: str, payload=None):
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + os.environ["GITHUB_TOKEN"],
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "brain-fast-burst-v2",
    }
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request("https://api.github.com" + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw) if raw else None


def post(marker: str, payload):
    body = marker + "\n" + json.dumps(payload, sort_keys=True)
    limit = int(CONFIG.get("comment_char_limit", 60000))
    if len(body) > limit:
        slim = dict(payload)
        slim["truncated_for_comment"] = True
        if isinstance(slim.get("results"), list):
            trimmed = []
            for item in slim["results"]:
                x = dict(item)
                for k in ("stdout", "stderr"):
                    if isinstance(x.get(k), str):
                        x[k] = x[k][-3000:]
                trimmed.append(x)
            slim["results"] = trimmed
        body = (marker + "\n" + json.dumps(slim, sort_keys=True))[:limit]
    repo = os.environ["GITHUB_REPOSITORY"]
    pr = os.environ["PR_NUMBER"]
    return gh_api("POST", f"/repos/{repo}/issues/{pr}/comments", {"body": body})


def comments():
    repo = os.environ["GITHUB_REPOSITORY"]
    pr = os.environ["PR_NUMBER"]
    try:
        return gh_api("GET", f"/repos/{repo}/issues/{pr}/comments?per_page=100") or []
    except urllib.error.HTTPError as exc:
        if exc.code not in (403, 429):
            raise
        retry_after = exc.headers.get("Retry-After")
        reset_at = exc.headers.get("X-RateLimit-Reset")
        delay = 15.0
        if retry_after:
            try:
                delay = max(delay, float(retry_after))
            except ValueError:
                pass
        if reset_at:
            try:
                delay = max(delay, float(reset_at) - time.time() + 2.0)
            except ValueError:
                pass
        time.sleep(min(max(delay, 1.0), 300.0))
        return []


def parse_payload(body: str, marker: str):
    if marker not in body:
        return None
    raw = body.split(marker, 1)[1].strip()
    try:
        return json.loads(raw)
    except Exception:
        return None


def authorized(comment):
    return (comment.get("user") or {}).get("login") == CONFIG["authorized_controller_login"]


def replay_bootstrap():
    spec = CONFIG.get("bootstrap_replay")
    if not spec:
        return {"enabled": False, "executed": 0}
    cp = legacy.git("fetch", "--quiet", "origin", spec["ref"], check=False)
    if cp.returncode != 0:
        raise RuntimeError("BOOTSTRAP_REF_FETCH_FAILED:" + (cp.stderr or "")[-2000:])
    records = []
    for step in range(int(spec.get("start", 0)), int(spec["end"]) + 1):
        rel = f"session_bridge/commands/{step:03d}.sh"
        show = legacy.git("show", f"FETCH_HEAD:{rel}", check=False)
        if show.returncode != 0:
            records.append({"step": step, "status": "MISSING"})
            if spec.get("require_contiguous", True):
                break
            continue
        obs = legacy.execute_command(step, show.stdout)
        records.append(obs)
        if obs["exit_code"] != 0 and spec.get("stop_on_error", True):
            break
    legacy.write_json(EVIDENCE / "bootstrap_replay.json", records)
    return {
        "enabled": True,
        "ref": spec["ref"],
        "requested": [int(spec.get("start", 0)), int(spec["end"])],
        "executed": sum(1 for r in records if "exit_code" in r),
        "last": records[-1] if records else None,
    }


def terminal_blocker(payload):
    if payload.get("schema") != "BRAIN_FAST_BURST_TERMINAL_AUTHORIZATION_V2":
        return "SCHEMA_INVALID"
    if payload.get("session_id") != CONFIG["session_id"]:
        return "SESSION_MISMATCH"
    if payload.get("submission_authorized") is not True:
        return "SUBMISSION_NOT_AUTHORIZED"
    if payload.get("known_relevant_failures") not in ([], None):
        return "KNOWN_RELEVANT_FAILURES_REMAIN"
    criteria = payload.get("acceptance_criteria")
    checks = payload.get("verification_commands")
    if not isinstance(criteria, list) or not criteria:
        return "ACCEPTANCE_CRITERIA_EVIDENCE_MISSING"
    if any(not isinstance(x, dict) or x.get("status") != "PASS" or not x.get("evidence") for x in criteria):
        return "ACCEPTANCE_CRITERIA_NOT_ALL_PASS"
    if not isinstance(checks, list) or not checks:
        return "VERIFICATION_COMMANDS_MISSING"
    if any(not isinstance(x, dict) or x.get("exit_code") != 0 or not x.get("command") for x in checks):
        return "VERIFICATION_COMMANDS_NOT_ALL_PASS"
    return None


def main():
    global CONFIG
    ap = argparse.ArgumentParser()
    ap.add_argument("--session-config", default="session_bridge/session.json")
    args = ap.parse_args()
    CONFIG = json.loads(Path(args.session_config).read_text(encoding="utf-8"))
    CONFIG.setdefault("authorized_controller_login", os.environ["GITHUB_REPOSITORY"].split("/", 1)[0])

    legacy.CONFIG = CONFIG
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    task_dir = legacy.clone_task()
    legacy.build_runtime(task_dir)
    bootstrap = replay_bootstrap()

    post(READY_MARKER, {
        "schema": "BRAIN_FAST_BURST_READY_V2",
        "session_id": CONFIG["session_id"],
        "task": CONFIG["task"],
        "transport": "PR_COMMENT_BURST",
        "microstep_git_commits": 0,
        "bootstrap": bootstrap,
        "max_commands_per_burst": int(CONFIG.get("max_commands_per_burst", 8)),
    })

    seen = set()
    next_burst = 0
    deadline = time.time() + int(CONFIG.get("session_timeout_sec", 10800))
    while time.time() < deadline:
        for comment in comments():
            cid = comment.get("id")
            if cid in seen or not authorized(comment):
                continue
            body = comment.get("body") or ""

            terminal = parse_payload(body, TERMINAL_MARKER)
            if terminal is not None:
                seen.add(cid)
                blocker = terminal_blocker(terminal)
                if blocker:
                    post("<!-- BRAIN_FAST_BURST_TERMINAL_BLOCKED_V2 -->", {
                        "schema": "BRAIN_FAST_BURST_TERMINAL_BLOCKED_V2",
                        "session_id": CONFIG["session_id"],
                        "reason": blocker,
                    })
                    continue
                final = legacy.verify(task_dir)
                post(FINAL_MARKER, final)
                return 0

            payload = parse_payload(body, COMMAND_MARKER)
            if payload is None:
                continue
            seen.add(cid)
            if payload.get("schema") != "BRAIN_FAST_BURST_COMMAND_V2":
                continue
            if payload.get("session_id") != CONFIG["session_id"]:
                continue
            if int(payload.get("burst_id", -1)) != next_burst:
                post("<!-- BRAIN_FAST_BURST_REJECTED_V2 -->", {
                    "schema": "BRAIN_FAST_BURST_REJECTED_V2",
                    "session_id": CONFIG["session_id"],
                    "expected_burst_id": next_burst,
                    "received_burst_id": payload.get("burst_id"),
                })
                continue
            cmds = payload.get("commands")
            if not isinstance(cmds, list) or not cmds:
                continue
            if len(cmds) > int(CONFIG.get("max_commands_per_burst", 8)):
                post("<!-- BRAIN_FAST_BURST_REJECTED_V2 -->", {
                    "schema": "BRAIN_FAST_BURST_REJECTED_V2",
                    "session_id": CONFIG["session_id"],
                    "reason": "TOO_MANY_COMMANDS",
                })
                continue

            results = []
            for idx, item in enumerate(cmds):
                if not isinstance(item, dict) or not isinstance(item.get("script"), str):
                    results.append({"index": idx, "exit_code": 2, "stderr": "INVALID_COMMAND_ITEM"})
                    break
                obs = legacy.execute_command(next_burst * 100 + idx, item["script"])
                obs["id"] = item.get("id", str(idx))
                results.append(obs)
                if obs["exit_code"] != 0 and item.get("stop_on_error", True):
                    break
            legacy.write_json(EVIDENCE / f"burst_{next_burst:03d}.json", {
                "session_id": CONFIG["session_id"],
                "burst_id": next_burst,
                "results": results,
            })
            post(OBS_MARKER, {
                "schema": "BRAIN_FAST_BURST_OBSERVATION_V2",
                "session_id": CONFIG["session_id"],
                "burst_id": next_burst,
                "results": results,
            })
            next_burst += 1
            if next_burst >= int(CONFIG.get("max_bursts", 20)):
                post("<!-- BRAIN_FAST_BURST_STOP_V2 -->", {
                    "schema": "BRAIN_FAST_BURST_STOP_V2",
                    "session_id": CONFIG["session_id"],
                    "reason": "BURST_LIMIT",
                })
                return 0

        time.sleep(float(CONFIG.get("poll_interval_sec", 2)))

    post("<!-- BRAIN_FAST_BURST_STOP_V2 -->", {
        "schema": "BRAIN_FAST_BURST_STOP_V2",
        "session_id": CONFIG["session_id"],
        "reason": "SESSION_TIMEOUT",
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
