#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import urllib.request

LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
RUNNER_COMMIT = "d8e6edd61fb1fbeedd856aa31cc202348e52529c"
RUNNER_BLOB = "05d71d3d06ebac9b5d74eb31b137141e6b8797c2"
LEGACY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
MODERN_BLOB = "adfed4832877566e62970257b50c6fa32c302fb2"
TARGET = "af4eeddebf27394eb689d2049f2f8104ae081ebafe237258bdc1a992e96f598d"

ACTIVE = (
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
)
EXCLUDED = (
    "keywords:frequency",
    "keywords:letter_frequency",
    "language:response_language",
    "detectable_content:number_placeholders",
    "detectable_format:constrained_response",
    "detectable_format:number_highlighted_sections",
    "change_case:english_capital",
    "change_case:english_lowercase",
    "change_case:capital_word_frequency",
    "punctuation:no_comma",
)
LEGACY25 = ACTIVE + EXCLUDED

def fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=30) as r:
        return r.read()

def git_blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def commitment(ids) -> str:
    return hashlib.sha256(json.dumps(sorted(ids)).encode()).hexdigest()

def main() -> int:
    assert len(ACTIVE) == 15
    assert len(EXCLUDED) == 10
    assert len(set(LEGACY25)) == 25
    assert not (set(ACTIVE) & set(EXCLUDED))
    assert commitment(ACTIVE) == TARGET
    for iid in EXCLUDED:
        assert commitment(ACTIVE + (iid,)) != TARGET, iid

    legacy_url = (
        "https://raw.githubusercontent.com/LiveBench/LiveBench/"
        + LIVEBENCH_COMMIT
        + "/livebench/if_runner/instruction_following_eval/instructions_registry.py"
    )
    modern_url = (
        "https://raw.githubusercontent.com/LiveBench/LiveBench/"
        + LIVEBENCH_COMMIT
        + "/livebench/if_runner/ifbench/instructions_registry.py"
    )
    runner_url = (
        "https://raw.githubusercontent.com/moxnixmdj/verification-capsule-runner/"
        + RUNNER_COMMIT + "/execute_livebench_if_threshold_v1.py"
    )
    legacy = fetch(legacy_url)
    modern = fetch(modern_url)
    runner = fetch(runner_url)
    assert git_blob(legacy) == LEGACY_BLOB
    assert git_blob(modern) == MODERN_BLOB
    assert git_blob(runner) == RUNNER_BLOB

    legacy_text = legacy.decode()
    modern_text = modern.decode()
    runner_text = runner.decode()
    for iid in LEGACY25:
        prefix, suffix = iid.split(":", 1)
        # Registry source constructs legacy IDs from category constants plus
        # suffix literals.  Every suffix must be present in the pinned legacy
        # source while none of the complete legacy IDs is a modern registry key.
        assert f'"{suffix}"' in legacy_text or f"'{suffix}'" in legacy_text
        assert f'"{iid}"' not in modern_text and f"'{iid}'" not in modern_text

    exact_hash_expression = (
        'hashlib.sha256(json.dumps(sorted(unknown)).encode()).hexdigest()'
    )
    assert exact_hash_expression in runner_text

    print(json.dumps({
        "schema": "LIVEBENCH_FROZEN_ACTIVE_LEGACY15_HASH_OPENING_PUBLIC_VERIFIER_V1",
        "status": "PASS",
        "active_id_count": len(ACTIVE),
        "excluded_legacy_id_count": len(EXCLUDED),
        "commitment_sha256": commitment(ACTIVE),
        "terminal_dataset_read": False,
        "new_terminal_cases_exposed": 0,
    }, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
