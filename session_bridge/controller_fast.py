#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.request

import controller as legacy
import acceptance_contract as acceptance

EVIDENCE = Path("/tmp/bridge-evidence")
COMMAND_MARKER = "<!-- BRAIN_FAST_BURST_COMMAND_V2 -->"
OBS_MARKER = "<!-- BRAIN_FAST_BURST_OBSERVATION_V2 -->"
READY_MARKER = "<!-- BRAIN_FAST_BURST_READY_V2 -->"
INSTRUCTION_MARKER = "<!-- BRAIN_FAST_BURST_INSTRUCTION_V1 -->"
LEASE_MARKER = "<!-- BRAIN_FAST_BURST_LEASE_AUTHORIZATION_V1 -->"
LEASE_BOUND_MARKER = "<!-- BRAIN_FAST_BURST_LEASE_BOUND_V1 -->"
LEASE_REVALIDATION_MARKER = "<!-- BRAIN_FAST_BURST_LEASE_REVALIDATION_V1 -->"
ACCEPTANCE_MARKER = "<!-- BRAIN_FAST_BURST_ACCEPTANCE_MODEL_V1 -->"
ACCEPTANCE_FROZEN_MARKER = "<!-- BRAIN_FAST_BURST_ACCEPTANCE_FROZEN_V1 -->"
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

def current_pr_open() -> bool:
    repo = os.environ["GITHUB_REPOSITORY"]
    pr = os.environ["PR_NUMBER"]
    payload = gh_api("GET", f"/repos/{repo}/pulls/{pr}") or {}
    return payload.get("state") == "open"

def runtime_authority_errors(
    *,
    session_id: str,
    task: str,
    lease_authorized: bool,
    bound_lease,
    revalidation,
    scope: str,
    burst_id: int | None = None,
    pr_open: bool = True,
):
    if not lease_authorized or not isinstance(bound_lease, dict):
        return ["CANONICAL_LEASE_NOT_BOUND"]
    if not pr_open:
        return ["RUNNER_PR_NOT_OPEN"]
    if revalidation is None:
        return ["PER_ACTION_CANONICAL_LEASE_REVALIDATION_REQUIRED"]
    return acceptance.validate_lease_revalidation(
        revalidation,
        session_id,
        task,
        bound_lease,
        expected_scope=scope,
        expected_burst_id=burst_id,
    )


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


def normalize_artifact_contract(entries):
    """Normalize trusted task artifact metadata for this single-container carrier.

    String artifacts are supported directly. Structured artifacts are supported
    only when they do not require another service/container and do not request
    exclude filtering. Unsupported entries are surfaced before runtime build so
    the task can be skipped unspent instead of crashing or producing false
    capability evidence.
    """
    normalized = []
    unsupported = []
    for entry in entries:
        if isinstance(entry, str):
            normalized.append({"source": entry, "destination": entry, "service": None})
            continue
        if not isinstance(entry, dict):
            unsupported.append({"entry": entry, "reason": "INVALID_ARTIFACT_ENTRY_TYPE"})
            continue
        source = entry.get("source")
        destination = entry.get("destination") or source
        service = entry.get("service")
        exclude = entry.get("exclude")
        if not isinstance(source, str) or not source:
            unsupported.append({"entry": entry, "reason": "ARTIFACT_SOURCE_MISSING_OR_INVALID"})
            continue
        if not isinstance(destination, str) or not destination:
            unsupported.append({"entry": entry, "reason": "ARTIFACT_DESTINATION_INVALID"})
            continue
        if service:
            unsupported.append({
                "source": source,
                "destination": destination,
                "service": service,
                "reason": "PER_SERVICE_ARTIFACT_REQUIRES_MULTI_SERVICE_COLLECTOR",
            })
            continue
        if exclude:
            unsupported.append({
                "source": source,
                "destination": destination,
                "exclude": exclude,
                "reason": "ARTIFACT_EXCLUDE_FILTER_UNSUPPORTED",
            })
            continue
        normalized.append({"source": source, "destination": destination, "service": None})
    return normalized, unsupported


