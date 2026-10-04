#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

import pyarrow.parquet as pq

SCHEMA = "PROJECT_BRAIN_QWEN38_4B_LIVEBENCH_PUBLIC_EXACT_20260625_V1"
SERVER = "http://127.0.0.1:8080/v1/chat/completions"
MODEL_ID = "brain-qwen38-4b-q4km"
MODEL_SHA256 = "dec96e8cf2e11b613bb46513dec485377f9ca5a351e71712ee0e244f287c6790"
LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
PARQUET_SHA256 = "a9bb97bbaf8788142c310bcb33d50e2f6f5df8cbd8b8c3db677816b06f0f4f25"
SELECTED_RELEASE = "2026-06-25"
TASKS = ("paraphrase", "simplify", "story_generation", "summarize")
PASS_FLOOR_PERCENT = 65.73775
BASE_SEED = 426200
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


def strip_reasoning(text: str) -> str:
    # Matches LiveBench's public ground-truth scorer behavior for <think> blocks.
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def call_model(prompt: str, seed: int) -> tuple[str, dict]:
    payload = {
        "model": "local-model",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.6,
        "top_p": 0.95,
        "top_k": 20,
        "max_tokens": 1536,
        "seed": seed,
        "stream": False,
    }
    req = urllib.request.Request(
        SERVER,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=900) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    choice = body["choices"][0]
    msg = choice.get("message") or {}
    text = str(msg.get("content") or "")
    return text, {
        "finish_reason": choice.get("finish_reason"),
        "usage": body.get("usage"),
        "reasoning_content_present": bool(msg.get("reasoning_content")),
    }


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
    # Exact LiveBench legacy IFEval score_results geometry.
    score = ((1.0 if all_followed else 0.0) + per_instruction) / 2.0
    return score, followed


def main() -> int:
    parquet = Path("/tmp/instruction_following.parquet")
    got = hashlib.sha256(parquet.read_bytes()).hexdigest()
    if got != PARQUET_SHA256:
        raise SystemExit(f"PARQUET_SHA_MISMATCH:{got}")

    table = pq.read_table(parquet)
    rows = table.to_pylist()
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

    counts = defaultdict(int)
    for row in active:
        counts[row["task"]] += 1
    expected = {task: 50 for task in TASKS}
    if dict(counts) != expected or len(active) != 200:
        raise SystemExit(f"ACTIVE_POPULATION_MISMATCH:{dict(counts)}:{len(active)}")
    if any(clean_date(r["livebench_release_date"]) >= "2025-11-25" for r in active):
        raise SystemExit("NONLEGACY_ROW_PRESENT")

    active.sort(key=lambda r: (str(r["task"]), str(r["question_id"])))
    task_scores: dict[str, list[float]] = {task: [] for task in TASKS}
    cases = []
    t0 = time.time()

    for idx, row in enumerate(active):
        prompt = str(row["turns"][0])
        raw, meta = call_model(prompt, BASE_SEED + idx)
        answer = strip_reasoning(raw)
        score, followed = strict_score(row, answer)
        task = str(row["task"])
        task_scores[task].append(score)
        rec = {
            "question_id": row["question_id"],
            "task": task,
            "score": score,
            "instruction_count": len(followed),
            "instruction_pass_count": sum(1 for x in followed if x),
            "all_instructions_followed": all(followed),
            "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            "response_sha256": hashlib.sha256(answer.encode("utf-8")).hexdigest(),
            **meta,
        }
        cases.append(rec)
        print(json.dumps({
            "progress": idx + 1,
            "total": len(active),
            "question_id": row["question_id"],
            "task": task,
            "score": score,
            "finish_reason": meta.get("finish_reason"),
        }, sort_keys=True), flush=True)

    task_percent = {
        task: 100.0 * sum(vals) / len(vals)
        for task, vals in task_scores.items()
    }
    exact_mean = sum(task_percent[t] for t in TASKS) / len(TASKS)
    passed = exact_mean >= PASS_FLOOR_PERCENT
    elapsed = time.time() - t0

    receipt = {
        "schema": SCHEMA,
        "status": "PASS" if passed else "FAIL",
        "target_predicate": "LIVEBENCH_IF_GE_65_7",
        "selected_release": SELECTED_RELEASE,
        "public_population": {
            "count": len(active),
            "task_counts": expected,
            "legacy_ifeval_only": True,
            "prompt_text_persisted_in_receipt": False,
            "parquet_sha256": PARQUET_SHA256,
        },
        "execution_subject": {
            "repository": "empero-ai/Qwen3.8-4B-Distill-GGUF",
            "revision": "391fc7d103e3942a408def3e4f51c2f85d464417",
            "file": "Qwen3.8-4B-Q4_K_M.gguf",
            "bytes": 2783446304,
            "sha256": MODEL_SHA256,
        },
        "runtime": {
            "repository": "ggml-org/llama.cpp",
            "commit": "0504396140d1c882f5f6ee34466a42db7ae90114",
            "threads": 4,
            "context_tokens": 4096,
            "parallel": 1,
        },
        "generation_policy": {
            "attempts_per_case": 1,
            "temperature": 0.6,
            "top_p": 0.95,
            "top_k": 20,
            "max_tokens": 1536,
            "fixed_seed_base": BASE_SEED,
            "adaptive_retry": False,
        },
        "scorer": {
            "livebench_repository_commit": LIVEBENCH_COMMIT,
            "family": "LEGACY_IFEVAL_STRICT",
            "score_rule": "MEAN_OF_PROMPT_LEVEL_ALL_FOLLOWED_AND_INSTRUCTION_LEVEL_FRACTION_DIVIDED_BY_TWO",
            "task_aggregation": "MEAN_SCORE_X_100_OVER_50_ACTIVE_ROWS_PER_TASK",
            "root1_aggregation": "ARITHMETIC_MEAN_OF_FOUR_TASK_PERCENTAGES",
        },
        "task_percent": task_percent,
        "exact_four_task_mean_percent": exact_mean,
        "opus_5_5_public_equal_task_mean_floor_percent": PASS_FLOOR_PERCENT,
        "margin_vs_floor_percentage_points": exact_mean - PASS_FLOOR_PERCENT,
        "elapsed_seconds": elapsed,
        "case_count": len(cases),
        "cases": cases,
        "terminal_cases_consumed": 0,
        "incremental_spend_usd": 0,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "ownership_credit_delta": 0,
        "hard_nonclaims": [
            "PUBLIC_ROOT1_SCORE_DOES_NOT_BY_ITSELF_GRANT_TERMINAL_ACCEPTANCE",
            "NO_HIDDEN_OR_FRESH_TERMINAL_CASES_USED",
            "NO_MULTIMODAL_OR_OTHER_OPUS55_FAMILY_CREDIT",
            "NO_DURABLE_BYTE_OWNERSHIP_UNTIL_SEPARATE_RELEASE_REASSEMBLY_PASS",
        ],
    }
    out = Path("qwen38_4b_livebench_public_exact_receipt.json")
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": receipt["status"],
        "task_percent": task_percent,
        "exact_four_task_mean_percent": exact_mean,
        "floor": PASS_FLOOR_PERCENT,
        "margin": receipt["margin_vs_floor_percentage_points"],
    }, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
