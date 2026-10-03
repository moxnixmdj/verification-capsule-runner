#!/usr/bin/env python3
"""Zero-reality attainability verifier for Terminal-Bench-Science v0.1.0.

This verifier reads ONLY public task.toml resource metadata from the exact
v0.1.0 release. It never reads task instructions, tests, solutions, graders, or
benchmark outputs, and it never executes a benchmark task.

The proof target is deliberately narrow:
  - a hard-$0 public GitHub-hosted runner exists,
  - Docker/Compose are usable,
  - enough of the exact 70-task v0.1.0 population fits the observed carrier
    that a full-benchmark score of 58.7% is mathematically attainable even if
    every incompatible task is conservatively assigned zero.

It does NOT prove a Brain score, capability parity, or acceptance.
"""
from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import sys
import tomllib
import urllib.request
from dataclasses import dataclass
from typing import Any

UPSTREAM_REPO = "harbor-framework/terminal-bench-science"
UPSTREAM_COMMIT = "f81afac4f11048e77a15dfc8fb1dbfb897fea0ce"
EXPECTED_TREE = "d880cb1969f28eb0f7f85df681232e26b2a3e7e3"
EXPECTED_TASK_COUNT = 70
TARGET_SCORE = 0.587
TRIALS_PER_TASK = 3
ALLOWED_SUFFIX = "/task.toml"


@dataclass(frozen=True)
class Carrier:
    cpus: int
    memory_mb: int
    free_storage_mb: int
    docker: bool
    docker_compose: bool


def _request(url: str) -> bytes:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "project-brain-tb-science-carrier-verifier-v1",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
        return r.read()


def _json(url: str) -> Any:
    return json.loads(_request(url).decode("utf-8"))


