#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import itertools
import json
import pathlib
import sys

SUBJECT_BLOB = "8c68e63bbc1e1b843f076dbcd8c4bfae11d4cc2a"
LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
SUBJECT = pathlib.Path(__file__).resolve().parent / "subject/livebench_union25_archetypes_v1_20261005"
MODULE = SUBJECT / "canonical/runtime/livebench_union25_archetypes_v1.py"


def git_blob(path: pathlib.Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def compatible_by_pairs(ids, pairs):
    s = set(ids)
    return not any(a in s and b in s for a, b in pairs)


def main() -> int:
    assert git_blob(MODULE) == SUBJECT_BLOB
    sys.path.insert(0, str(SUBJECT))
    from canonical.runtime import livebench_union25_archetypes_v1 as subject

    live = pathlib.Path("/tmp/LiveBench")
    sys.path.insert(0, str(live / "livebench/if_runner"))
    from instruction_following_eval import instructions_registry as registry

    actual_ids = tuple(registry.INSTRUCTION_DICT.keys())
    assert actual_ids == subject.ALL_IDS
    assert len(actual_ids) == 25

    registry_path = (
        live / "livebench/if_runner/instruction_following_eval/instructions_registry.py"
    )
    assert git_blob(registry_path) == REGISTRY_BLOB

    actual_pairs = set()
    for a, values in registry.INSTRUCTION_CONFLICTS.items():
        for b in values:
            if a == b:
                continue
            actual_pairs.add(tuple(sorted((a, b))))
    assert len(actual_pairs) == 97

    subject_pairs = {
        tuple(sorted((a, b)))
        for a in subject.ALL_IDS
        for b in subject.CONFLICTS[a]
        if a != b
    }
    assert subject_pairs == actual_pairs

    actual_sets = []
    for n in range(1, 6):
        for ids in itertools.combinations(actual_ids, n):
            if compatible_by_pairs(ids, actual_pairs):
                actual_sets.append(ids)
    subject_sets = list(subject.enumerate_compatible_sets())
    assert subject_sets == actual_sets

    out = subject.verify()
    assert out["compatible_total"] == 14559
    assert out["embedded_active15_total"] == 928
    assert out["extra_bearing_total"] == 13631
    assert out["distinct_extra10_signatures"] == 156
    assert out["route_counts_extra_bearing"] == {
        "GENERAL": 13614,
        "TWO_RESPONSES": 12,
        "REPEAT_PROMPT": 4,
        "CONSTRAINED_SINGLETON": 1,
    }

    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_UNION25_ARCHETYPES_PUBLIC_RUNNER_VERIFICATION_20261005_V1",
        "status": "PASS__EXACT_PINNED_REGISTRY_PAIR_AND_COMPATIBLE_SET_EQUALITY__UNION25_REDUCED_TO_156_EXTRA_SIGNATURES",
        "subject_blob": SUBJECT_BLOB,
        "pinned_livebench_commit": LIVEBENCH_COMMIT,
        "pinned_registry_blob": REGISTRY_BLOB,
        "registry_instruction_count": 25,
        "nonself_conflict_pairs": len(actual_pairs),
        "compatible_sets": len(actual_sets),
        "compatible_by_cardinality": out["compatible_by_cardinality"],
        "embedded_active15_sets": out["embedded_active15_total"],
        "extra_bearing_sets": out["extra_bearing_total"],
        "distinct_extra10_signatures": out["distinct_extra10_signatures"],
        "route_counts_extra_bearing": out["route_counts_extra_bearing"],
        "terminal_rows_read": 0,
        "hidden_kwargs_read": 0,
        "target_scores_read": 0,
        "acceptance_credit_delta": 0,
        "hard_nonclaims": [
            "STRUCTURAL_REDUCTION_ONLY",
            "UNION25_POINTWISE_COMPOSITION_NOT_YET_PROVED",
            "NO_TERMINAL_GOAL_COMPLETION_CREDIT",
        ],
    }
    pathlib.Path("livebench_union25_archetypes_verification.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
