#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import sys
import types
import urllib.request

SUBJECT = pathlib.Path("subject/legacy_repeat_prompt_visible_recovery_v1.py")
EXPECTED_SUBJECT_BLOB = "7b2c56bf9da9df5ba3dd916719fcf1e991cf5dc9"
IFEVAL_URL = (
    "https://raw.githubusercontent.com/google-research/google-research/"
    "e49bbfe381c9c0e564b937f1c4e163a2273c65cc/"
    "instruction_following_eval/data/input_data.jsonl"
)
IFEVAL_BLOB = "cbe52f6eecf3986fdac745b4acba4da1408eb146"
CHECKER_URL = (
    "https://raw.githubusercontent.com/LiveBench/LiveBench/"
    "8f8e5c381a16e3f24257776edd53471fe86f8091/"
    "livebench/if_runner/instruction_following_eval/instructions.py"
)
CHECKER_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "project-brain-independent-verifier"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def load_subject():
    raw = SUBJECT.read_bytes()
    assert git_blob_sha(raw) == EXPECTED_SUBJECT_BLOB
    # The exact canonical module also imports the unrelated ratio-overlap
    # constructor. Stub only that dependency so this verifier exercises the
    # exact repeat-prompt implementation bytes without importing extra Brain code.
    canonical = types.ModuleType("canonical")
    runtime = types.ModuleType("canonical.runtime")
    ratio = types.ModuleType(
        "canonical.runtime.livebench_ngram_whitespace_invariant_compiler_v1"
    )
    ratio.construct_from_pinned_public_prompt = lambda prompt: (_ for _ in ()).throw(
        AssertionError("UNRELATED_RATIO_ROUTE_MUST_NOT_RUN")
    )
    sys.modules["canonical"] = canonical
    sys.modules["canonical.runtime"] = runtime
    sys.modules[
        "canonical.runtime.livebench_ngram_whitespace_invariant_compiler_v1"
    ] = ratio

    spec = importlib.util.spec_from_file_location("subject_repeat", SUBJECT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    subject = load_subject()

    checker_raw = fetch(CHECKER_URL)
    assert git_blob_sha(checker_raw) == CHECKER_BLOB
    checker = checker_raw.decode("utf-8")
    start = checker.index("class RepeatPromptThenAnswer(Instruction):")
    end = checker.find("\nclass ", start + 1)
    section = checker[start:] if end < 0 else checker[start:end]
    assert (
        "value.strip().lower().startswith(self._prompt_to_repeat.strip().lower())"
        in section
    )

    data_raw = fetch(IFEVAL_URL)
    assert git_blob_sha(data_raw) == IFEVAL_BLOB
    rows = [json.loads(x) for x in data_raw.decode("utf-8").splitlines() if x.strip()]
    assert len(rows) == 541

    repeat_rows = exact_recoveries = exact_checker_passes = 0
    prefix_layout = suffix_layout = 0
    failures = []

    for row in rows:
        ids = list(row.get("instruction_id_list") or [])
        if "combination:repeat_prompt" not in ids:
            continue
        repeat_rows += 1
        idx = ids.index("combination:repeat_prompt")
        hidden = str((row.get("kwargs") or [])[idx].get("prompt_to_repeat") or "")
        prompt = str(row.get("prompt") or "")
        assert hidden

        pos = prompt.lower().find(hidden.lower())
        assert pos >= 0
        if pos == 0:
            prefix_layout += 1
        elif pos + len(hidden) == len(prompt):
            suffix_layout += 1
        else:
            failures.append({"key": row.get("key"), "reason": "HIDDEN_NOT_EDGE_ALIGNED"})
            continue

        recovered = subject.recover_legacy_repeat_prompt(prompt)
        got = str(recovered["prompt_to_repeat"])
        if got.strip().lower() != hidden.strip().lower():
            failures.append({"key": row.get("key"), "reason": "RECOVERY_MISMATCH"})
            continue
        exact_recoveries += 1

        # Exact legacy checker condition, independently applied with public kwargs.
        witness = got + "\nAnswer."
        if witness.strip().lower().startswith(hidden.strip().lower()):
            exact_checker_passes += 1
        else:
            failures.append({"key": row.get("key"), "reason": "EXACT_CHECKER_FAIL"})

        assert recovered["hidden_prompt_to_repeat_required"] is False
        assert recovered["source"] == "VISIBLE_PROMPT_ONLY"

    assert repeat_rows == 41, repeat_rows
    assert prefix_layout == 33, prefix_layout
    assert suffix_layout == 8, suffix_layout
    assert exact_recoveries == 41, (exact_recoveries, failures)
    assert exact_checker_passes == 41, (exact_checker_passes, failures)
    assert not failures, failures

    receipt = {
        "schema": "PROJECT_BRAIN_CANONICAL_LEGACY_REPEAT_PROMPT_RECOVERY_INDEPENDENT_VERIFICATION_V1",
        "status": "PASS__CANONICAL_BLOB__41_OF_41_EXACT_RECOVERY_AND_CHECKER_PASS",
        "subject_git_blob_sha": EXPECTED_SUBJECT_BLOB,
        "ifeval_git_blob_sha": IFEVAL_BLOB,
        "legacy_checker_git_blob_sha": CHECKER_BLOB,
        "public_rows_total": len(rows),
        "repeat_prompt_rows": repeat_rows,
        "exact_recoveries": exact_recoveries,
        "exact_checker_passes": exact_checker_passes,
        "request_prefix_layout_rows": prefix_layout,
        "request_suffix_layout_rows": suffix_layout,
        "terminal_livebench_cases_read": 0,
        "hidden_runtime_kwargs_used_by_subject": False,
        "incremental_spend_usd": 0,
        "acceptance_credit": False,
    }
    pathlib.Path("legacy_repeat_prompt_visible_recovery_v1_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
