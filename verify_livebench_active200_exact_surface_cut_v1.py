#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
import subprocess
from collections import Counter
from fractions import Fraction
from pathlib import Path

import pyarrow.parquet as pq

HF_REVISION = "0868379c4b5cf62aeacaf8be4f08fced815c81bb"
HF_URL = (
    "https://huggingface.co/datasets/livebench/instruction_following/resolve/"
    + HF_REVISION
    + "/data/test-00000-of-00001.parquet"
)
HF_SHA256 = "a9bb97bbaf8788142c310bcb33d50e2f6f5df8cbd8b8c3db677816b06f0f4f25"
HF_BYTES = 537024
TARGET_RELEASE = "2026-06-25"
TARGET_PERCENT = Fraction("65.7")
COMPARATOR_EXACT_PERCENT = Fraction("65.73775")

LEGACY_25 = {
    "keywords:existence",
    "keywords:frequency",
    "keywords:forbidden_words",
    "keywords:letter_frequency",
    "language:response_language",
    "length_constraints:number_sentences",
    "length_constraints:number_paragraphs",
    "length_constraints:number_words",
    "length_constraints:nth_paragraph_first_word",
    "detectable_content:number_placeholders",
    "detectable_content:postscript",
    "detectable_format:number_bullet_lists",
    "detectable_format:constrained_response",
    "detectable_format:number_highlighted_sections",
    "detectable_format:multiple_sections",
    "detectable_format:json_format",
    "detectable_format:title",
    "combination:two_responses",
    "combination:repeat_prompt",
    "startend:end_checker",
    "change_case:capital_word_frequency",
    "change_case:english_capital",
    "change_case:english_lowercase",
    "punctuation:no_comma",
    "startend:quotation",
}

EXPECTED_TASKS = {
    "paraphrase": 50,
    "simplify": 50,
    "story_generation": 50,
    "summarize": 50,
}


def as_date(value) -> str:
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return str(value or "")


def fetch_exact_parquet(path: Path) -> None:
    subprocess.run(
        [
            "curl",
            "--fail",
            "--location",
            "--retry",
            "3",
            "--silent",
            "--show-error",
            HF_URL,
            "-o",
            str(path),
        ],
        check=True,
    )
    raw = path.read_bytes()
    assert len(raw) == HF_BYTES, len(raw)
    assert hashlib.sha256(raw).hexdigest() == HF_SHA256


def score_scaled(rows_masks: list[int], arities: list[int], selected_mask: int, L: int) -> int:
    total = 0
    for row_mask, k in zip(rows_masks, arities):
        g = (row_mask & selected_mask).bit_count()
        # Exact score x (2L): partial term contributes L*g/k.
        total += L * g // k
        if g == k:
            # Full-all-checkers bonus contributes another L.
            total += L
    return total


def threshold_met(scaled: int, N: int, L: int, percent: Fraction) -> bool:
    # percent = 100 * (scaled / (2L)) / N.
    return 100 * scaled * percent.denominator >= percent.numerator * (2 * L * N)


def percent_fraction(scaled: int, N: int, L: int) -> Fraction:
    return Fraction(100 * scaled, 2 * L * N)


