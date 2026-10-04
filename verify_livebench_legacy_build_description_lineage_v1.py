#!/usr/bin/env python3
from __future__ import annotations

import collections
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY_BUILD_DESCRIPTION_LINEAGE_PUBLIC_RUNNER_V1"
LIVEBENCH_SCORER_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
LIVEBENCH_LEGACY_INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
LIVEBENCH_LEGACY_REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
LIVEBENCH_GENERATOR_COMMIT = "262cfc141e65fa9cf80015b9630b54bed2346f43"
LIVEBENCH_GENERATOR_BLOB = "6ff390d6885cf90f88d9d36959735cb327613edc"
DATASET_REV = "0868379c4b5cf62aeacaf8be4f08fced815c81bb"
DATASET_SHA256 = "a9bb97bbaf8788142c310bcb33d50e2f6f5df8cbd8b8c3db677816b06f0f4f25"
DATASET_BYTES = 537024
SELECTED_RELEASE = "2026-06-25"
DISPATCH_BOUNDARY = "2025-11-25"
EXPECTED_ACTIVE = 200
EXPECTED_TASK_COUNTS = {
    "paraphrase": 50,
    "simplify": 50,
    "story_generation": 50,
    "summarize": 50,
}

ROOT = Path(__file__).resolve().parent
LIVEBENCH_ROOT = Path(os.environ["LIVEBENCH_ROOT"]).resolve()
PARQUET = Path(os.environ["LIVEBENCH_PARQUET"]).resolve()
RECEIPT = ROOT / "livebench_legacy_build_description_lineage_receipt.json"

def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    h = hashlib.sha1()
    h.update(f"blob {len(data)}\0".encode("ascii"))
    h.update(data)
    return h.hexdigest()

def git_head(path: Path) -> str:
    return subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()

assert git_head(LIVEBENCH_ROOT) == LIVEBENCH_SCORER_COMMIT
assert git_blob_sha(LIVEBENCH_ROOT / "livebench/if_runner/instruction_following_eval/instructions.py") == LIVEBENCH_LEGACY_INSTRUCTIONS_BLOB
assert git_blob_sha(LIVEBENCH_ROOT / "livebench/if_runner/instruction_following_eval/instructions_registry.py") == LIVEBENCH_LEGACY_REGISTRY_BLOB
assert PARQUET.stat().st_size == DATASET_BYTES
assert hashlib.sha256(PARQUET.read_bytes()).hexdigest() == DATASET_SHA256

# Bind the deleted original generator primitive without executing it or making
# it an authority source by itself. The actual proof below is the 200-row
# byte-exact round trip against the frozen dataset.
generator = subprocess.check_output(
    ["git", "-C", str(LIVEBENCH_ROOT), "show", f"{LIVEBENCH_GENERATOR_COMMIT}:livebench/if_runner/live_data.py"],
    text=True,
)
gen_raw = generator.encode("utf-8")
gen_blob = hashlib.sha1(f"blob {len(gen_raw)}\0".encode("ascii") + gen_raw).hexdigest()
assert gen_blob == LIVEBENCH_GENERATOR_BLOB
for needle in (
    "instruction_text = build_instruction.build_description()",
    'instruction_combined_text += " "+instruction_text',
    "generated_prompt = prompt.format(extracted_text, task_prompt, constraint_text)",
):
    assert needle in generator

import pyarrow.parquet as pq  # noqa: E402

# Import the exact frozen legacy registry. No candidate code is imported.
sys.path.insert(0, str(LIVEBENCH_ROOT / "livebench/if_runner"))
from instruction_following_eval import instructions_registry  # noqa: E402

columns = [
    "task",
    "turns",
    "instruction_id_list",
    "kwargs",
    "task_prompt",
    "livebench_release_date",
    "livebench_removal_date",
]
table = pq.read_table(PARQUET, columns=columns)
rows = table.to_pylist()
assert len(rows) == 400

