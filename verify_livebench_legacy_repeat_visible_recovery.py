#!/usr/bin/env python3
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import pathlib
import urllib.request

BRAIN_COMMIT = "910985ea9d78a4bce1a99ce34c83e7ec44822da7"
RUNTIME_PATH = "canonical/runtime/legacy_repeat_prompt_visible_recovery_v1.py"
RUNTIME_BLOB = "919314f7344acecaa1c83dc0b53b63514de06979"

GOOGLE_COMMIT = "e49bbfe381c9c0e564b937f1c4e163a2273c65cc"
GOOGLE_PATH = "instruction_following_eval/data/input_data.jsonl"
GOOGLE_BLOB = "cbe52f6eecf3986fdac745b4acba4da1408eb146"

LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
LEGACY_PATH = "livebench/if_runner/instruction_following_eval/instructions.py"
LEGACY_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"

REPEAT_ID = "combination:repeat_prompt"
EXPECTED_TOTAL = 541
EXPECTED_REPEAT = 41

def git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def fetch(url: str, path: pathlib.Path, expected_blob: str) -> bytes:
    urllib.request.urlretrieve(url, path)
    raw = path.read_bytes()
    got = git_blob_sha(raw)
    assert got == expected_blob, (path.name, got, expected_blob)
    return raw

root = pathlib.Path("repeat_visible_verify")
root.mkdir(exist_ok=True)

runtime_raw = fetch(
    f"https://raw.githubusercontent.com/moxnixmdj/brain/{BRAIN_COMMIT}/{RUNTIME_PATH}",
    root / "runtime.py",
    RUNTIME_BLOB,
)
google_raw = fetch(
    f"https://raw.githubusercontent.com/google-research/google-research/{GOOGLE_COMMIT}/{GOOGLE_PATH}",
    root / "input_data.jsonl",
    GOOGLE_BLOB,
)
legacy_raw = fetch(
    f"https://raw.githubusercontent.com/LiveBench/LiveBench/{LIVEBENCH_COMMIT}/{LEGACY_PATH}",
    root / "legacy_instructions.py",
    LEGACY_BLOB,
)

# Independently pin the exact frozen checker semantics without executing upstream code.
legacy_tree = ast.parse(legacy_raw.decode("utf-8"))
repeat_cls = next(
    n for n in legacy_tree.body
    if isinstance(n, ast.ClassDef) and n.name == "RepeatPromptThenAnswer"
)
check = next(
    n for n in repeat_cls.body
    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == "check_following"
)
check_src = ast.unparse(check)
assert ".strip().lower()" in check_src
assert ".startswith(" in check_src
assert "_prompt_to_repeat" in check_src

spec = importlib.util.spec_from_file_location("candidate", root / "runtime.py")
candidate = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(candidate)

rows = [json.loads(line) for line in google_raw.decode("utf-8").splitlines() if line.strip()]
assert len(rows) == EXPECTED_TOTAL, len(rows)

repeat_rows = 0
true_positive = 0
false_positive = 0
exact_hidden_match = 0
checker_witness_match = 0
false_positive_examples = []

for row_i, row in enumerate(rows):
    prompt = str(row["prompt"])
    ids = list(row.get("instruction_id_list") or [])
    kwargs = list(row.get("kwargs") or [])
    repeat_positions = [i for i, iid in enumerate(ids) if iid == REPEAT_ID]
    assert len(repeat_positions) <= 1, (row_i, repeat_positions)
    expected_repeat = bool(repeat_positions)

    try:
        recovered = candidate.recover_prompt_to_repeat(prompt)
        passed = True
    except candidate.RepeatPromptRecoveryBlocked:
        recovered = None
        passed = False

    if expected_repeat:
        repeat_rows += 1
        assert passed, ("FALSE_NEGATIVE", row_i, prompt)
        true_positive += 1
        pos = repeat_positions[0]
        assert pos < len(kwargs), ("KWARGS_POSITION_MISSING", row_i, pos, len(kwargs))
        expected = str((kwargs[pos] or {}).get("prompt_to_repeat") or "")
        assert expected, ("EXPECTED_PROMPT_TO_REPEAT_MISSING", row_i)
        got = str(recovered["prompt_to_repeat"])
        assert got.strip() == expected.strip(), ("HIDDEN_MISMATCH", row_i, got, expected)
        exact_hidden_match += 1

        witness = candidate.construct_checker_witness(prompt)
        answer = str(witness["answer"])
        assert answer.strip().lower().startswith(expected.strip().lower()), (
            "CHECKER_WITNESS_MISMATCH", row_i
        )
        checker_witness_match += 1
    elif passed:
        false_positive += 1
        if len(false_positive_examples) < 10:
            false_positive_examples.append({
                "row": row_i,
                "recovered": recovered["prompt_to_repeat"],
                "prompt_prefix": prompt[:240],
            })

assert repeat_rows == EXPECTED_REPEAT, repeat_rows
assert true_positive == EXPECTED_REPEAT, true_positive
assert exact_hidden_match == EXPECTED_REPEAT, exact_hidden_match
assert checker_witness_match == EXPECTED_REPEAT, checker_witness_match
assert false_positive == 0, ("FALSE_POSITIVES", false_positive, false_positive_examples)

print("LIVEBENCH_LEGACY_REPEAT_VISIBLE_RECOVERY_ADVERSARIAL_VERIFICATION=PASS")
print(f"public_rows={len(rows)}")
print(f"repeat_rows={repeat_rows}")
print(f"true_positive={true_positive}")
print(f"false_negative={repeat_rows-true_positive}")
print(f"false_positive={false_positive}")
print(f"true_negative={len(rows)-repeat_rows-false_positive}")
print(f"exact_hidden_match={exact_hidden_match}")
print(f"checker_witness_match={checker_witness_match}")
print("terminal_livebench_rows_used=0")
print("models_used=0")
print("incremental_spend_usd=0")
