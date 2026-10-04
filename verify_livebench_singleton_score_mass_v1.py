#!/usr/bin/env python3
from __future__ import annotations

import collections
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import types

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_SINGLETON_SCORE_MASS_PUBLIC_RUNNER_V1"
BRAIN_SOLVER_BLOB = "b74d986fae033ac94827c5f1eb2db655a99ae4cc"
BRAIN_NGRAM_BLOB = "bcd4a4ede2e70e17e90a33416f3f4a564162f3ea"
LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
LIVEBENCH_INSTRUCTIONS_BLOB = "02b2dfeb50f036b89bec3df34522c73f756d8f44"
IFBENCH_COMMIT = "1c40f0c10d9b5c5c2f10a175a28007ebb64f7f4d"
IFBENCH_DATA_BLOB = "a8e343ed928d8b4e649b9dba651fed7757ccacc3"
PUBLIC_THRESHOLD_PERCENT = 65.7
EXPECTED_ROWS = 300
EXPECTED_SINGLETONS = 256
EXPECTED_PAIRS = 44
MIN_SINGLETON_PASSES_FOR_THRESHOLD = math.ceil(PUBLIC_THRESHOLD_PERCENT * EXPECTED_ROWS / 100.0)

REPO_ROOT = Path(__file__).resolve().parent
SUBJECT_ROOT = REPO_ROOT / "subject" / "livebench_singleton_score_mass_v1"
LIVEBENCH_ROOT = Path(os.environ["LIVEBENCH_ROOT"]).resolve()
IFBENCH_ROOT = Path(os.environ["IFBENCH_ROOT"]).resolve()
RECEIPT = REPO_ROOT / "livebench_singleton_score_mass_receipt.json"

def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    h = hashlib.sha1()
    h.update(f"blob {len(data)}\0".encode("ascii"))
    h.update(data)
    return h.hexdigest()

def git_head(path: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        text=True,
    ).strip()

subject_solver = SUBJECT_ROOT / "canonical/runtime/livebench_if_single_checker_solver_v1.py"
subject_ngram = SUBJECT_ROOT / "canonical/runtime/livebench_ngram_reference_free_v1.py"
assert git_blob_sha(subject_solver) == BRAIN_SOLVER_BLOB
assert git_blob_sha(subject_ngram) == BRAIN_NGRAM_BLOB
assert git_head(LIVEBENCH_ROOT) == LIVEBENCH_COMMIT
assert git_head(IFBENCH_ROOT) == IFBENCH_COMMIT
assert git_blob_sha(LIVEBENCH_ROOT / "livebench/if_runner/ifbench/instructions.py") == LIVEBENCH_INSTRUCTIONS_BLOB
assert git_blob_sha(IFBENCH_ROOT / "data/IFBench_test.jsonl") == IFBENCH_DATA_BLOB

# The exact frozen checker package imports spaCy at module bootstrap, but the
# 58 active IFBench checker implementations do not need it for this evaluation.
# Fail if the dead bootstrap path attempts a real use.
spacy = types.ModuleType("spacy")
spacy.util = types.SimpleNamespace(is_package=lambda _name: True)
spacy_cli = types.ModuleType("spacy.cli")
spacy_cli.download = lambda _name: (_ for _ in ()).throw(
    RuntimeError("dead spacy download path invoked")
)
sys.modules["spacy"] = spacy
sys.modules["spacy.cli"] = spacy_cli

sys.path.insert(0, str(SUBJECT_ROOT))
sys.path.insert(0, str(LIVEBENCH_ROOT))

from canonical.runtime import livebench_if_single_checker_solver_v1 as solver  # noqa: E402
from livebench.if_runner.ifbench.instructions_registry import INSTRUCTION_DICT  # noqa: E402

