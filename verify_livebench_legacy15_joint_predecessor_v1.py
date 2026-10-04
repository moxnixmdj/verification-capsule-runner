#!/usr/bin/env python3
from __future__ import annotations

import collections
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_JOINT_PREDECESSOR_PUBLIC_VERIFICATION_V1"
SUBJECT_ROOT = Path(__file__).resolve().parent / "subject/livebench_legacy15_joint_predecessor_v1"
LIVEBENCH_ROOT = Path(os.environ["LIVEBENCH_ROOT"]).resolve()
PARQUET = Path(os.environ["LIVEBENCH_PREDECESSOR_PARQUET"]).resolve()
RECEIPT = Path("livebench_legacy15_joint_predecessor_receipt.json")

LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
PREDECESSOR_REVISION = "4f7ab12f0d47848da31de92bd7cc3d7d4acfe695"
PREDECESSOR_SHA256 = "57cbc3a738f7a95b234125965929247e7781ce6c5216bdea1d18548f4b10e98c"
PREDECESSOR_BYTES = 277319

SUBJECT_BLOBS = {
    "canonical/runtime/livebench_legacy15_joint_witness_v1.py": "8a7ee693072b662979683fa4b60de54ea6c60a10",
    "canonical/runtime/livebench_legacy_visible_constraint_compiler_v1.py": "e986035ff68b53c0dc7a7eb478f6e3d8882214aa",
    "canonical/runtime/livebench_legacy_visible_constraint_compiler_v2.py": "0e7519f4f2b7d40084effc83a5bef814ee7fd487",
    "canonical/runtime/livebench_frozen_active_legacy15_v1.py": "34440ee69322e9d519cbe656cb03c55683a8b9c6",
}

ACTIVE_IDS = frozenset({
    "keywords:existence",
    "keywords:forbidden_words",
    "length_constraints:number_paragraphs",
    "length_constraints:number_words",
    "length_constraints:number_sentences",
    "length_constraints:nth_paragraph_first_word",
    "detectable_content:postscript",
    "detectable_format:number_bullet_lists",
    "detectable_format:title",
    "detectable_format:multiple_sections",
    "detectable_format:json_format",
    "combination:repeat_prompt",
    "combination:two_responses",
    "startend:end_checker",
    "startend:quotation",
})

def git_blob(path: Path) -> str:
    data = path.read_bytes()
    h = hashlib.sha1()
    h.update(b"blob " + str(len(data)).encode("ascii") + b"\0" + data)
    return h.hexdigest()

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def nonnull_kwargs(raw) -> dict:
    out = {}
    for k, v in dict(raw or {}).items():
        if v is None:
            continue
        if hasattr(v, "tolist"):
            v = v.tolist()
        elif isinstance(v, tuple):
            v = list(v)
        out[str(k)] = v
    return out

def exact_score(registry, ids, kwargs_list, response: str):
    truths = []
    errors = []
    for iid, raw_kwargs in zip(ids, kwargs_list):
        try:
            checker = registry.INSTRUCTION_DICT[iid](iid)
            checker.build_description(**nonnull_kwargs(raw_kwargs))
            ok = bool(checker.check_following(response))
            truths.append(ok)
        except Exception as exc:
            truths.append(False)
            errors.append(type(exc).__name__)
    n = len(truths)
    followed = sum(truths)
    score = 0.5 * (1.0 if n and followed == n else 0.0) + 0.5 * (followed / n if n else 0.0)
    return score, followed == n and n > 0, followed, n, errors

def archetype(ids):
    s=set(ids)
    if "detectable_format:json_format" in s: return "JSON"
    if "combination:repeat_prompt" in s: return "REPEAT_PROMPT"
    if "combination:two_responses" in s: return "TWO_RESPONSES"
    if "length_constraints:nth_paragraph_first_word" in s: return "NTH_PARAGRAPH"
    if "length_constraints:number_paragraphs" in s: return "STAR_PARAGRAPH"
    if "length_constraints:number_sentences" in s: return "SENTENCE"
    return "PLAIN"

