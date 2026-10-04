from __future__ import annotations

import copy
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SUBJECT = ROOT / "subject"
LIVEBENCH = ROOT / "livebench-src"
IFBENCH = ROOT / "ifbench-src"

EXPECTED_BLOBS = {
    "canonical/runtime/livebench_if_single_checker_solver_v1.py": "a1648ab011aedf2a631ca05bfc1ba28ce0923853",
    "canonical/runtime/livebench_ngram_reference_free_v1.py": "bcd4a4ede2e70e17e90a33416f3f4a564162f3ea",
    "canonical/runtime/livebench_prompt_only_repeat_compiler_v1.py": "332fbb1fac1cdee2632dc454b497376d319e2287",
}
EXPECTED_DATA_BLOB = "a8e343ed928d8b4e649b9dba651fed7757ccacc3"
EXPECTED_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
EXPECTED_IFBENCH_COMMIT = "1c40f0c10d9b5c5c2f10a175a28007ebb64f7f4d"


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def main() -> None:
    for rel, expected in EXPECTED_BLOBS.items():
        actual = git_blob_sha(SUBJECT / rel)
        if actual != expected:
            raise AssertionError(f"SUBJECT_BLOB_MISMATCH:{rel}:{actual}:{expected}")

    dataset = IFBENCH / "data" / "IFBench_test.jsonl"
    data_blob = git_blob_sha(dataset)
    if data_blob != EXPECTED_DATA_BLOB:
        raise AssertionError(f"DATASET_BLOB_MISMATCH:{data_blob}:{EXPECTED_DATA_BLOB}")

    sys.path.insert(0, str(SUBJECT))
    sys.path.insert(0, str(LIVEBENCH))

    from canonical.runtime.livebench_if_single_checker_solver_v1 import solve
    from livebench.if_runner.ifbench import evaluation_lib

    rows = [json.loads(line) for line in dataset.read_text(encoding="utf-8").splitlines() if line.strip()]
    singles = [row for row in rows if len(row.get("instruction_id_list") or []) == 1]

    family_total = Counter()
    family_pass = Counter()
    solve_status = Counter()
    failures = []
    passes = 0

    for row in singles:
        iid = row["instruction_id_list"][0]
        family_total[iid] += 1
        out = solve(row["prompt"])
        solve_status[out.get("status", "MISSING_STATUS")] += 1

        followed = False
        scorer_error = None
        if out.get("status") == "PASS_CANDIDATE_SINGLE_CHECKER_WITNESS":
            if out.get("checker_id") != iid:
                scorer_error = f"DETECTED_WRONG_FAMILY:{out.get('checker_id')}:{iid}"
            else:
                try:
                    inp = evaluation_lib.InputExample(
                        key=row["key"],
                        instruction_id_list=list(row["instruction_id_list"]),
                        prompt=row["prompt"],
                        kwargs=copy.deepcopy(row["kwargs"]),
                    )
                    scored = evaluation_lib.test_instruction_following_strict(inp, str(out.get("response") or ""))
                    followed = bool(scored.follow_all_instructions and scored.follow_instruction_list == [True])
                except Exception as exc:
                    scorer_error = f"{type(exc).__name__}:{exc}"

        if followed:
            passes += 1
            family_pass[iid] += 1
        else:
            failures.append({
                "key": row["key"],
                "instruction_id": iid,
                "solver_status": out.get("status"),
                "solver_error": out.get("error"),
                "recognized_checker_ids": out.get("recognized_checker_ids"),
                "response": out.get("response"),
                "scorer_error": scorer_error,
            })

    if len(rows) != 300:
        raise AssertionError(f"ROW_COUNT_CHANGED:{len(rows)}")
    if len(singles) != 256:
        raise AssertionError(f"SINGLE_COUNT_CHANGED:{len(singles)}")

    threshold_passes = 198
    result = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_SINGLE_CHECKER_PUBLIC_256_EXACT_REPLAY_V1",
        "status": "THRESHOLD_MET" if passes >= threshold_passes else "THRESHOLD_NOT_MET",
        "livebench_commit": EXPECTED_LIVEBENCH_COMMIT,
        "ifbench_commit": EXPECTED_IFBENCH_COMMIT,
        "dataset_blob": data_blob,
        "public_rows": len(rows),
        "single_checker_rows": len(singles),
        "single_checker_passes": passes,
        "single_checker_failures": len(singles) - passes,
        "minimum_single_passes_for_65_7_with_all_two_checker_rows_zero": threshold_passes,
        "implied_public_score_percent_with_all_two_checker_rows_zero": passes / len(rows) * 100.0,
        "margin_single_rows_vs_threshold": passes - threshold_passes,
        "family_total": dict(sorted(family_total.items())),
        "family_pass": dict(sorted(family_pass.items())),
        "solve_status": dict(sorted(solve_status.items())),
        "failures": failures,
        "terminal_cases_consumed": 0,
        "model_dependency_count": 0,
        "hard_nonclaims": [
            "PUBLIC_PINNED_POPULATION_ONLY",
            "NO_FROZEN_TERMINAL_SCOPE_EQUIVALENCE_CLAIM",
            "NO_SEMANTIC_TRANSFORMATION_CAPABILITY_CLAIM",
            "NO_ACCEPTANCE_OR_OWNERSHIP_CREDIT"
        ],
    }
    out_path = ROOT / "livebench_single_checker_public_256_result.json"
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "failures"}, indent=2, sort_keys=True))
    print("FAILURE_COUNT", len(failures))
    for item in failures[:80]:
        print("FAIL", json.dumps(item, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
