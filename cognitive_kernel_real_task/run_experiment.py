#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import itertools
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


def load_task(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def find_candidate(task: dict[str, Any], contract_id: str, candidate_id: str):
    for contract in task["contracts"]:
        if contract["id"] != contract_id:
            continue
        for candidate in contract["candidates"]:
            if candidate["id"] == candidate_id:
                return contract, candidate
    raise KeyError((contract_id, candidate_id))


def load_function(code: str, fn_name: str):
    ns: dict[str, Any] = {}
    exec(compile(code, "<candidate>", "exec"), {}, ns)
    fn = ns.get(fn_name)
    if not callable(fn):
        raise RuntimeError(f"candidate did not define {fn_name}")
    return fn


def verify_candidate(contract_id: str, code: str) -> dict[str, Any]:
    if contract_id == "RETRY_CONTROL":
        fn = load_function(code, "should_retry")
        rows = list(itertools.product((False, True), (False, True), range(6)))
        oracle = lambda success, transient, attempts: (not success) and transient and attempts < 3
    elif contract_id == "LEASE_ADMISSION":
        fn = load_function(code, "may_launch")
        rows = list(itertools.product((False, True), repeat=4))
        oracle = lambda active, uncertain, hash_match, authorized: (
            authorized and hash_match and not active and not uncertain
        )
    elif contract_id == "PROMOTION_GATE":
        fn = load_function(code, "may_promote")
        rows = list(itertools.product((False, True), repeat=4))
        oracle = lambda independent, heldout, donor_deleted, contaminated: (
            independent and heldout and donor_deleted and not contaminated
        )
    elif contract_id == "SOURCE_ADMISSION":
        fn = load_function(code, "admit_source")
        rows = list(itertools.product((False, True), repeat=4))
        oracle = lambda authoritative, direct, stale, conflict: (
            authoritative and direct and not stale and not conflict
        )
    else:
        raise ValueError(f"unknown contract {contract_id}")

    started = time.perf_counter()
    for args in rows:
        observed = bool(fn(*args))
        expected = bool(oracle(*args))
        if observed != expected:
            return {
                "satisfies": False,
                "cases_checked": rows.index(args) + 1,
                "total_cases": len(rows),
                "first_mismatch": {
                    "args": list(args),
                    "observed": observed,
                    "expected": expected,
                },
                "verification_ms": (time.perf_counter() - started) * 1000.0,
            }
    return {
        "satisfies": True,
        "cases_checked": len(rows),
        "total_cases": len(rows),
        "first_mismatch": None,
        "verification_ms": (time.perf_counter() - started) * 1000.0,
    }


def worker_main(args) -> int:
    task = load_task(args.task)
    contract, candidate = find_candidate(task, args.contract, args.candidate)
    try:
        result = verify_candidate(contract["id"], candidate["code"])
    except Exception as exc:
        result = {
            "satisfies": False,
            "cases_checked": 0,
            "total_cases": None,
            "first_mismatch": {"exception": repr(exc)},
            "verification_ms": 0.0,
        }
    print(json.dumps(result))
    return 0


def run_verifier_subprocess(
    script: Path,
    task_path: Path,
    contract_id: str,
    candidate_id: str,
) -> tuple[bool, float, dict[str, Any]]:
    started = time.perf_counter()
    proc = subprocess.run(
        [
            sys.executable,
            str(script),
            "--worker",
            "--task",
            str(task_path),
            "--contract",
            contract_id,
            "--candidate",
            candidate_id,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    wall_ms = (time.perf_counter() - started) * 1000.0
    result = json.loads(proc.stdout)
    return bool(result["satisfies"]), wall_ms, result


def load_kernel(path: Path):
    spec = importlib.util.spec_from_file_location("cognitive_decision_kernel_real_task", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load kernel")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def experiment_main(args) -> int:
    task = load_task(args.task)
    kernel = load_kernel(args.kernel)
    threshold = float(task["kernel_threshold"])
    candidates = [
        (contract, candidate)
        for contract in task["contracts"]
        for candidate in contract["candidates"]
    ]

    # CASCADE FIRST. Audit truth for admitted cases is intentionally not computed yet.
    cascade_started = time.perf_counter()
    cascade_rows: list[dict[str, Any]] = []
    fallback_calls = 0
    for contract, candidate in candidates:
        state = {
            "signature": contract["signature"],
            "contract": contract["contract"],
            "candidate_implementation": candidate["code"],
        }
        decision = kernel.decide(
            endpoint=args.endpoint,
            model=args.model,
            state=state,
            question="Does this candidate implementation satisfy the contract exactly for all valid inputs?",
            threshold=threshold,
            timeout_s=args.timeout,
        )

        fallback = None
        fallback_wall_ms = 0.0
        if decision.status == "ADMIT":
            final_decision = bool(decision.decision)
        else:
            fallback_calls += 1
            final_decision, fallback_wall_ms, fallback = run_verifier_subprocess(
                Path(__file__).resolve(),
                args.task,
                contract["id"],
                candidate["id"],
            )

        cascade_rows.append({
            "contract_id": contract["id"],
            "candidate_id": candidate["id"],
            "kernel_status": decision.status,
            "kernel_decision": decision.decision,
            "probability_yes": decision.probability_yes,
            "confidence": decision.confidence,
            "kernel_latency_ms": decision.latency_ms,
            "fallback_called": fallback is not None,
            "fallback_wall_ms": fallback_wall_ms,
            "final_decision": final_decision,
        })
    cascade_wall_ms = (time.perf_counter() - cascade_started) * 1000.0

    # INDEPENDENT AUDIT / VERIFY-ALL BASELINE, after cascade is frozen.
    baseline_started = time.perf_counter()
    audit: dict[tuple[str, str], dict[str, Any]] = {}
    baseline_verifier_wall_ms = 0.0
    for contract, candidate in candidates:
        gold, wall_ms, detail = run_verifier_subprocess(
            Path(__file__).resolve(),
            args.task,
            contract["id"],
            candidate["id"],
        )
        baseline_verifier_wall_ms += wall_ms
        audit[(contract["id"], candidate["id"])] = {
            "gold": gold,
            "wall_ms": wall_ms,
            "detail": detail,
        }
    baseline_wall_ms = (time.perf_counter() - baseline_started) * 1000.0

    wrong_admissions = []
    wrong_terminal = []
    admitted = 0
    for row in cascade_rows:
        key = (row["contract_id"], row["candidate_id"])
        gold = audit[key]["gold"]
        row["audit_gold"] = gold
        row["terminal_correct"] = row["final_decision"] == gold
        if row["kernel_status"] == "ADMIT":
            admitted += 1
            if row["kernel_decision"] != gold:
                wrong_admissions.append(row)
        if not row["terminal_correct"]:
            wrong_terminal.append(row)

    total = len(cascade_rows)
    verifier_calls_saved = total - fallback_calls
    acceptance = task["acceptance"]
    passed = (
        len(wrong_terminal) == 0
        and len(wrong_admissions) <= int(acceptance["wrong_kernel_admissions_max"])
        and verifier_calls_saved >= int(acceptance["verifier_calls_saved_min"])
    )

    kernel_total_ms = sum(r["kernel_latency_ms"] for r in cascade_rows)
    fallback_total_ms = sum(r["fallback_wall_ms"] for r in cascade_rows)
    avg_kernel_ms = kernel_total_ms / total
    avg_baseline_verifier_ms = baseline_verifier_wall_ms / total

    result = {
        "schema": "PROJECT_BRAIN_COGNITIVE_KERNEL_FRESH_EXECUTABLE_TASK_RESULT_V1",
        "task_id": task["task_id"],
        "status": "PASS" if passed else "FAIL",
        "threshold": threshold,
        "candidates": total,
        "admitted": admitted,
        "escalated": fallback_calls,
        "coverage": admitted / total,
        "wrong_admissions": len(wrong_admissions),
        "wrong_terminal_decisions": len(wrong_terminal),
        "verifier_calls_baseline": total,
        "verifier_calls_cascade": fallback_calls,
        "verifier_calls_saved": verifier_calls_saved,
        "verifier_calls_saved_fraction": verifier_calls_saved / total,
        "cascade_wall_ms": cascade_wall_ms,
        "verify_all_baseline_wall_ms": baseline_wall_ms,
        "cascade_wall_clock_delta_ms": cascade_wall_ms - baseline_wall_ms,
        "cascade_wall_clock_speedup_ratio": (
            baseline_wall_ms / cascade_wall_ms if cascade_wall_ms else None
        ),
        "kernel_total_inference_ms": kernel_total_ms,
        "fallback_total_wall_ms": fallback_total_ms,
        "avg_kernel_inference_ms": avg_kernel_ms,
        "avg_verify_all_verifier_wall_ms": avg_baseline_verifier_ms,
        "break_even_verifier_ms_per_candidate_estimate": (
            avg_kernel_ms * total / max(verifier_calls_saved, 1)
        ),
        "rows": cascade_rows,
        "wrong_admission_rows": wrong_admissions,
        "wrong_terminal_rows": wrong_terminal,
        "capability_credit_delta": 0,
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in ("rows", "wrong_admission_rows", "wrong_terminal_rows")}, indent=2))
    if wrong_admissions:
        print("WRONG_ADMISSIONS")
        print(json.dumps(wrong_admissions, indent=2))
    return 0 if passed else 1


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--worker", action="store_true")
    p.add_argument("--task", required=True, type=Path)
    p.add_argument("--contract")
    p.add_argument("--candidate")
    p.add_argument("--kernel", type=Path)
    p.add_argument("--endpoint", default="http://127.0.0.1:8017/v1/systemone")
    p.add_argument("--model", default="jev-latest")
    p.add_argument("--timeout", type=float, default=30.0)
    p.add_argument("--output", type=Path)
    args = p.parse_args()

    if args.worker:
        if not args.contract or not args.candidate:
            p.error("--worker requires --contract and --candidate")
        return worker_main(args)
    if args.kernel is None or args.output is None:
        p.error("experiment mode requires --kernel and --output")
    return experiment_main(args)


if __name__ == "__main__":
    raise SystemExit(main())