def main() -> int:
    parquet = Path("/tmp/livebench_instruction_following_exact.parquet")
    fetch_exact_parquet(parquet)

    # Metadata only. Intentionally never request turns, prompt, task_prompt, kwargs,
    # reference answers, model responses, or scorer feedback.
    columns = [
        "question_id",
        "task",
        "category",
        "livebench_release_date",
        "livebench_removal_date",
        "instruction_id_list",
    ]
    rows = pq.read_table(parquet, columns=columns).to_pylist()
    assert len(rows) == 400
    assert len({row["question_id"] for row in rows}) == 400
    assert all(row["category"] == "instruction_following" for row in rows)

    active = []
    for row in rows:
        removal = as_date(row["livebench_removal_date"])
        if removal == "" or removal > TARGET_RELEASE:
            active.append(row)
    assert len(active) == 200

    task_counts = Counter(row["task"] for row in active)
    assert task_counts == EXPECTED_TASKS, task_counts

    active_ids = []
    arities = []
    type_frequency = Counter()
    for index, row in enumerate(active):
        ids = tuple(str(x) for x in (row["instruction_id_list"] or []))
        assert ids, ("EMPTY_IDS", index)
        assert len(set(ids)) == len(ids), ("DUPLICATE_IDS", index, ids)
        assert set(ids) <= LEGACY_25, ("NON_LEGACY_ID", index, set(ids) - LEGACY_25)
        active_ids.append(ids)
        arities.append(len(ids))
        type_frequency.update(ids)

    types = sorted({x for ids in active_ids for x in ids})
    assert set(types) <= LEGACY_25
    assert len(types) <= 25
    type_index = {name: i for i, name in enumerate(types)}
    row_masks = [
        sum(1 << type_index[name] for name in ids)
        for ids in active_ids
    ]
    assert all(mask.bit_count() == k for mask, k in zip(row_masks, arities))

    L = 1
    for k in arities:
        L = math.lcm(L, k)

    input_path = Path("/tmp/livebench_cut_input.txt")
    with input_path.open("w", encoding="utf-8") as f:
        f.write(f"{len(types)} {len(active)} {L}\n")
        for mask, k in zip(row_masks, arities):
            f.write(f"{mask} {k}\n")

    binary = Path("/tmp/livebench_exact_cut")
    subprocess.run(
        [
            "g++",
            "-O3",
            "-march=x86-64",
            "-std=c++20",
            "verify_livebench_active200_exact_surface_cut_v1.cpp",
            "-o",
            str(binary),
        ],
        check=True,
    )
    result = subprocess.run(
        [str(binary)],
        stdin=input_path.open("rb"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
        timeout=420,
        text=True,
    )

    best: dict[int, tuple[int, int]] = {}
    parsed_T = parsed_N = parsed_L = None
    for line in result.stdout.splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "T":
            parsed_T = int(parts[1])
        elif parts[0] == "N":
            parsed_N = int(parts[1])
        elif parts[0] == "L":
            parsed_L = int(parts[1])
        elif parts[0] == "BEST":
            best[int(parts[1])] = (int(parts[2]), int(parts[3]))

    assert parsed_T == len(types)
    assert parsed_N == len(active)
    assert parsed_L == L
    assert set(best) == set(range(len(types) + 1))

    min_k = next(k for k in range(len(types) + 1) if threshold_met(best[k][0], len(active), L, TARGET_PERCENT))
    min_exact_k = next(
        k for k in range(len(types) + 1)
        if threshold_met(best[k][0], len(active), L, COMPARATOR_EXACT_PERCENT)
    )

    best_scaled, best_mask = best[min_k]
    exact_recomputed = score_scaled(row_masks, arities, best_mask, L)
    assert exact_recomputed == best_scaled

    lower = None
    if min_k > 0:
        lower_scaled, lower_mask = best[min_k - 1]
        assert score_scaled(row_masks, arities, lower_mask, L) == lower_scaled
        assert not threshold_met(lower_scaled, len(active), L, TARGET_PERCENT)
        lower = {
            "checker_type_count": min_k - 1,
            "scaled_score_2L": lower_scaled,
            "best_score_percent_fraction": str(percent_fraction(lower_scaled, len(active), L)),
            "best_score_percent": float(percent_fraction(lower_scaled, len(active), L)),
            "checker_types": [types[i] for i in range(len(types)) if (lower_mask >> i) & 1],
        }

    selected = [types[i] for i in range(len(types)) if (best_mask >> i) & 1]
    arity_counts = Counter(arities)

    # Independent algebraic decomposition check.
    linear = Fraction(0)
    fully_covered = 0
    for ids in active_ids:
        g = sum(name in selected for name in ids)
        linear += Fraction(g, 2 * len(ids))
        if g == len(ids):
            fully_covered += 1
    independent_total = linear + Fraction(fully_covered, 2)
    assert independent_total == Fraction(best_scaled, 2 * L)

    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_ACTIVE200_EXACT_MINIMUM_CHECKER_SURFACE_CUT_INDEPENDENT_VERIFICATION_V1",
        "status": "PASS",
        "pinned_dataset": {
            "hf_revision": HF_REVISION,
            "parquet_sha256": HF_SHA256,
            "parquet_bytes": HF_BYTES,
            "rows_total": 400,
            "active_2026_06_25_rows": 200,
            "active_task_counts": dict(sorted(task_counts.items())),
        },
        "metadata_firewall": {
            "columns_read": columns,
            "prompt_or_turn_columns_read": False,
            "kwargs_read": False,
            "response_or_scorer_feedback_read": False,
        },
        "active_checker_geometry": {
            "legacy_registered_types": 25,
            "active_checker_type_count": len(types),
            "active_checker_types": types,
            "active_type_frequency": dict(sorted(type_frequency.items())),
            "arity_distribution": {str(k): v for k, v in sorted(arity_counts.items())},
            "lcm_arity": L,
        },
        "exact_optimization": {
            "formula": "SUM_SELECTED_TYPE_PARTIAL_MASS_PLUS_HALF_FULLY_COVERED_ROW_COUNT",
            "enumerated_subsets": 1 << len(types),
            "minimum_types_for_65_7": min_k,
            "selected_checker_types_for_65_7": selected,
            "best_scaled_score_2L": best_scaled,
            "best_score_percent_fraction": str(percent_fraction(best_scaled, len(active), L)),
            "best_score_percent": float(percent_fraction(best_scaled, len(active), L)),
            "fully_covered_rows": fully_covered,
            "partial_mass_score_points": str(linear),
            "best_with_one_fewer": lower,
            "minimum_types_for_exact_opus55_65_73775": min_exact_k,
            "proof": "EXHAUSTIVE_GRAY_CODE_ENUMERATION_OF_ALL_CHECKER_TYPE_SUBSETS__BEST_SCORE_RECORDED_BY_CARDINALITY__PYTHON_EXACT_RECOMPUTATION_OF_WINNER_AND_LOWER_NEIGHBOR",
        },
        "hard_nonclaims": [
            "NO_BRAIN_RESPONSE_GENERATION",
            "NO_BRAIN_LIVEBENCH_SCORE_CLAIM",
            "NO_ACCEPTANCE_OR_FAMILY_CREDIT",
            "NO_PROMPT_TURN_KWARGS_RESPONSE_OR_SCORER_FEEDBACK_CONTENT_READ",
            "CHECKER_TYPE_COVERAGE_IS_A_SCORE_MASS_TARGET_NOT_PROOF_THE_SELECTED_CHECKERS_ARE_ALREADY_SOLVED",
        ],
        "accounting": {
            "incremental_spend_usd": 0,
            "new_terminal_prompt_cases_exposed": 0,
            "fresh_reality_authority": False,
        },
    }
    Path("livebench_active200_exact_surface_cut_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