def main() -> int:
    for rel, expected in SUBJECT_BLOBS.items():
        got = git_blob(SUBJECT_ROOT / rel)
        if got != expected:
            raise SystemExit(f"FAIL_CLOSED:SUBJECT_BLOB_DRIFT:{rel}:{got}")

    head = subprocess.check_output(["git", "-C", str(LIVEBENCH_ROOT), "rev-parse", "HEAD"], text=True).strip()
    if head != LIVEBENCH_COMMIT:
        raise SystemExit("FAIL_CLOSED:LIVEBENCH_COMMIT_DRIFT")
    if PARQUET.stat().st_size != PREDECESSOR_BYTES or sha256(PARQUET) != PREDECESSOR_SHA256:
        raise SystemExit("FAIL_CLOSED:PREDECESSOR_DATASET_DRIFT")

    sys.path.insert(0, str(SUBJECT_ROOT))
    sys.path.insert(0, str(LIVEBENCH_ROOT / "livebench/if_runner"))
    subject = importlib.import_module("canonical.runtime.livebench_legacy15_joint_witness_v1")
    registry = importlib.import_module("instruction_following_eval.instructions_registry")

    import pyarrow.parquet as pq

    table = pq.read_table(
        PARQUET,
        columns=["turns", "instruction_id_list", "kwargs", "livebench_release_date"],
    )
    rows = table.to_pylist()
    if len(rows) != 200:
        raise SystemExit(f"FAIL_CLOSED:PREDECESSOR_ROW_COUNT:{len(rows)}")

    eligible = 0
    solver_candidates = 0
    full_pass = 0
    score_mass = 0.0
    instruction_instances = 0
    by_arch = collections.Counter()
    arch_full = collections.Counter()
    solver_fail = collections.Counter()
    checker_fail = collections.Counter()
    score_hist = collections.Counter()
    max_constraints = 0

    for row in rows:
        ids = [str(x) for x in (row.get("instruction_id_list") or [])]
        if not ids or not set(ids) <= ACTIVE_IDS:
            continue
        # The recovered LiveBench generator samples instruction IDs without replacement.
        if len(ids) != len(set(ids)):
            solver_fail["PREDECESSOR_DUPLICATE_ID_OUTSIDE_GENERATOR_CONTRACT"] += 1
            continue
        turns = list(row.get("turns") or [])
        kwargs_list = list(row.get("kwargs") or [])
        if len(turns) != 1 or len(kwargs_list) != len(ids):
            solver_fail["ROW_SHAPE_INVALID"] += 1
            continue

        eligible += 1
        instruction_instances += len(ids)
        max_constraints = max(max_constraints, len(ids))
        arch = archetype(ids)
        by_arch[arch] += 1

        out = subject.solve(str(turns[0]))
        if out.get("status") != "PASS_CANDIDATE_JOINT_LEGACY15_WITNESS":
            solver_fail[str(out.get("error") or "UNKNOWN_SOLVER_FAILURE")] += 1
            continue
        solver_candidates += 1
        response = str(out.get("response") or "")
        score, all_ok, followed, n, errors = exact_score(registry, ids, kwargs_list, response)
        score_mass += score
        score_hist[f"{score:.6f}"] += 1
        for err in errors:
            checker_fail["EXCEPTION:" + err] += 1
        if all_ok:
            full_pass += 1
            arch_full[arch] += 1
        else:
            checker_fail[f"PARTIAL_{followed}_OF_{n}"] += 1

    if eligible <= 0:
        status = "FAIL_CLOSED_NO_ACTIVE15_PREDECESSOR_ROWS"
    elif full_pass == eligible:
        status = "PASS_ALL_ELIGIBLE_PREDECESSOR_ROWS_FULL_SCORE"
    else:
        status = "FAIL_CLOSED_JOINT_WITNESS_PREDECESSOR_MISMATCH"

    receipt = {
        "schema": SCHEMA,
        "status": status,
        "bindings": {
            "subject_blobs": SUBJECT_BLOBS,
            "livebench_commit": LIVEBENCH_COMMIT,
            "predecessor_revision": PREDECESSOR_REVISION,
            "predecessor_sha256": PREDECESSOR_SHA256,
            "predecessor_bytes": PREDECESSOR_BYTES,
        },
        "population": {
            "predecessor_rows": len(rows),
            "active15_subset_eligible_rows": eligible,
            "eligible_instruction_instances": instruction_instances,
            "max_constraints_per_eligible_row": max_constraints,
            "eligible_rows_by_archetype": dict(sorted(by_arch.items())),
        },
        "result": {
            "solver_candidate_rows": solver_candidates,
            "full_score_rows": full_pass,
            "full_score_fraction": full_pass / eligible if eligible else 0.0,
            "score_mass": score_mass,
            "mean_score_on_eligible_rows": score_mass / eligible if eligible else 0.0,
            "full_score_rows_by_archetype": dict(sorted(arch_full.items())),
            "score_histogram": dict(sorted(score_hist.items())),
            "solver_failure_counts": dict(sorted(solver_fail.items())),
            "checker_failure_counts": dict(sorted(checker_fail.items())),
        },
        "firewall": {
            "active_terminal_rows_read": 0,
            "active_terminal_prompt_text_read": False,
            "active_terminal_kwargs_read": False,
            "predecessor_hidden_labels_used_only_by_verifier": True,
            "candidate_input_visible_prompt_only": True,
            "incremental_spend_usd": 0,
        },
        "hard_nonclaims": [
            "REMOVED_PREDECESSOR_IS_NONTERMINAL_AND_DOES_NOT_PROVE_ACTIVE_TERMINAL_SCORE",
            "NO_ACTIVE_TERMINAL_CASE_FREQUENCY_OR_COMBINATION_IS_INFERRED",
            "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
        ],
    }
    RECEIPT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))
    return 0 if status == "PASS_ALL_ELIGIBLE_PREDECESSOR_ROWS_FULL_SCORE" else 1

if __name__ == "__main__":
    raise SystemExit(main())
