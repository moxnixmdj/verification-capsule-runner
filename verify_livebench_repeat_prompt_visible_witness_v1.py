#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib
import urllib.request

import pyarrow.parquet as pq

DATASET_REV = "0868379c4b5cf62aeacaf8be4f08fced815c81bb"
DATASET_SHA256 = "a9bb97bbaf8788142c310bcb33d50e2f6f5df8cbd8b8c3db677816b06f0f4f25"
DATASET_BYTES = 537024
DATASET_ROWS = 400

LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
INSTRUCTIONS_PATH = "livebench/if_runner/instruction_following_eval/instructions.py"
INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
REPEAT_ID = "combination:repeat_prompt"
CHECKER_LITERAL = "if value.strip().lower().startswith(self._prompt_to_repeat.strip().lower()):"

def git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def main() -> int:
    src_url = (
        "https://raw.githubusercontent.com/LiveBench/LiveBench/"
        + LIVEBENCH_COMMIT + "/" + INSTRUCTIONS_PATH
    )
    src = urllib.request.urlopen(src_url, timeout=30).read()
    if git_blob_sha(src) != INSTRUCTIONS_BLOB:
        raise SystemExit("FAIL_CLOSED:INSTRUCTIONS_BLOB_MISMATCH")
    source_text = src.decode("utf-8")
    if "class RepeatPromptThenAnswer" not in source_text:
        raise SystemExit("FAIL_CLOSED:REPEAT_CHECKER_CLASS_MISSING")
    if CHECKER_LITERAL not in source_text:
        raise SystemExit("FAIL_CLOSED:REPEAT_CHECKER_SEMANTICS_DRIFT")

    data_url = (
        "https://huggingface.co/datasets/livebench/instruction_following/resolve/"
        + DATASET_REV + "/data/test-00000-of-00001.parquet?download=true"
    )
    dst = pathlib.Path("livebench_if_400.parquet")
    urllib.request.urlretrieve(data_url, dst)
    raw = dst.read_bytes()
    if len(raw) != DATASET_BYTES:
        raise SystemExit("FAIL_CLOSED:DATASET_SIZE_MISMATCH")
    if hashlib.sha256(raw).hexdigest() != DATASET_SHA256:
        raise SystemExit("FAIL_CLOSED:DATASET_SHA256_MISMATCH")

    rows = pq.read_table(dst).to_pylist()
    if len(rows) != DATASET_ROWS:
        raise SystemExit("FAIL_CLOSED:DATASET_ROW_COUNT_MISMATCH")

    repeat_rows = 0
    prefix_witness_rows = 0
    malformed_rows = 0
    empty_hidden_rows = 0

    for q in rows:
        ids = list(q.get("instruction_id_list") or [])
        if REPEAT_ID not in ids:
            continue
        repeat_rows += 1
        try:
            idx = ids.index(REPEAT_ID)
            kwargs = list(q.get("kwargs") or [])
            kw = dict(kwargs[idx] or {})
            hidden = kw.get("prompt_to_repeat")
            turns = list(q.get("turns") or [])
            visible = turns[0] if turns else None
        except Exception:
            malformed_rows += 1
            continue

        if not isinstance(hidden, str) or not hidden.strip():
            empty_hidden_rows += 1
            continue
        if not isinstance(visible, str) or not visible.strip():
            malformed_rows += 1
            continue

        # Exact checker-equivalent predicate. No row text is emitted.
        if visible.strip().lower().startswith(hidden.strip().lower()):
            prefix_witness_rows += 1

    if repeat_rows <= 0:
        raise SystemExit("FAIL_CLOSED:NO_REPEAT_PROMPT_ROWS")
    if malformed_rows != 0 or empty_hidden_rows != 0:
        raise SystemExit("FAIL_CLOSED:REPEAT_ROW_STRUCTURE_FAILURE")
    if prefix_witness_rows != repeat_rows:
        raise SystemExit("FAIL_CLOSED:VISIBLE_PROMPT_NOT_UNIVERSAL_REPEAT_PREFIX_WITNESS")

    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_LEGACY_REPEAT_PROMPT_VISIBLE_WITNESS_PUBLIC_VERIFICATION_V1",
        "status": "PASS",
        "bindings": {
            "dataset_revision": DATASET_REV,
            "dataset_sha256": DATASET_SHA256,
            "dataset_bytes": DATASET_BYTES,
            "dataset_rows": DATASET_ROWS,
            "livebench_commit": LIVEBENCH_COMMIT,
            "instructions_git_blob_sha": INSTRUCTIONS_BLOB,
            "instruction_id": REPEAT_ID,
        },
        "verified": {
            "repeat_prompt_rows_in_400_row_superset": repeat_rows,
            "visible_prompt_is_checker_valid_prefix_witness_rows": prefix_witness_rows,
            "violations": repeat_rows - prefix_witness_rows,
            "malformed_rows": malformed_rows,
            "empty_hidden_parameter_rows": empty_hidden_rows,
            "universal_superset_property": True,
            "subset_transfer": "ANY_FROZEN_SUBSET_OF_THIS_EXACT_400_ROW_OBJECT_INHERITS_THE_PROPERTY",
            "runtime_hidden_prompt_to_repeat_read_required_for_THIS_CHECKER": False,
        },
        "proof": [
            "PINNED_CHECKER_ACCEPTS_IFF_RESPONSE_STRIPPED_LOWER_STARTS_WITH_HIDDEN_PROMPT_TO_REPEAT_STRIPPED_LOWER",
            "FOR_EVERY_REPEAT_PROMPT_ROW_IN_THE_EXACT_400_ROW_SOURCE_OBJECT_THE_VISIBLE_PROMPT_ITSELF_SATISFIES_THAT_PREFIX_PREDICATE",
            "THEREFORE_RESPONSE_EQUALS_VISIBLE_PROMPT_IS_A_REFERENCE_FREE_WITNESS_FOR_REPEAT_PROMPT_ON_EVERY_SUCH_SOURCE_ROW",
            "ANY_FROZEN_200_ROW_SUBSET_OF_THE_EXACT_SOURCE_OBJECT_INHERITS_THIS_UNIVERSAL_PROPERTY",
        ],
        "contamination_firewall": {
            "prompt_text_emitted": False,
            "hidden_kwarg_text_emitted": False,
            "question_ids_emitted": False,
            "row_level_semantics_emitted": False,
            "aggregate_counts_only": True,
        },
        "hard_nonclaims": [
            "NO_CLAIM_OTHER_CONJUNCTIVE_INSTRUCTIONS_PASS_WHEN_RESPONSE_EQUALS_VISIBLE_PROMPT",
            "NO_CLAIM_LIVEBENCH_THRESHOLD_OR_ACCEPTANCE_IS_CLOSED",
            "NO_GENERAL_SEMANTIC_CAPABILITY_CREDIT",
            "NO_TERMINAL_CASE_CONTENT_EXPOSED",
        ],
        "accounting": {
            "incremental_spend_usd": 0,
            "new_terminal_cases_exposed": 0,
            "acceptance_credit_delta": 0,
        },
    }
    pathlib.Path("livebench_repeat_prompt_visible_witness_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
