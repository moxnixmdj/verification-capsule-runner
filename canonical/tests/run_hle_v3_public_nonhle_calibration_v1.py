#!/usr/bin/env python3
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

DATASET = "ai-safety-institute/trivia_qa_verified"
CONFIG = "default"
SPLIT = "validation"
OFFSET = 0
SAMPLE_SIZE = 25
EXPECTED_TOTAL_ROWS = 3381
SCHEMA = "PROJECT_BRAIN_HLE_V3_PUBLIC_NONHLE_CALIBRATION_RUNNER_V1"
USER_AGENT = "ProjectBrain-HLE-V3-Calibration/1.0"


def _canon(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha_obj(obj: Any) -> str:
    return hashlib.sha256(_canon(obj)).hexdigest()


def _fetch_rows() -> list[dict[str, Any]]:
    query = urllib.parse.urlencode(
        {
            "dataset": DATASET,
            "config": CONFIG,
            "split": SPLIT,
            "offset": str(OFFSET),
            "length": str(SAMPLE_SIZE),
        }
    )
    url = "https://datasets-server.huggingface.co/rows?" + query
    last = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            if int(payload.get("num_rows_total") or -1) != EXPECTED_TOTAL_ROWS:
                raise RuntimeError("DATASET_TOTAL_ROWS_MISMATCH")
            rows = payload.get("rows")
            if not isinstance(rows, list) or len(rows) != SAMPLE_SIZE:
                raise RuntimeError("CALIBRATION_SAMPLE_SIZE_MISMATCH")
            out = []
            for expected_idx, item in enumerate(rows):
                if not isinstance(item, dict) or int(item.get("row_idx", -1)) != expected_idx:
                    raise RuntimeError("DATASET_CANONICAL_ORDER_MISMATCH")
                row = item.get("row")
                if not isinstance(row, dict):
                    raise RuntimeError("DATASET_ROW_INVALID")
                question = row.get("question")
                answer = row.get("answer")
                if not isinstance(question, str) or not question.strip():
                    raise RuntimeError("QUESTION_INVALID")
                if not isinstance(answer, str) or not answer.strip():
                    raise RuntimeError("ANSWER_INVALID")
                out.append(
                    {
                        "row_idx": expected_idx,
                        "source_index": row.get("index"),
                        "question": question,
                        "answer": answer,
                    }
                )
            return out
        except Exception as exc:
            last = exc
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError(type(last).__name__ if last else "FETCH_FAILED")


def prepare(path: Path) -> None:
    rows = _fetch_rows()
    questions = [
        {
            "row_idx": r["row_idx"],
            "task_id": f"triviaqa_validation_row_{r['row_idx']}",
            "question": r["question"],
            "question_sha256": hashlib.sha256(r["question"].encode("utf-8")).hexdigest(),
        }
        for r in rows
    ]
    doc = {
        "schema": SCHEMA,
        "phase": "QUESTIONS_ONLY_PREPARED",
        "dataset": DATASET,
        "split": SPLIT,
        "sample_rule": "FIRST_25_ROWS_IN_DATASET_SERVER_CANONICAL_ORDER",
        "rows": SAMPLE_SIZE,
        "questions_manifest_sha256": _sha_obj(questions),
        "questions": questions,
        "gold_written": False,
    }
    path.write_text(json.dumps(doc, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in doc.items() if k != "questions"}, sort_keys=True))