def date_string(v) -> str:
    if hasattr(v, "strftime"):
        return v.strftime("%Y-%m-%d")
    return str(v)

active = []
for row in rows:
    rd = date_string(row["livebench_release_date"])
    rem = row["livebench_removal_date"] or ""
    if rd <= SELECTED_RELEASE and (rem == "" or rem > SELECTED_RELEASE):
        active.append((row, rd))

assert len(active) == EXPECTED_ACTIVE
task_counts = collections.Counter(row["task"] for row, _ in active)
assert dict(task_counts) == EXPECTED_TASK_COUNTS
assert all(rd < DISPATCH_BOUNDARY for _, rd in active)

exact_suffix_matches = 0
normalized_suffix_matches = 0
registry_only_rows = 0
roundtrip_failures = collections.Counter()
instruction_instance_count = 0
active_type_set = set()
constraint_count_hist = collections.Counter()

for row, _rd in active:
    turns = row["turns"]
    ids = list(row["instruction_id_list"] or [])
    kwargs_list = list(row["kwargs"] or [])
    constraint_count_hist[len(ids)] += 1

    if not isinstance(turns, list) or len(turns) != 1 or not isinstance(turns[0], str):
        roundtrip_failures["TURN_SHAPE"] += 1
        continue
    prompt = turns[0]
    if len(ids) != len(kwargs_list) or not ids:
        roundtrip_failures["ID_KWARGS_SHAPE"] += 1
        continue
    if any(iid not in instructions_registry.INSTRUCTION_DICT for iid in ids):
        roundtrip_failures["ID_NOT_IN_FROZEN_REGISTRY"] += 1
        continue

    registry_only_rows += 1
    descriptions = []
    row_ok = True
    for iid, raw_kwargs in zip(ids, kwargs_list):
        instruction_instance_count += 1
        active_type_set.add(iid)
        if not isinstance(raw_kwargs, dict):
            roundtrip_failures["KWARGS_NOT_DICT"] += 1
            row_ok = False
            break
        kwargs = {k: v for k, v in raw_kwargs.items() if v is not None}
        try:
            inst = instructions_registry.INSTRUCTION_DICT[iid](iid)
            desc = inst.build_description(**kwargs)
        except Exception as exc:
            roundtrip_failures["BUILD_DESCRIPTION_EXCEPTION:" + type(exc).__name__] += 1
            row_ok = False
            break
        if not isinstance(desc, str) or not desc:
            roundtrip_failures["BUILD_DESCRIPTION_EMPTY"] += 1
            row_ok = False
            break
        descriptions.append(desc)

    if not row_ok:
        continue

    generated_suffix = "".join(" " + d for d in descriptions)
    if prompt.endswith(generated_suffix):
        exact_suffix_matches += 1
        normalized_suffix_matches += 1
        continue

    # Diagnostic only. It never authorizes a pass and never emits prompt text.
    norm_prompt = " ".join(prompt.split())
    norm_suffix = " ".join(generated_suffix.split())
    if norm_prompt.endswith(norm_suffix):
        normalized_suffix_matches += 1
        roundtrip_failures["EXACT_SUFFIX_FAIL_WHITESPACE_ONLY"] += 1
    else:
        roundtrip_failures["VISIBLE_SUFFIX_NOT_CURRENT_BUILD_DESCRIPTION"] += 1

# Strong pass requires exact byte suffix identity for every active row.
status = (
    "PASS_ALL_200_ACTIVE_ROWS_EXACT_BUILD_DESCRIPTION_SUFFIX"
    if exact_suffix_matches == EXPECTED_ACTIVE
    else "FAIL_NOT_ALL_ACTIVE_ROWS_EXACT_BUILD_DESCRIPTION_SUFFIX"
)

