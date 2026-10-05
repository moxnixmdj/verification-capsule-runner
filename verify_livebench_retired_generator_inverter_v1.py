#!/usr/bin/env python3
from __future__ import annotations

import collections
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

import pyarrow.parquet as pq

OLD_REV = "c42da7fb3b7647377f1e6aa48b3d52b774778fb4"
OLD_SHA256 = "d55a24b043daa8aba9acc62dc718f27ab354e9bad38ae1f0c545dac352f8bdd2"
OLD_BYTES = 276190
OLD_ROWS = 200
SUBJECT_PATH = Path("subject/livebench_legacy_visible_description_inverter_v1.py")
SUBJECT_BLOB = "f3374d84a1c60a3df7341946784a7e42b4e9ba1c"


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def load_subject():
    raw = SUBJECT_PATH.read_bytes()
    got = git_blob_sha(raw)
    assert got == SUBJECT_BLOB, (got, SUBJECT_BLOB)
    spec = importlib.util.spec_from_file_location("legacy_inverter_subject", SUBJECT_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def norm(v):
    if isinstance(v, str):
        return v.strip().lower()
    if isinstance(v, (list, tuple)):
        return [norm(x) for x in v]
    return v


def prompt_of(row: dict) -> str:
    turns = row.get("turns")
    if isinstance(turns, list) and turns:
        return str(turns[0])
    if row.get("prompt") is not None:
        return str(row["prompt"])
    raise AssertionError("NO_PROMPT_FIELD_IN_RETIRED_ROW")


def main() -> int:
    subject = load_subject()

    url = (
        "https://huggingface.co/datasets/livebench/instruction_following/resolve/"
        + OLD_REV
        + "/data/test-00000-of-00001.parquet?download=true"
    )
    path = Path("/tmp/livebench_instruction_following_retired_20240626.parquet")
    subprocess.run(
        ["curl", "--fail", "--location", "--retry", "3", "--silent", "--show-error",
         url, "-o", str(path)],
        check=True,
    )
    raw = path.read_bytes()
    assert len(raw) == OLD_BYTES, (len(raw), OLD_BYTES)
    assert hashlib.sha256(raw).hexdigest() == OLD_SHA256

    rows = pq.read_table(path).to_pylist()
    assert len(rows) == OLD_ROWS

    expected_instances = 0
    recognized_expected_instances = 0
    observed_instances = 0
    false_positive_instances = 0
    rows_exact_multiset = 0
    rows_all_expected_recognized = 0
    parser_errors = 0

    expected_family_counts = collections.Counter()
    recognized_family_counts = collections.Counter()
    false_positive_family_counts = collections.Counter()
    kwargs_compared = collections.Counter()
    kwargs_matched = collections.Counter()
    kwargs_mismatched = collections.Counter()

    for row in rows:
        prompt = prompt_of(row)
        expected_ids = [str(x) for x in (row.get("instruction_id_list") or [])]
        expected_kwargs = list(row.get("kwargs") or [])
        assert len(expected_kwargs) == len(expected_ids)

        expected = collections.Counter(expected_ids)
        expected_instances += sum(expected.values())
        expected_family_counts.update(expected_ids)

        try:
            result = subject.invert_legacy_descriptions(prompt)
            observed_ids = [str(x) for x in result.get("instruction_ids") or []]
            matches = list(result.get("matches") or [])
        except Exception:
            parser_errors += 1
            observed_ids = []
            matches = []

        observed = collections.Counter(observed_ids)
        observed_instances += sum(observed.values())

        overlap = expected & observed
        recognized_expected_instances += sum(overlap.values())
        recognized_family_counts.update(list(overlap.elements()))

        extras = observed - expected
        false_positive_instances += sum(extras.values())
        false_positive_family_counts.update(list(extras.elements()))

        if overlap == expected:
            rows_all_expected_recognized += 1
        if observed == expected:
            rows_exact_multiset += 1

        # Historical/public kwargs are used only to audit whether already-visible
        # values recovered by the subject agree. They never enter the parser.
        by_id = collections.defaultdict(list)
        for match in matches:
            by_id[str(match.get("instruction_id"))].append(match)
        used = collections.Counter()
        for idx, instruction_id in enumerate(expected_ids):
            occ = used[instruction_id]
            used[instruction_id] += 1
            candidates = by_id.get(instruction_id, [])
            if occ >= len(candidates):
                continue
            visible = dict(candidates[occ].get("kwargs_visible") or {})
            hidden = dict(expected_kwargs[idx] or {})
            for key, value in visible.items():
                if key not in hidden:
                    continue
                kwargs_compared[instruction_id] += 1
                if norm(value) == norm(hidden[key]):
                    kwargs_matched[instruction_id] += 1
                else:
                    kwargs_mismatched[instruction_id] += 1

    family_set = sorted(expected_family_counts)
    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_RETIRED_GENERATOR_INVERTER_AUDIT_V1",
        "status": "PASS__INDEPENDENT_HISTORICAL_DISTRIBUTION_MEASUREMENT_COMPLETE",
        "subject": {
            "git_blob_sha": SUBJECT_BLOB,
            "hidden_metadata_inputs": False,
            "scorer_feedback_inputs": False,
        },
        "historical_dataset": {
            "repository": "livebench/instruction_following",
            "revision": OLD_REV,
            "sha256": OLD_SHA256,
            "bytes": OLD_BYTES,
            "rows": OLD_ROWS,
            "published_before_current_2024_11_25_active_population": True,
        },
        "results": {
            "rows": len(rows),
            "expected_instruction_instances": expected_instances,
            "recognized_expected_instruction_instances": recognized_expected_instances,
            "instruction_instance_recall": (
                recognized_expected_instances / expected_instances if expected_instances else 1.0
            ),
            "observed_instruction_instances": observed_instances,
            "false_positive_instruction_instances": false_positive_instances,
            "rows_all_expected_recognized": rows_all_expected_recognized,
            "row_all_expected_recall": rows_all_expected_recognized / len(rows),
            "rows_exact_instruction_multiset": rows_exact_multiset,
            "row_exact_multiset_fraction": rows_exact_multiset / len(rows),
            "parser_errors": parser_errors,
            "actual_historical_instruction_family_count": len(family_set),
            "actual_historical_instruction_families": family_set,
            "expected_family_counts": dict(sorted(expected_family_counts.items())),
            "recognized_family_counts": dict(sorted(recognized_family_counts.items())),
            "false_positive_family_counts": dict(sorted(false_positive_family_counts.items())),
            "visible_kwarg_fields_compared_by_family": dict(sorted(kwargs_compared.items())),
            "visible_kwarg_fields_matched_by_family": dict(sorted(kwargs_matched.items())),
            "visible_kwarg_fields_mismatched_by_family": dict(sorted(kwargs_mismatched.items())),
            "visible_kwarg_total_compared": sum(kwargs_compared.values()),
            "visible_kwarg_total_matched": sum(kwargs_matched.values()),
            "visible_kwarg_total_mismatched": sum(kwargs_mismatched.values()),
        },
        "interpretation_rule": {
            "if_near_complete": (
                "SUPPORTS_SOURCE_TEMPLATE_GRAMMAR_AS_REPRESENTATIVE_OF_ACTUAL_RETIRED_"
                "LIVEBENCH_GENERATOR_OUTPUT__DOES_NOT_BY_ITSELF_PROVE_ACTIVE_2024_11_25_COVERAGE"
            ),
            "if_low": (
                "FALSIFIES_EXACT_TEMPLATE_INVERSION_AS_A_GENERATOR_DISTRIBUTION_SOLUTION_"
                "AND_REQUIRES_A_BROADER_PROMPT_ONLY_PARSER"
            ),
        },
        "hard_nonclaims": [
            "NO_CURRENT_ACTIVE_2024_11_25_LIVEBENCH_PROMPT_READ",
            "NO_CURRENT_ACTIVE_CASE_ID_OR_KWARG_READ",
            "NO_TERMINAL_SCORE_CLAIM",
            "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
            "NO_EXECUTION_OR_PROMOTION_AUTHORITY",
            "HISTORICAL_DISTRIBUTION_GENERALIZATION_IS_NOT_TERMINAL_POPULATION_EQUIVALENCE",
        ],
        "accounting": {
            "incremental_spend_usd": 0,
            "current_active_terminal_cases_consumed": 0,
            "acceptance_credit_delta": 0,
        },
    }
    Path("livebench_retired_generator_inverter_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