def _solve_one(item: dict[str, Any]) -> dict[str, Any]:
    from canonical.runtime.hle_native_research_solver_v3 import propose

    out = propose(
        task_id=str(item["task_id"]),
        question=str(item["question"]),
        has_nonempty_image_payload=False,
    )
    answer = out.get("candidate_answer")
    if answer is not None and not isinstance(answer, str):
        raise RuntimeError("CANDIDATE_TYPE_INVALID")
    answer = answer if isinstance(answer, str) else ""
    external_model_calls = int(out.get("external_model_calls", 0) or 0)
    external_reasoning_model_calls = int(out.get("external_reasoning_model_calls", 0) or 0)
    model_dependency_count = int(out.get("model_dependency_count", 0) or 0)
    if external_model_calls or external_reasoning_model_calls or model_dependency_count:
        raise RuntimeError("EXTERNAL_COGNITION_DETECTED")
    if out.get("gold_accessed") is not False:
        raise RuntimeError("GOLD_ACCOUNTING_NOT_FALSE")
    return {
        "row_idx": int(item["row_idx"]),
        "task_id": str(item["task_id"]),
        "question_sha256": str(item["question_sha256"]),
        "candidate_answer": answer,
        "candidate_answer_sha256": hashlib.sha256(answer.encode("utf-8")).hexdigest(),
        "attempted": bool(answer.strip()),
        "status": str(out.get("status") or ""),
        "independent_support_host_count": int(out.get("independent_support_host_count", 0) or 0),
        "external_model_calls": external_model_calls,
        "external_reasoning_model_calls": external_reasoning_model_calls,
        "model_dependency_count": model_dependency_count,
        "gold_accessed": False,
    }


def solve(questions_path: Path, commitments_path: Path, workers: int) -> None:
    doc = json.loads(questions_path.read_text(encoding="utf-8"))
    questions = doc.get("questions")
    if not isinstance(questions, list) or len(questions) != SAMPLE_SIZE:
        raise RuntimeError("QUESTIONS_FILE_INVALID")
    if _sha_obj(questions) != doc.get("questions_manifest_sha256"):
        raise RuntimeError("QUESTIONS_MANIFEST_HASH_MISMATCH")

    results: list[dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        future_map = {pool.submit(_solve_one, item): int(item["row_idx"]) for item in questions}
        for fut in concurrent.futures.as_completed(future_map):
            idx = future_map[fut]
            try:
                results.append(fut.result())
            except Exception as exc:
                item = questions[idx]
                results.append(
                    {
                        "row_idx": idx,
                        "task_id": str(item["task_id"]),
                        "question_sha256": str(item["question_sha256"]),
                        "candidate_answer": "",
                        "candidate_answer_sha256": hashlib.sha256(b"").hexdigest(),
                        "attempted": False,
                        "status": "SOLVER_EXCEPTION:" + type(exc).__name__,
                        "independent_support_host_count": 0,
                        "external_model_calls": 0,
                        "external_reasoning_model_calls": 0,
                        "model_dependency_count": 0,
                        "gold_accessed": False,
                    }
                )

    results.sort(key=lambda x: x["row_idx"])
    if [x["row_idx"] for x in results] != list(range(SAMPLE_SIZE)):
        raise RuntimeError("COMMITMENT_SLOT_SET_INVALID")
    if any(x["external_model_calls"] or x["external_reasoning_model_calls"] or x["model_dependency_count"] for x in results):
        raise RuntimeError("EXTERNAL_COGNITION_DETECTED_IN_COMMITMENTS")

    sealed = {
        "schema": SCHEMA,
        "phase": "COMMITMENTS_SEALED_BEFORE_GOLD_SCORE",
        "dataset": DATASET,
        "split": SPLIT,
        "questions_manifest_sha256": doc["questions_manifest_sha256"],
        "commitment_count": len(results),
        "commitments_manifest_sha256": _sha_obj(results),
        "commitments": results,
        "gold_loaded_by_solver_process": False,
        "external_model_calls_total": sum(x["external_model_calls"] for x in results),
        "external_reasoning_model_calls_total": sum(x["external_reasoning_model_calls"] for x in results),
        "model_dependency_count_total": sum(x["model_dependency_count"] for x in results),
    }
    commitments_path.write_text(json.dumps(sealed, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "phase": sealed["phase"],
                "commitment_count": sealed["commitment_count"],
                "commitments_manifest_sha256": sealed["commitments_manifest_sha256"],
                "attempted": sum(bool(x["attempted"]) for x in results),
                "external_model_calls_total": 0,
                "external_reasoning_model_calls_total": 0,
                "model_dependency_count_total": 0,
            },
            sort_keys=True,
        )
    )


_ARTICLE = re.compile(r"\b(a|an|the)\b", re.IGNORECASE)


def normalize_answer(value: str) -> str:
    x = unicodedata.normalize("NFKD", str(value or "")).lower()
    x = "".join(ch for ch in x if not unicodedata.category(ch).startswith("P"))
    x = _ARTICLE.sub(" ", x)
    return " ".join(x.split())


