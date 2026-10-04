#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pyarrow.parquet as pq

import candidate_livebench_legacy15_joint_witness_v1 as candidate
from candidate_livebench_frozen_active_legacy15_v1 import ACTIVE_IDS

SCHEMA = "PROJECT_BRAIN_LEGACY15_DETERMINISTIC_EXACT_PUBLIC_ROOT1_V1"
LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
PARQUET_SHA256 = "a9bb97bbaf8788142c310bcb33d50e2f6f5df8cbd8b8c3db677816b06f0f4f25"
PARQUET_BYTES = 537024
SELECTED_RELEASE = "2026-06-25"
TASKS = ("paraphrase", "simplify", "story_generation", "summarize")
PASS_FLOOR_PERCENT = 65.73775
VALID_RELEASE_DATES = {
    "2024-06-24","2024-07-26","2024-08-31","2024-11-25",
    "2025-04-02","2025-04-25","2025-05-30","2025-11-25",
    "2025-12-23","2026-01-08","2026-06-25",
}

sys.path.insert(0, "/tmp/LiveBench/livebench/if_runner")
from instruction_following_eval import instructions_registry  # noqa: E402


def clean_date(v) -> str:
    if v is None:
        return ""
    return v.strftime("%Y-%m-%d") if hasattr(v, "strftime") else str(v)


def strict_score(question: dict, response: str) -> tuple[float, list[bool]]:
    prompt = question["turns"][0]
    ids = list(question["instruction_id_list"])
    kwargs = [{k: v for k, v in d.items() if v is not None} for d in question["kwargs"]]
    followed: list[bool] = []
    for idx, instruction_id in enumerate(ids):
        cls = instructions_registry.INSTRUCTION_DICT[instruction_id]
        instruction = cls(instruction_id)
        instruction.build_description(**kwargs[idx])
        args = instruction.get_instruction_args()
        if args and "prompt" in args:
            instruction.build_description(prompt=prompt)
        followed.append(bool(response.strip()) and bool(instruction.check_following(response)))
    all_followed = all(followed)
    per_instruction = sum(1 for x in followed if x) / len(followed)
    return ((1.0 if all_followed else 0.0) + per_instruction) / 2.0, followed