def surface_instruction(task_dir: Path):
    """Surface only the official agent instruction after READY; fail closed."""
    path = task_dir / "instruction.md"
    if not path.is_file():
        post("<!-- BRAIN_FAST_BURST_INSTRUCTION_BLOCKED_V1 -->", {
            "schema": "BRAIN_FAST_BURST_INSTRUCTION_BLOCKED_V1",
            "session_id": CONFIG["session_id"],
            "task": CONFIG["task"],
            "reason": "INSTRUCTION_MD_MISSING",
        })
        return False
    raw = path.read_bytes()
    text_value = raw.decode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    payload = {
        "schema": "BRAIN_FAST_BURST_INSTRUCTION_V1",
        "session_id": CONFIG["session_id"],
        "task": CONFIG["task"],
        "instruction_sha256": digest,
        "instruction_length": len(text_value),
        "instruction": text_value,
        "authority": "OFFICIAL_TASK_INSTRUCTION_MD_AFTER_READY",
        "solution_tests_verifier_exposed": False,
    }
    marker_body = INSTRUCTION_MARKER + "\n" + json.dumps(payload, sort_keys=True)
    if len(marker_body) > int(CONFIG.get("comment_char_limit", 60000)):
        post("<!-- BRAIN_FAST_BURST_INSTRUCTION_BLOCKED_V1 -->", {
            "schema": "BRAIN_FAST_BURST_INSTRUCTION_BLOCKED_V1",
            "session_id": CONFIG["session_id"],
            "task": CONFIG["task"],
            "reason": "INSTRUCTION_TOO_LARGE_FOR_EXACT_COMMENT_HANDOFF",
            "instruction_sha256": digest,
            "instruction_length": len(text_value),
        })
        return False
    post(INSTRUCTION_MARKER, payload)
    return True