def score(questions_path: Path, commitments_path: Path, summary_path: Path) -> None:
    questions_doc = json.loads(questions_path.read_text(encoding="utf-8"))
    sealed = json.loads(commitments_path.read_text(encoding="utf-8"))
    commitments = sealed.get("commitments")
    if not isinstance(commitments, list) or len(commitments) != SAMPLE_SIZE:
        raise RuntimeError("SEALED_COMMITMENTS_INVALID")
    if _sha_obj(commitments) != sealed.get("commitments_manifest_sha256"):
        raise RuntimeError("COMMITMENTS_MANIFEST_HASH_MISMATCH")

    rows = _fetch_rows()
    by_idx = {int(r["row_idx"]): r for r in rows}
    questions = questions_doc.get("questions")
    for item in questions:
        idx = int(item["row_idx"])
        if hashlib.sha256(by_idx[idx]["question"].encode("utf-8")).hexdigest() != item["question_sha256"]:
            raise RuntimeError("QUESTION_REFETCH_MISMATCH")

    attempted = 0
    exact = 0
    per_slot = []
    for item in commitments:
        idx = int(item["row_idx"])
        candidate = str(item.get("candidate_answer") or "")
        gold = str(by_idx[idx]["answer"])
        hit = bool(candidate.strip()) and normalize_answer(candidate) == normalize_answer(gold)
        attempted += int(bool(candidate.strip()))
        exact += int(hit)
        per_slot.append(
            {
                "row_idx": idx,
                "task_id": item["task_id"],
                "candidate_answer_sha256": item["candidate_answer_sha256"],
                "attempted": bool(candidate.strip()),
                "normalized_exact": hit,
                "status": item.get("status"),
            }
        )

    attempt_rate = attempted / SAMPLE_SIZE
    exact_rate = exact / SAMPLE_SIZE
    gate = attempt_rate >= 0.25 and exact_rate >= 0.20
    summary = {
        "schema": "PROJECT_BRAIN_HLE_V3_PUBLIC_NONHLE_CALIBRATION_RESULT_V1",
        "dataset": DATASET,
        "split": SPLIT,
        "sample_rule": "FIRST_25_ROWS_IN_DATASET_SERVER_CANONICAL_ORDER",
        "sample_size": SAMPLE_SIZE,
        "questions_manifest_sha256": questions_doc["questions_manifest_sha256"],
        "commitments_manifest_sha256": sealed["commitments_manifest_sha256"],
        "attempted": attempted,
        "attempt_rate": attempt_rate,
        "normalized_exact": exact,
        "normalized_exact_rate": exact_rate,
        "promotion_gate": {
            "minimum_attempt_rate": 0.25,
            "minimum_normalized_exact_rate": 0.20,
            "passed": gate,
        },
        "external_model_calls_total": 0,
        "external_reasoning_model_calls_total": 0,
        "model_dependency_count_total": 0,
        "gold_hidden_from_solver_until_commitments_sealed": True,
        "hle_questions_consumed": 0,
        "hle_gold_consumed": 0,
        "hle_score_credit": 0,
        "per_slot_receipts": per_slot,
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "per_slot_receipts"}, sort_keys=True))


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    p_prepare = sub.add_parser("prepare")
    p_prepare.add_argument("--questions", required=True, type=Path)

    p_solve = sub.add_parser("solve")
    p_solve.add_argument("--questions", required=True, type=Path)
    p_solve.add_argument("--commitments", required=True, type=Path)
    p_solve.add_argument("--workers", type=int, default=5)

    p_score = sub.add_parser("score")
    p_score.add_argument("--questions", required=True, type=Path)
    p_score.add_argument("--commitments", required=True, type=Path)
    p_score.add_argument("--summary", required=True, type=Path)

    a = p.parse_args()
    if a.cmd == "prepare":
        prepare(a.questions)
    elif a.cmd == "solve":
        if not 1 <= a.workers <= 10:
            raise SystemExit("workers must be 1..10")
        solve(a.questions, a.commitments, a.workers)
    elif a.cmd == "score":
        score(a.questions, a.commitments, a.summary)
    else:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