def main() -> int:
    parquet = Path("/tmp/instruction_following.parquet")
    if parquet.stat().st_size != PARQUET_BYTES:
        raise SystemExit(f"PARQUET_BYTE_MISMATCH:{parquet.stat().st_size}")
    got = hashlib.sha256(parquet.read_bytes()).hexdigest()
    if got != PARQUET_SHA256:
        raise SystemExit(f"PARQUET_SHA_MISMATCH:{got}")

    rows = pq.read_table(parquet).to_pylist()
    active = []
    for row in rows:
        rd = clean_date(row.get("livebench_release_date"))
        rem = clean_date(row.get("livebench_removal_date"))
        if (
            row.get("task") in TASKS
            and rd in VALID_RELEASE_DATES
            and (rem == "" or rem > SELECTED_RELEASE)
        ):
            active.append(row)

    counts = Counter(str(r["task"]) for r in active)
    if len(active) != 200 or counts != Counter({t: 50 for t in TASKS}):
        raise SystemExit(f"ACTIVE_POPULATION_MISMATCH:{len(active)}:{dict(counts)}")
    if any(clean_date(r["livebench_release_date"]) >= "2025-11-25" for r in active):
        raise SystemExit("NONLEGACY_ROW_PRESENT")

    hidden_ids = {str(iid) for r in active for iid in (r.get("instruction_id_list") or [])}
    outside = sorted(hidden_ids - set(ACTIVE_IDS))
    if outside:
        raise SystemExit("ACTIVE15_SET_MISMATCH:" + ",".join(outside))

    active.sort(key=lambda r: (str(r["task"]), str(r["question_id"])))
    task_scores: dict[str, list[float]] = {t: [] for t in TASKS}
    compiler_status = Counter()
    route_counts = Counter()
    family_total = Counter()
    family_pass = Counter()
    full_score_rows = 0
    nonzero_rows = 0
    cases = []

    for row in active:
        prompt = str(row["turns"][0])
        solved = candidate.solve(prompt)
        status = str(solved.get("status"))
        compiler_status[status] += 1
        response = str(solved.get("response") or "")
        route_counts[str(solved.get("route") or "NONE")] += 1

        if response:
            score, followed = strict_score(row, response)
        else:
            ids = list(row["instruction_id_list"])
            score, followed = 0.0, [False] * len(ids)

        if score == 1.0:
            full_score_rows += 1
        if score > 0:
            nonzero_rows += 1
        task = str(row["task"])
        task_scores[task].append(score)

        ids = [str(x) for x in row["instruction_id_list"]]
        for iid, ok in zip(ids, followed):
            family_total[iid] += 1
            if ok:
                family_pass[iid] += 1

        cases.append({
            "question_id": row["question_id"],
            "task": task,
            "solver_status": status,
            "route": solved.get("route"),
            "score": score,
            "instruction_count": len(followed),
            "instruction_pass_count": sum(1 for x in followed if x),
            "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            "response_sha256": hashlib.sha256(response.encode("utf-8")).hexdigest() if response else None,
            "error": solved.get("error"),
        })

    task_percent = {
        task: 100.0 * sum(vals) / len(vals)
        for task, vals in task_scores.items()
    }
    exact_mean = sum(task_percent[t] for t in TASKS) / len(TASKS)
    passed = exact_mean >= PASS_FLOOR_PERCENT

    family_fraction = {
        iid: family_pass[iid] / family_total[iid]
        for iid in sorted(family_total)
    }

    receipt = {
        "schema": SCHEMA,
        "status": "PASS" if passed else "FAIL",
        "target_predicate": "LIVEBENCH_IF_GE_65_7",
        "selected_release": SELECTED_RELEASE,
        "public_population": {
            "count": len(active),
            "task_counts": dict(sorted(counts.items())),
            "legacy_ifeval_only": True,
            "active_instruction_id_count": len(hidden_ids),
            "active_instruction_ids": sorted(hidden_ids),
            "parquet_sha256": PARQUET_SHA256,
            "terminal_or_hidden_case_count": 0,
        },
        "candidate": {
            "kind": "DETERMINISTIC_VISIBLE_PROMPT_COMPILER_PLUS_JOINT_WITNESS",
            "model_dependency_count": 0,
            "network_dependency_at_runtime": False,
            "hidden_ids_or_kwargs_used_by_candidate": False,
            "compiler_status_counts": dict(sorted(compiler_status.items())),
            "route_counts": dict(sorted(route_counts.items())),
        },
        "scorer": {
            "livebench_commit": LIVEBENCH_COMMIT,
            "family": "LEGACY_IFEVAL_STRICT",
            "score_rule": "(ALL_TRUE_BINARY + TRUE_FRACTION)/2",
        },
        "results": {
            "task_percent": task_percent,
            "exact_four_task_mean_percent": exact_mean,
            "opus_5_5_public_equal_task_mean_floor_percent": PASS_FLOOR_PERCENT,
            "margin_percentage_points": exact_mean - PASS_FLOOR_PERCENT,
            "full_score_rows": full_score_rows,
            "nonzero_rows": nonzero_rows,
            "family_pass_fraction": family_fraction,
        },
        "cases": cases,
        "incremental_spend_usd": 0,
        "terminal_cases_consumed": 0,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "ownership_credit_delta": 0,
        "hard_nonclaims": [
            "PUBLIC_ROOT1_THRESHOLD_RESULT_IS_NOT_FULL_TERMINAL_GOAL_ACCEPTANCE",
            "NO_HIDDEN_OR_FRESH_TERMINAL_CASES_USED",
            "OTHER_OPUS55_CAPABILITY_FAMILIES_ARE_UNCHANGED",
        ],
    }
    Path("legacy15_joint_public_exact_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": receipt["status"],
        "task_percent": task_percent,
        "exact_four_task_mean_percent": exact_mean,
        "floor": PASS_FLOOR_PERCENT,
        "margin": exact_mean - PASS_FLOOR_PERCENT,
        "full_score_rows": full_score_rows,
        "compiler_status_counts": dict(compiler_status),
        "route_counts": dict(route_counts),
        "family_pass_fraction": family_fraction,
    }, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