rows = [
    json.loads(line)
    for line in (IFBENCH_ROOT / "data/IFBench_test.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip()
]
count_hist = collections.Counter(len(row.get("instruction_id_list") or []) for row in rows)
assert len(rows) == EXPECTED_ROWS, len(rows)
assert count_hist == collections.Counter({1: EXPECTED_SINGLETONS, 2: EXPECTED_PAIRS}), count_hist

singleton_total = 0
solver_pass_candidates = 0
checker_passed = 0
failure_counts = collections.Counter()
family_totals = collections.Counter()
family_passes = collections.Counter()
failure_examples = []

for row in rows:
    ids = list(row.get("instruction_id_list") or [])
    if len(ids) != 1:
        continue
    singleton_total += 1
    iid = str(ids[0])
    family_totals[iid] += 1
    if iid not in INSTRUCTION_DICT:
        failure_counts["CHECKER_ID_MISSING_FROM_FROZEN_REGISTRY"] += 1
        continue

    try:
        result = solver.solve(str(row.get("prompt") or ""))
    except Exception as exc:
        failure_counts["SOLVER_EXCEPTION:" + type(exc).__name__] += 1
        if len(failure_examples) < 20:
            failure_examples.append({"family": iid, "stage": "solver", "error": type(exc).__name__ + ":" + str(exc)[:240]})
        continue

    if result.get("status") != "PASS_CANDIDATE_SINGLE_CHECKER_WITNESS":
        failure_counts["SOLVER_FAIL_CLOSED:" + str(result.get("error") or "UNKNOWN")] += 1
        if len(failure_examples) < 20:
            failure_examples.append({
                "family": iid,
                "stage": "solver",
                "status": result.get("status"),
                "error": result.get("error"),
                "recognized_checker_ids": result.get("recognized_checker_ids"),
            })
        continue

    solver_pass_candidates += 1
    if result.get("checker_id") != iid:
        failure_counts["WRONG_CHECKER_ID"] += 1
        if len(failure_examples) < 20:
            failure_examples.append({"family": iid, "stage": "identity", "observed": result.get("checker_id")})
        continue

    kwargs_list = list(row.get("kwargs") or [])
    if len(kwargs_list) != 1 or not isinstance(kwargs_list[0], dict):
        failure_counts["PUBLIC_KWARGS_SHAPE_INVALID"] += 1
        continue

    try:
        checker = INSTRUCTION_DICT[iid](iid)
        checker.build_description(**kwargs_list[0])
        ok = bool(checker.check_following(str(result.get("response") or "")))
    except Exception as exc:
        failure_counts["CHECKER_EXCEPTION:" + type(exc).__name__] += 1
        if len(failure_examples) < 20:
            failure_examples.append({"family": iid, "stage": "checker", "error": type(exc).__name__ + ":" + str(exc)[:240]})
        continue

    if ok:
        checker_passed += 1
        family_passes[iid] += 1
    else:
        failure_counts["EXACT_CHECKER_REJECTED"] += 1
        if len(failure_examples) < 20:
            failure_examples.append({"family": iid, "stage": "checker", "error": "EXACT_CHECKER_REJECTED"})

# Every pair is forced to zero in this lower bound. On a singleton row, an exact
# checker pass implies all=1 and fraction=1, so the LiveBench formula contributes
# exactly 1.0 for that row. Therefore this is a literal score lower bound on the
# pinned public 300-row population, not an extrapolation to hidden terminal rows.
public_score_lower_bound_percent = 100.0 * checker_passed / EXPECTED_ROWS
threshold_crossed = checker_passed >= MIN_SINGLETON_PASSES_FOR_THRESHOLD

family_rows = []
for iid in sorted(family_totals):
    total = family_totals[iid]
    passed = family_passes[iid]
    family_rows.append({
        "checker_id": iid,
        "singleton_rows": total,
        "exact_checker_passes": passed,
        "exact_checker_failures": total - passed,
    })

receipt = {
    "schema": SCHEMA,
    "status": "PASS_PUBLIC_SINGLETON_LOWER_BOUND_ABOVE_65_7" if threshold_crossed else "FAIL_PUBLIC_SINGLETON_LOWER_BOUND_BELOW_65_7",
    "subject": {
        "solver_git_blob_sha": BRAIN_SOLVER_BLOB,
        "ngram_dependency_git_blob_sha": BRAIN_NGRAM_BLOB,
    },
    "pinned_public_sources": {
        "livebench_commit": LIVEBENCH_COMMIT,
        "livebench_instructions_git_blob_sha": LIVEBENCH_INSTRUCTIONS_BLOB,
        "ifbench_commit": IFBENCH_COMMIT,
        "ifbench_data_git_blob_sha": IFBENCH_DATA_BLOB,
    },
    "population": {
        "rows": len(rows),
        "singleton_rows": singleton_total,
        "pair_rows_forced_to_zero": EXPECTED_PAIRS,
        "constraint_count_histogram": {str(k): v for k, v in sorted(count_hist.items())},
    },
    "result": {
        "solver_pass_candidates": solver_pass_candidates,
        "exact_checker_passed_singletons": checker_passed,
        "minimum_singleton_passes_required_for_65_7_of_300": MIN_SINGLETON_PASSES_FOR_THRESHOLD,
        "public_score_lower_bound_percent_with_all_pairs_zero": public_score_lower_bound_percent,
        "public_threshold_percent": PUBLIC_THRESHOLD_PERCENT,
        "threshold_crossed": threshold_crossed,
        "family_rows": family_rows,
        "failure_counts": dict(sorted(failure_counts.items())),
        "failure_examples_without_prompt_or_response_text": failure_examples,
    },
    "firewall": {
        "terminal_case_content_read": False,
        "terminal_case_ids_read": False,
        "public_ifbench_only": True,
        "model_dependency_count": 0,
        "paid_external_api_used": False,
        "incremental_spend_usd": 0,
    },
    "hard_nonclaims": [
        "NO_FROZEN_TERMINAL_POPULATION_EQUIVALENCE",
        "NO_FROZEN_TERMINAL_SCORE_CLAIM",
        "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
        "NO_PAIR_COMPOSITION_CREDIT",
    ],
}
RECEIPT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print("RESULT_JSON=" + json.dumps(receipt, sort_keys=True))
if not threshold_crossed:
    raise SystemExit(1)