receipt = {
    "schema": SCHEMA,
    "status": status,
    "pinned_sources": {
        "livebench_scorer_commit": LIVEBENCH_SCORER_COMMIT,
        "legacy_instructions_git_blob_sha": LIVEBENCH_LEGACY_INSTRUCTIONS_BLOB,
        "legacy_registry_git_blob_sha": LIVEBENCH_LEGACY_REGISTRY_BLOB,
        "deleted_generator_commit": LIVEBENCH_GENERATOR_COMMIT,
        "deleted_generator_git_blob_sha": LIVEBENCH_GENERATOR_BLOB,
        "dataset_revision": DATASET_REV,
        "dataset_parquet_sha256": DATASET_SHA256,
        "dataset_parquet_bytes": DATASET_BYTES,
    },
    "population": {
        "all_rows": len(rows),
        "active_rows": len(active),
        "task_counts": dict(sorted(task_counts.items())),
        "legacy_dispatch_rows": sum(1 for _, rd in active if rd < DISPATCH_BOUNDARY),
        "modern_dispatch_rows": sum(1 for _, rd in active if rd >= DISPATCH_BOUNDARY),
        "constraint_count_histogram": {str(k): v for k, v in sorted(constraint_count_hist.items())},
        "active_registered_instruction_type_count": len(active_type_set),
        "instruction_instance_count": instruction_instance_count,
    },
    "roundtrip": {
        "registry_only_rows": registry_only_rows,
        "exact_build_description_suffix_matches": exact_suffix_matches,
        "normalized_build_description_suffix_matches": normalized_suffix_matches,
        "exact_match_required": EXPECTED_ACTIVE,
        "failure_counts": dict(sorted(roundtrip_failures.items())),
    },
    "consequence_if_pass": {
        "visible_constraint_grammar": "EXACT_PINNED_LEGACY_BUILD_DESCRIPTION_OUTPUTS_ON_ALL_200_ACTIVE_ROWS",
        "paraphrase_complete_classic_ifeval_parser_required_for_this_frozen_target": False,
        "terminal_instruction_id_list_runtime_dependency_for_visible_grammar": "DELETABLE_AFTER_A_PROMPT_ONLY_INVERTER_IS_PROVED_COMPLETE_OVER_THE_BUILD_DESCRIPTION_SURFACE",
        "next_cut": "COMPOSE_SOURCE_TEMPLATE_INVERTER_WITH_EXACT_LEGACY_WITNESS_SYNTHESIS_AND_VERIFY_CONSTRUCTED_RESPONSES_ON_PUBLIC_SYNTHETIC_BUILD_DESCRIPTION_CASES_BEFORE_ANY_TERMINAL_CANDIDATE_EXECUTION",
    },
    "firewall": {
        "candidate_code_imported": False,
        "candidate_response_generated": False,
        "terminal_score_read": False,
        "terminal_prompt_text_read_inside_isolated_verifier": True,
        "terminal_prompt_text_emitted": False,
        "terminal_question_ids_read": False,
        "per_row_instruction_ids_emitted": False,
        "per_row_kwargs_emitted": False,
        "only_aggregate_roundtrip_result_emitted": True,
        "incremental_spend_usd": 0,
    },
    "hard_nonclaims": [
        "DATASET_PROMPT_TEXT_IS_READ_INSIDE_THE_ISOLATED_VERIFIER_BUT_NEVER_EMITTED",
        "THIS_DOES_NOT_EXECUTE_OR_SCORE_ANY_SUCCESSOR",
        "THIS_DOES_NOT_PROVE_ANY CONSTRUCTED RESPONSE PASSES",
        "THIS_DOES_NOT_GRANT_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
        "THE_DELETED_GENERATOR_SOURCE_IS SUPPORTING_PROVENANCE_ONLY; THE 200_ROW_EXACT_ROUNDTRIP_IS_THE_LOAD_BEARING TEST",
    ],
}
RECEIPT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print("RESULT_JSON=" + json.dumps(receipt, sort_keys=True))
if status != "PASS_ALL_200_ACTIVE_ROWS_EXACT_BUILD_DESCRIPTION_SUFFIX":
    raise SystemExit(1)
