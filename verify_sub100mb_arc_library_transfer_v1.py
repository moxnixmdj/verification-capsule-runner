from __future__ import annotations

import inspect
import json
from pathlib import Path
import signal
import sys
from typing import Any

ROOT = Path(__file__).resolve().parent
SUBJECT = ROOT / "subject" / "sub100mb_arc_library_transfer_v1"
VENDOR = SUBJECT / "vendor"
TASKS = SUBJECT / "tasks"
sys.path.insert(0, str(VENDOR))

import solvers  # type: ignore  # exact MIT-licensed donor snapshot


def freeze_grid(value: Any):
    return tuple(tuple(int(cell) for cell in row) for row in value)


def thaw_grid(value: Any):
    return [list(row) for row in value]


def same_grid(a: Any, b: Any) -> bool:
    try:
        return freeze_grid(a) == freeze_grid(b)
    except Exception:
        return False


CALL_BUDGET_SECONDS = 0.1


class CandidateTimeout(TimeoutError):
    pass


def _timeout_handler(_signum, _frame):
    raise CandidateTimeout("CANDIDATE_CALL_BUDGET_EXCEEDED")


def bounded_call(fn, arg):
    previous = signal.signal(signal.SIGALRM, _timeout_handler)
    signal.setitimer(signal.ITIMER_REAL, CALL_BUDGET_SECONDS)
    try:
        return fn(arg)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def solver_functions():
    rows = []
    for name in sorted(dir(solvers)):
        if not name.startswith("solve_"):
            continue
        fn = getattr(solvers, name)
        if not callable(fn):
            continue
        try:
            source = inspect.getsource(fn)
        except Exception:
            source = name
        rows.append((len(source.encode("utf-8")), name, fn))
    return rows


def fits_training(fn, task: dict[str, Any]) -> bool:
    try:
        for pair in task["train"]:
            pred = bounded_call(fn, freeze_grid(pair["input"]))
            if not same_grid(pred, pair["output"]):
                return False
        return True
    except Exception:
        return False


def solves_test(fn, task: dict[str, Any]) -> bool:
    try:
        return all(
            same_grid(bounded_call(fn, freeze_grid(pair["input"])), pair["output"])
            for pair in task["test"]
        )
    except Exception:
        return False


def main() -> int:
    library = solver_functions()
    if len(library) != 400:
        raise SystemExit(f"EXPECTED_400_SOLVERS_GOT_{len(library)}")

    rows = []
    for path in sorted(TASKS.glob("*.json")):
        task = json.loads(path.read_text(encoding="utf-8"))
        candidates = [(size, name, fn) for size, name, fn in library if fits_training(fn, task)]
        candidates.sort(key=lambda row: (row[0], row[1]))

        selected = candidates[0] if candidates else None
        selected_solved = bool(selected and solves_test(selected[2], task))

        # Diagnostic only. Never used for candidate selection or claimed score.
        oracle_names = [name for _, name, fn in candidates if solves_test(fn, task)]

        rows.append({
            "task_id": path.stem,
            "training_fit_candidate_count": len(candidates),
            "selected_solver": None if selected is None else selected[1],
            "selected_solver_source_bytes": None if selected is None else selected[0],
            "selected_solver_test_solved": selected_solved,
            "diagnostic_any_training_fit_candidate_test_solved": bool(oracle_names),
            "diagnostic_oracle_solver_names": oracle_names,
        })

    result = {
        "schema": "PROJECT_BRAIN_SUB100MB_ARC_LIBRARY_TRANSFER_V1_PUBLIC_RUNNER_RESULT",
        "donor_solver_count": len(library),
        "task_count": len(rows),
        "selection_rule": "MINIMUM_SOURCE_BYTES_THEN_LEXICOGRAPHIC_NAME_AMONG_TRAINING_EXACT_CANDIDATES",
        "selected_exact_success_count": sum(1 for row in rows if row["selected_solver_test_solved"]),
        "training_expressible_task_count": sum(1 for row in rows if row["training_fit_candidate_count"] > 0),
        "diagnostic_oracle_any_success_count": sum(
            1 for row in rows if row["diagnostic_any_training_fit_candidate_test_solved"]
        ),
        "persistent_learned_state_bytes": 0,
        "frontier_model_calls": 0,
        "per_solver_call_budget_seconds": CALL_BUDGET_SECONDS,
        "rows": rows,
        "hard_nonclaims": [
            "ORACLE_DIAGNOSTIC_IS_NOT_A_VALID_SELECTION_SCORE",
            "NO_FULL_ARC_REPRESENTATIVENESS_CLAIM",
            "NO_FRONTIER_OR_UNKNOWN_DOMAIN_PARITY_CLAIM",
            "NO_ACCEPTANCE_OR_CAPABILITY_CREDIT",
        ],
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["task_count"] != 10:
        raise SystemExit("EXPECTED_10_TASKS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