def _run_ok(argv: list[str]) -> bool:
    try:
        p = subprocess.run(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
        return p.returncode == 0
    except Exception:
        return False


def measure_carrier() -> Carrier:
    cpus = os.cpu_count() or 0
    mem_kb = 0
    with open("/proc/meminfo", "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("MemTotal:"):
                mem_kb = int(line.split()[1])
                break
    free = shutil.disk_usage("/").free // (1024 * 1024)
    return Carrier(
        cpus=int(cpus),
        memory_mb=int(mem_kb // 1024),
        free_storage_mb=int(free),
        docker=_run_ok(["docker", "info"]),
        docker_compose=_run_ok(["docker", "compose", "version"]),
    )


def task_paths() -> list[str]:
    tree = _json(
        f"https://api.github.com/repos/{UPSTREAM_REPO}/git/trees/{EXPECTED_TREE}?recursive=1"
    )
    if tree.get("truncated") is True:
        raise RuntimeError("UPSTREAM_TREE_TRUNCATED")
    paths = sorted(
        row["path"]
        for row in tree.get("tree", [])
        if row.get("type") == "blob"
        and str(row.get("path", "")).startswith("tasks/")
        and str(row.get("path", "")).endswith(ALLOWED_SUFFIX)
    )
    if len(paths) != EXPECTED_TASK_COUNT:
        raise RuntimeError(f"TASK_COUNT_MISMATCH:{len(paths)}")
    if any(
        p.endswith(("instruction.md", "solution.sh", "test.sh"))
        or "/tests/" in p
        or "/solution" in p
        for p in paths
    ):
        raise RuntimeError("FORBIDDEN_TASK_CONTENT_PATH")
    return paths


def load_resource_row(path: str) -> dict[str, Any]:
    if not (path.startswith("tasks/") and path.endswith(ALLOWED_SUFFIX)):
        raise RuntimeError("NON_METADATA_PATH_FORBIDDEN")
    raw = _request(
        f"https://raw.githubusercontent.com/{UPSTREAM_REPO}/{UPSTREAM_COMMIT}/{path}"
    )
    doc = tomllib.loads(raw.decode("utf-8"))
    env = doc.get("environment")
    if not isinstance(env, dict):
        raise RuntimeError(f"ENVIRONMENT_SECTION_MISSING:{path}")
    fields = {}
    for key in ("cpus", "memory_mb", "storage_mb", "gpus"):
        value = env.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise RuntimeError(f"INVALID_RESOURCE_FIELD:{path}:{key}:{value!r}")
        fields[key] = int(value)
    return {"path": path, **fields}


def compatible(row: dict[str, Any], carrier: Carrier) -> bool:
    return bool(
        row["cpus"] <= carrier.cpus
        and row["memory_mb"] <= carrier.memory_mb
        and row["storage_mb"] <= carrier.free_storage_mb
        and row["gpus"] == 0
        and carrier.docker
        and carrier.docker_compose
    )


def evaluate(rows: list[dict[str, Any]], carrier: Carrier) -> dict[str, Any]:
    good = [r for r in rows if compatible(r, carrier)]
    bad = [r for r in rows if not compatible(r, carrier)]
    n = len(rows)
    k = len(good)
    max_full_score_if_unrunnable_zero = k / n if n else 0.0
    required_compatible_mean = TARGET_SCORE * n / k if k else math.inf
    compatible_trial_slots = k * TRIALS_PER_TASK
    total_trial_slots = n * TRIALS_PER_TASK

    passed = bool(
        n == EXPECTED_TASK_COUNT
        and carrier.docker
        and carrier.docker_compose
        and max_full_score_if_unrunnable_zero >= TARGET_SCORE
        and required_compatible_mean <= 1.0
    )
    return {
        "schema": "PROJECT_BRAIN_TB_SCIENCE_V01_PUBLIC_GITHUB_CARRIER_ATTAINABILITY_V1",
        "status": (
            "PASS__ZERO_COST_PUBLIC_GITHUB_CARRIER_MAKES_FROZEN_58_7_BAR_MATHEMATICALLY_ATTAINABLE__ZERO_ACCEPTANCE_CREDIT"
            if passed
            else "FAIL_CLOSED__PUBLIC_GITHUB_CARRIER_DOES_NOT_PROVE_ATTAINABILITY"
        ),
        "pass": passed,
        "upstream": {
            "repository": UPSTREAM_REPO,
            "commit": UPSTREAM_COMMIT,
            "tree": EXPECTED_TREE,
            "task_count": n,
            "metadata_only": True,
        },
        "carrier": {
            "cpus": carrier.cpus,
            "memory_mb": carrier.memory_mb,
            "free_storage_mb": carrier.free_storage_mb,
            "docker": carrier.docker,
            "docker_compose": carrier.docker_compose,
            "zero_incremental_spend": True,
            "carrier_kind": "PUBLIC_GITHUB_HOSTED_RUNNER",
        },
        "attainability": {
            "target_score": TARGET_SCORE,
            "trials_per_task": TRIALS_PER_TASK,
            "compatible_task_count": k,
            "incompatible_task_count": len(bad),
            "compatible_trial_slots": compatible_trial_slots,
            "total_trial_slots": total_trial_slots,
            "max_full_score_if_all_incompatible_zero": max_full_score_if_unrunnable_zero,
            "required_mean_on_compatible_tasks_if_all_incompatible_zero": required_compatible_mean,
            "threshold_attainable": max_full_score_if_unrunnable_zero >= TARGET_SCORE,
        },
        "incompatible_resources": bad,
        "hard_nonclaims": [
            "NO_BENCHMARK_TASK_EXECUTION",
            "NO_TASK_INSTRUCTION_TEST_SOLUTION_OR_GRADER_READ",
            "NO_BRAIN_SCORE_CLAIM",
            "NO_OPUS_PARITY_CLAIM",
            "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
            "ATTAINABILITY_IS_NOT_ACHIEVEMENT",
        ],
        "new_reality_units_consumed": 0,
        "terminal_cases_consumed": 0,
        "incremental_spend_usd": 0,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }


def main() -> int:
    paths = task_paths()
    rows = [load_resource_row(p) for p in paths]
    out = evaluate(rows, measure_carrier())
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