def terminal_blocker(payload, acceptance_payload=None, acceptance_hash=None, lease_authorized=False):
    if payload.get("schema") != "BRAIN_FAST_BURST_TERMINAL_AUTHORIZATION_V2":
        return "SCHEMA_INVALID"
    if payload.get("session_id") != CONFIG["session_id"]:
        return "SESSION_MISMATCH"
    if CONFIG.get("require_canonical_lease_authorization", True) and not lease_authorized:
        return "CANONICAL_LEASE_NOT_BOUND"
    if CONFIG.get("require_acceptance_contract", True):
        if acceptance_payload is None or not acceptance_hash:
            return "ACCEPTANCE_CONTRACT_NOT_FROZEN"
        errors = acceptance.terminal_acceptance_errors(payload, acceptance_payload, acceptance_hash)
        if errors:
            return errors[0]
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
    CONFIG.setdefault("require_acceptance_contract", True)
    CONFIG.setdefault("require_canonical_lease_authorization", True)

    legacy.CONFIG = CONFIG
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    task_dir = legacy.clone_task()

    # Artifact metadata is trusted execution-interface metadata. Inspect it
    # before building the task runtime so unsupported multi-service contracts
    # can be skipped unspent without exposing task instructions or burning CI.
    raw_artifacts, verifier_environment_mode = legacy.load_artifacts(task_dir)
    artifact_contract, unsupported_artifacts = normalize_artifact_contract(raw_artifacts)
    if unsupported_artifacts:
        post("<!-- BRAIN_FAST_BURST_SURFACE_INCOMPATIBLE_V2 -->", {
            "schema": "BRAIN_FAST_BURST_SURFACE_INCOMPATIBLE_V2",
            "session_id": CONFIG["session_id"],
            "task": CONFIG["task"],
            "reason": "ARTIFACT_CONTRACT_UNSUPPORTED_BY_SINGLE_CONTAINER_CARRIER",
            "unsupported_artifacts": unsupported_artifacts,
            "verifier_environment_mode": verifier_environment_mode,
            "instruction_read": False,
            "capability_credit_delta": 0,
        })
        return 0

    legacy.build_runtime(task_dir)
    artifact_paths = [item["source"] for item in artifact_contract]
    artifact_parent_dirs = sorted({str(Path(p).parent) for p in artifact_paths if str(Path(p).parent)})
    for parent in artifact_parent_dirs:
        legacy.run(["docker", "exec", "brain-bridge-task", "mkdir", "-p", parent])

    bootstrap = replay_bootstrap()

    post(READY_MARKER, {
        "schema": "BRAIN_FAST_BURST_READY_V2",
        "session_id": CONFIG["session_id"],
        "task": CONFIG["task"],
        "transport": "PR_COMMENT_BURST",
        "microstep_git_commits": 0,
        "bootstrap": bootstrap,
        "max_commands_per_burst": int(CONFIG.get("max_commands_per_burst", 8)),
        "artifact_paths": artifact_paths,
        "artifact_contract": artifact_contract,
        "verifier_environment_mode": verifier_environment_mode,
        "artifact_contract_authority": "TRUSTED_TASK_METADATA_ONLY__NO_SOLUTION_TEST_OR_VERIFIER_CONTENT_EXPOSED",
    })

    seen = set()
    next_burst = 0
    lease_payload = None
    lease_authorized = False
    instruction_surfaced = False
    acceptance_payload = None
    acceptance_hash = None
    burst_revalidations = {}
    terminal_revalidation = None
    deadline = time.time() + int(CONFIG.get("session_timeout_sec", 10800))
    while time.time() < deadline:
        for comment in comments():
            cid = comment.get("id")
            if cid in seen or not authorized(comment):
                continue
            body = comment.get("body") or ""

            lease = parse_payload(body, LEASE_MARKER)
            if lease is not None:
                seen.add(cid)
                if lease_authorized:
                    post("<!-- BRAIN_FAST_BURST_LEASE_BLOCKED_V1 -->", {
                        "schema": "BRAIN_FAST_BURST_LEASE_BLOCKED_V1",
                        "session_id": CONFIG["session_id"],
                        "reason": "CANONICAL_LEASE_ALREADY_BOUND",
                    })
                    continue
                if next_burst != 0 or acceptance_hash is not None:
                    post("<!-- BRAIN_FAST_BURST_LEASE_BLOCKED_V1 -->", {
                        "schema": "BRAIN_FAST_BURST_LEASE_BLOCKED_V1",
                        "session_id": CONFIG["session_id"],
                        "reason": "SESSION_ALREADY_ADVANCED_BEYOND_LEASE_GATE",
                    })
                    continue
                errors = acceptance.validate_lease_authorization(
                    lease, CONFIG["session_id"], CONFIG["task"]
                )
                if errors:
                    post("<!-- BRAIN_FAST_BURST_LEASE_BLOCKED_V1 -->", {
                        "schema": "BRAIN_FAST_BURST_LEASE_BLOCKED_V1",
                        "session_id": CONFIG["session_id"],
                        "reason": errors[0],
                        "all_errors": errors,
                    })
                    continue
                lease_payload = lease
                lease_authorized = True
                legacy.write_json(EVIDENCE / "canonical_lease_authorization.json", lease_payload)
                post(LEASE_BOUND_MARKER, {
                    "schema": "BRAIN_FAST_BURST_LEASE_BOUND_V1",
                    "session_id": CONFIG["session_id"],
                    "task": CONFIG["task"],
                    "canonical_brain_commit": lease["canonical_brain_commit"],
                    "canonical_lease_path": lease["canonical_lease_path"],
                    "sample_rank": lease["sample_rank"],
                    "instruction_exposed": False,
                })
                if not surface_instruction(task_dir):
                    return 0
                instruction_surfaced = True
                continue

            revalidation = parse_payload(body, LEASE_REVALIDATION_MARKER)
            if revalidation is not None:
                seen.add(cid)
                if not lease_authorized or not isinstance(lease_payload, dict):
                    post("<!-- BRAIN_FAST_BURST_LEASE_REVALIDATION_BLOCKED_V1 -->", {
                        "schema": "BRAIN_FAST_BURST_LEASE_REVALIDATION_BLOCKED_V1",
                        "session_id": CONFIG["session_id"],
                        "reason": "CANONICAL_LEASE_NOT_BOUND",
                    })
                    continue
                scope = revalidation.get("scope")
                expected_burst = next_burst if scope == "BURST" else None
                errors = acceptance.validate_lease_revalidation(
                    revalidation,
                    CONFIG["session_id"],
                    CONFIG["task"],
                    lease_payload,
                    expected_scope=scope,
                    expected_burst_id=expected_burst,
                )
                if errors:
                    post("<!-- BRAIN_FAST_BURST_LEASE_REVALIDATION_BLOCKED_V1 -->", {
                        "schema": "BRAIN_FAST_BURST_LEASE_REVALIDATION_BLOCKED_V1",
                        "session_id": CONFIG["session_id"],
                        "reason": errors[0],
                        "all_errors": errors,
                    })
                    continue
                if not current_pr_open():
                    post("<!-- BRAIN_FAST_BURST_LEASE_REVALIDATION_BLOCKED_V1 -->", {
                        "schema": "BRAIN_FAST_BURST_LEASE_REVALIDATION_BLOCKED_V1",
                        "session_id": CONFIG["session_id"],
                        "reason": "RUNNER_PR_NOT_OPEN",
                    })
                    return 0
                if scope == "BURST":
                    burst_revalidations[next_burst] = revalidation
                elif scope == "TERMINAL":
                    terminal_revalidation = revalidation
                post("<!-- BRAIN_FAST_BURST_LEASE_REVALIDATED_V1 -->", {
                    "schema": "BRAIN_FAST_BURST_LEASE_REVALIDATED_V1",
                    "session_id": CONFIG["session_id"],
                    "scope": scope,
                    "burst_id": revalidation.get("burst_id"),
                    "canonical_brain_commit": revalidation.get("canonical_brain_commit"),
                    "canonical_lease_path": revalidation.get("canonical_lease_path"),
                })
                continue

            contract = parse_payload(body, ACCEPTANCE_MARKER)
            if contract is not None:
                seen.add(cid)
                if CONFIG.get("require_canonical_lease_authorization", True) and not lease_authorized:
                    post("<!-- BRAIN_FAST_BURST_ACCEPTANCE_BLOCKED_V1 -->", {
                        "schema": "BRAIN_FAST_BURST_ACCEPTANCE_BLOCKED_V1",
                        "session_id": CONFIG["session_id"],
                        "reason": "CANONICAL_LEASE_NOT_BOUND",
                    })
                    continue
                if not instruction_surfaced:
                    post("<!-- BRAIN_FAST_BURST_ACCEPTANCE_BLOCKED_V1 -->", {
                        "schema": "BRAIN_FAST_BURST_ACCEPTANCE_BLOCKED_V1",
                        "session_id": CONFIG["session_id"],
                        "reason": "OFFICIAL_INSTRUCTION_NOT_SURFACED",
                    })
                    continue
                if acceptance_hash is not None:
                    post("<!-- BRAIN_FAST_BURST_ACCEPTANCE_BLOCKED_V1 -->", {
                        "schema": "BRAIN_FAST_BURST_ACCEPTANCE_BLOCKED_V1",
                        "session_id": CONFIG["session_id"],
                        "reason": "ACCEPTANCE_CONTRACT_ALREADY_FROZEN",
                        "acceptance_contract_sha256": acceptance_hash,
                    })
                    continue
                if next_burst != 0:
                    post("<!-- BRAIN_FAST_BURST_ACCEPTANCE_BLOCKED_V1 -->", {
                        "schema": "BRAIN_FAST_BURST_ACCEPTANCE_BLOCKED_V1",
                        "session_id": CONFIG["session_id"],
                        "reason": "BUILDER_ALREADY_STARTED",
                    })
                    continue
                errors = acceptance.validate_acceptance_payload(contract, CONFIG["session_id"])
                if errors:
                    post("<!-- BRAIN_FAST_BURST_ACCEPTANCE_BLOCKED_V1 -->", {
                        "schema": "BRAIN_FAST_BURST_ACCEPTANCE_BLOCKED_V1",
                        "session_id": CONFIG["session_id"],
                        "reason": errors[0],
                        "all_errors": errors,
                    })
                    continue
                acceptance_payload = contract
                acceptance_hash = acceptance.canonical_payload_hash(contract)
                artifact_baseline = {}
                for artifact in artifact_paths:
                    probe = legacy.run(
                        ["docker", "exec", "brain-bridge-task", "test", "-e", artifact],
                        check=False,
                    )
                    artifact_baseline[artifact] = {"exists_before_builder": probe.returncode == 0}
                legacy.write_json(EVIDENCE / "acceptance_contract.json", {
                    "acceptance_contract_sha256": acceptance_hash,
                    "contract": acceptance_payload,
                    "artifact_baseline": artifact_baseline,
                    "next_burst_at_freeze": next_burst,
                })
                post(ACCEPTANCE_FROZEN_MARKER, {
                    "schema": "BRAIN_FAST_BURST_ACCEPTANCE_FROZEN_V1",
                    "session_id": CONFIG["session_id"],
                    "acceptance_contract_sha256": acceptance_hash,
                    "artifact_baseline": artifact_baseline,
                    "builder_commands_executed": 0,
                })
                continue

            terminal = parse_payload(body, TERMINAL_MARKER)
            if terminal is not None:
                seen.add(cid)
                authority_errors = runtime_authority_errors(
                    session_id=CONFIG["session_id"],
                    task=CONFIG["task"],
                    lease_authorized=lease_authorized,
                    bound_lease=lease_payload,
                    revalidation=terminal_revalidation,
                    scope="TERMINAL",
                    pr_open=current_pr_open(),
                )
                if authority_errors:
                    post("<!-- BRAIN_FAST_BURST_TERMINAL_BLOCKED_V2 -->", {
                        "schema": "BRAIN_FAST_BURST_TERMINAL_BLOCKED_V2",
                        "session_id": CONFIG["session_id"],
                        "reason": authority_errors[0],
                        "all_errors": authority_errors,
                    })
                    if authority_errors[0] == "RUNNER_PR_NOT_OPEN":
                        return 0
                    continue
                blocker = terminal_blocker(terminal, acceptance_payload, acceptance_hash, lease_authorized)
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
            if CONFIG.get("require_canonical_lease_authorization", True):
                authority_errors = runtime_authority_errors(
                    session_id=CONFIG["session_id"],
                    task=CONFIG["task"],
                    lease_authorized=lease_authorized,
                    bound_lease=lease_payload,
                    revalidation=burst_revalidations.get(next_burst),
                    scope="BURST",
                    burst_id=next_burst,
                    pr_open=current_pr_open(),
                )
                if authority_errors:
                    post("<!-- BRAIN_FAST_BURST_REJECTED_V2 -->", {
                        "schema": "BRAIN_FAST_BURST_REJECTED_V2",
                        "session_id": CONFIG["session_id"],
                        "reason": authority_errors[0],
                        "all_errors": authority_errors,
                    })
                    if authority_errors[0] == "RUNNER_PR_NOT_OPEN":
                        return 0
                    continue
            if CONFIG.get("require_acceptance_contract", True):
                if acceptance_hash is None:
                    post("<!-- BRAIN_FAST_BURST_REJECTED_V2 -->", {
                        "schema": "BRAIN_FAST_BURST_REJECTED_V2",
                        "session_id": CONFIG["session_id"],
                        "reason": "ACCEPTANCE_CONTRACT_REQUIRED_BEFORE_BUILDER_COMMAND",
                    })
                    continue
                if payload.get("acceptance_contract_sha256") != acceptance_hash:
                    post("<!-- BRAIN_FAST_BURST_REJECTED_V2 -->", {
                        "schema": "BRAIN_FAST_BURST_REJECTED_V2",
                        "session_id": CONFIG["session_id"],
                        "reason": "ACCEPTANCE_CONTRACT_HASH_MISMATCH",
                        "expected_acceptance_contract_sha256": acceptance_hash,
                    })
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

            # Single-use authority: consume the current-burst revalidation before
            # execution so it can never authorize a later/replayed burst.
            burst_revalidations.pop(next_burst, None)
            terminal_revalidation = None
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
