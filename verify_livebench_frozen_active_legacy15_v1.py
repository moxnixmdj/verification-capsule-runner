#!/usr/bin/env python3
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
SUBJECT = ROOT / "subject/legacy15/livebench_frozen_active_legacy15_v1.py"
RECEIPT = ROOT / "subject/legacy15/FIRST_DIRECT_ATTEMPT_RECEIPT.json"
LIVEBENCH = pathlib.Path("/tmp/LiveBench")
RUNNER = pathlib.Path("/tmp/execute_livebench_if_threshold_v1.py")

EXPECTED_SUBJECT_BLOB = "34440ee69322e9d519cbe656cb03c55683a8b9c6"
EXPECTED_RECEIPT_BLOB = "0ddffd52cd05b880964cf034527aabddb255baef"
EXPECTED_RUNNER_BLOB = "05d71d3d06ebac9b5d74eb31b137141e6b8797c2"
EXPECTED_LEGACY_REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
EXPECTED_MODERN_REGISTRY_BLOB = "adfed4832877566e62970257b50c6fa32c302fb2"


def git_blob(path: pathlib.Path) -> str:
    return subprocess.run(
        ["git", "hash-object", str(path)], check=True, capture_output=True, text=True
    ).stdout.strip()


def registry_ids(path: pathlib.Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(t, ast.Name) and t.id == "INSTRUCTION_DICT" for t in targets):
                value = node.value
                if isinstance(value, ast.Dict):
                    out = set()
                    for k in value.keys:
                        if isinstance(k, ast.Constant) and isinstance(k.value, str):
                            out.add(k.value)
                    return out
    raise AssertionError("INSTRUCTION_DICT_NOT_FOUND")


def load_subject():
    spec = importlib.util.spec_from_file_location("legacy15_subject", SUBJECT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    assert git_blob(SUBJECT) == EXPECTED_SUBJECT_BLOB
    assert git_blob(RECEIPT) == EXPECTED_RECEIPT_BLOB
    assert git_blob(RUNNER) == EXPECTED_RUNNER_BLOB

    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    frozen_digest = receipt["observed"]["unmatched_instruction_id_set_sha256"]
    assert frozen_digest == "af4eeddebf27394eb689d2049f2f8104ae081ebafe237258bdc1a992e96f598d"
    assert receipt["observed"]["candidate_inference_count"] == 0
    assert receipt["observed"]["candidate_response_count"] == 0

    runner_source = RUNNER.read_text(encoding="utf-8")
    normalized = "".join(runner_source.split())
    assert "hashlib.sha256(json.dumps(sorted(unknown)).encode()).hexdigest()" in normalized

    subject = load_subject()
    active = tuple(subject.ACTIVE_IDS)
    excluded = tuple(subject.EXCLUDED_IDS)
    computed = hashlib.sha256(json.dumps(sorted(active)).encode()).hexdigest()
    assert computed == frozen_digest
    assert subject.verify()["commitment_sha256"] == frozen_digest

    legacy_path = LIVEBENCH / "livebench/if_runner/instruction_following_eval/instructions_registry.py"
    modern_path = LIVEBENCH / "livebench/if_runner/ifbench/instructions_registry.py"
    assert git_blob(legacy_path) == EXPECTED_LEGACY_REGISTRY_BLOB
    assert git_blob(modern_path) == EXPECTED_MODERN_REGISTRY_BLOB
    legacy = registry_ids(legacy_path)
    modern = registry_ids(modern_path)

    assert len(legacy) == 25, len(legacy)
    assert len(active) == 15 and len(set(active)) == 15
    assert len(excluded) == 10 and len(set(excluded)) == 10
    assert set(active).issubset(legacy)
    assert set(excluded) == legacy - set(active)
    assert set(active).isdisjoint(set(excluded))
    assert legacy.isdisjoint(modern)

    result = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_FROZEN_ACTIVE_LEGACY15_INDEPENDENT_OPENING_V1",
        "status": "PASS__EXISTING_FROZEN_UNKNOWN_SET_DIGEST_OPENS_TO_EXACT_15_LEGACY_IDS",
        "frozen_digest": frozen_digest,
        "active_id_count": len(active),
        "excluded_legacy_id_count": len(excluded),
        "legacy_registry_count": len(legacy),
        "modern_registry_count": len(modern),
        "legacy_modern_intersection_count": len(legacy & modern),
        "active_ids": list(active),
        "excluded_ids": list(excluded),
        "pinned_blobs": {
            "candidate_subject": EXPECTED_SUBJECT_BLOB,
            "first_attempt_receipt": EXPECTED_RECEIPT_BLOB,
            "first_attempt_runner": EXPECTED_RUNNER_BLOB,
            "legacy_registry": EXPECTED_LEGACY_REGISTRY_BLOB,
            "modern_registry": EXPECTED_MODERN_REGISTRY_BLOB,
        },
        "new_terminal_rows_read": 0,
        "new_terminal_prompts_read": 0,
        "new_terminal_kwargs_read": 0,
        "new_terminal_responses_read": 0,
        "acceptance_credit_delta": 0,
        "incremental_spend_usd": 0,
    }
    pathlib.Path("livebench_frozen_active_legacy15_opening_v1.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
