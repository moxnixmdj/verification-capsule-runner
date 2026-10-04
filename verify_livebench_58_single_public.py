#!/usr/bin/env python3
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys

from canonical.runtime.livebench_if_single_checker_solver_v1 import detect, solve


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--livebench-root", required=True)
    ap.add_argument("--ifbench-jsonl", required=True)
    ns = ap.parse_args()

    lb = pathlib.Path(ns.livebench_root).resolve()
    data = pathlib.Path(ns.ifbench_jsonl).resolve()
    sys.path.insert(0, str(lb))

    from livebench.if_runner.ifbench import evaluation_lib

    rows = [json.loads(line) for line in data.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(rows) != 300:
        raise SystemExit(f"PUBLIC_ROW_COUNT_MISMATCH:{len(rows)}")

    set_match = 0
    single_total = 0
    single_solved = 0
    single_exact_scorer_pass = 0
    multi_total = 0
    multi_fail_closed = 0
    scoring_exceptions = 0

    by_family: dict[str, dict[str, int]] = collections.defaultdict(
        lambda: {"rows": 0, "detected": 0, "solved": 0, "scorer_pass": 0, "scorer_fail": 0}
    )
    failure_reasons = collections.Counter()
    failed_families = collections.Counter()

    for row in rows:
        actual = list(row.get("instruction_id_list") or [])
        expected = sorted(set(actual))
        hits = sorted(set(detect(str(row.get("prompt") or ""))))
        if expected == hits:
            set_match += 1

        if len(expected) == 1:
            single_total += 1
            family = expected[0]
            by_family[family]["rows"] += 1
            if hits == expected:
                by_family[family]["detected"] += 1

            out = solve(str(row.get("prompt") or ""))
            if out.get("status") != "PASS_CANDIDATE_SINGLE_CHECKER_WITNESS":
                failure_reasons["SOLVER_" + str(out.get("error") or out.get("status"))] += 1
                failed_families[family] += 1
                continue
            if out.get("checker_id") != family:
                failure_reasons["SOLVER_CHECKER_ID_MISMATCH"] += 1
                failed_families[family] += 1
                continue

            single_solved += 1
            by_family[family]["solved"] += 1
            try:
                inp = evaluation_lib.InputExample(
                    key=row.get("key"),
                    instruction_id_list=actual,
                    prompt=str(row.get("prompt") or ""),
                    kwargs=list(row.get("kwargs") or []),
                )
                result = evaluation_lib.test_instruction_following_strict(
                    inp, str(out.get("response") or "")
                )
                passed = bool(result.follow_all_instructions) and all(result.follow_instruction_list)
            except Exception as exc:
                scoring_exceptions += 1
                failure_reasons["SCORER_EXCEPTION_" + type(exc).__name__] += 1
                failed_families[family] += 1
                continue

            if passed:
                single_exact_scorer_pass += 1
                by_family[family]["scorer_pass"] += 1
            else:
                by_family[family]["scorer_fail"] += 1
                failed_families[family] += 1
                failure_reasons["EXACT_SCORER_FALSE"] += 1

        else:
            multi_total += 1
            out = solve(str(row.get("prompt") or ""))
            if (
                out.get("status") == "FAIL_CLOSED"
                and out.get("error") == "CHECKER_FAMILY_CARDINALITY_NOT_ONE"
                and sorted(set(out.get("recognized_checker_ids") or [])) == expected
            ):
                multi_fail_closed += 1
            else:
                failure_reasons["MULTI_NOT_EXACT_FAIL_CLOSED"] += 1

    summary = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_58_SINGLE_PUBLIC_EXACT_SCORER_MEASUREMENT_V1",
        "public_rows": len(rows),
        "public_instruction_family_count": len(by_family),
        "exact_instruction_set_detection": set_match,
        "single_checker_rows": single_total,
        "single_checker_solver_candidates": single_solved,
        "single_checker_exact_frozen_scorer_pass": single_exact_scorer_pass,
        "single_checker_exact_frozen_scorer_fail": single_total - single_exact_scorer_pass,
        "two_checker_rows": multi_total,
        "two_checker_exact_fail_closed": multi_fail_closed,
        "scoring_exception_count": scoring_exceptions,
        "failed_family_counts": dict(sorted(failed_families.items())),
        "failure_reason_counts": dict(sorted(failure_reasons.items())),
        "by_family": dict(sorted(by_family.items())),
        "terminal_case_content_read": False,
        "acceptance_credit": False,
    }
    print("LIVEBENCH_58_SINGLE_PUBLIC_RESULT=" + json.dumps(summary, sort_keys=True))
    pathlib.Path("livebench_58_single_public_receipt.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    # Measurement completion is success. The caller interprets scorer failures.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
