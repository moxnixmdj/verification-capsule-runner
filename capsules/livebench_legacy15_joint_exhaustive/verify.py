#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path

LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
SUBJECT_BLOBS = {
    "livebench_legacy_visible_constraint_compiler_v1.py": "e986035ff68b53c0dc7a7eb478f6e3d8882214aa",
    "livebench_legacy_visible_constraint_compiler_v4.py": "f3d5165071438a7f0ce8cd57c0c3489aa3d08497",
    "livebench_frozen_active_legacy15_v1.py": "34440ee69322e9d519cbe656cb03c55683a8b9c6",
    "livebench_legacy15_joint_witness_v1.py": "556370b5cee746fb80750050b1903e99fc71f140",
}
REPEAT_MARKER = (
    "First repeat the request word for word without change,"
    " then give your answer (1. do not say any words or characters"
    " before repeating the request; 2. the request you need to repeat"
    " does not include this sentence)"
)


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def projected_conflict_pairs(registry, active_ids: tuple[str, ...]) -> set[frozenset[str]]:
    active = set(active_ids)
    pairs: set[frozenset[str]] = set()
    for left, rights in registry.INSTRUCTION_CONFLICTS.items():
        if left not in active:
            continue
        for right in rights:
            if right in active and right != left:
                pairs.add(frozenset((left, right)))
    return pairs


def valid_subset(subset: tuple[str, ...], conflicts: set[frozenset[str]]) -> bool:
    s = set(subset)
    return not any(pair <= s for pair in conflicts)


def build_case(registry, subset: tuple[str, ...], seed: int):
    random.seed(seed)
    descriptions: list[str] = []
    kwargs_by_id: dict[str, dict] = {}

    for iid in subset:
        inst = registry.INSTRUCTION_DICT[iid](iid)
        desc = inst.build_description()
        kwargs = inst.get_instruction_args()
        descriptions.append(str(desc))
        kwargs_by_id[iid] = dict(kwargs or {})

    prompt = (
        "The following are the beginning sentences of a news article from the Guardian.\n"
        "-------\n"
        "A neutral source sentence about a public event. Another source sentence gives context.\n"
        "-------\n"
        "Please summarize based on the sentences provided. "
        + " ".join(descriptions)
    )

    if "combination:repeat_prompt" in subset:
        positions = []
        start = 0
        while True:
            pos = prompt.find(REPEAT_MARKER, start)
            if pos < 0:
                break
            positions.append(pos)
            start = pos + 1
        assert len(positions) == 1, ("REPEAT_MARKER_COUNT", subset, len(positions))
        kwargs_by_id["combination:repeat_prompt"]["prompt_to_repeat"] = prompt[: positions[0]]

    exact_checkers = []
    for iid in subset:
        checker = registry.INSTRUCTION_DICT[iid](iid)
        checker.build_description(**kwargs_by_id[iid])
        exact_checkers.append((iid, checker, kwargs_by_id[iid]))

    return prompt, exact_checkers


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--livebench-root", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    capsule = Path(__file__).resolve().parent
    brain_root = capsule / "brain"
    runtime = brain_root / "canonical/runtime"
    for name, expected in SUBJECT_BLOBS.items():
        got = git_blob_sha(runtime / name)
        assert got == expected, ("SUBJECT_BLOB_DRIFT", name, got, expected)

    livebench_root = Path(args.livebench_root).resolve()
    instructions_path = livebench_root / "livebench/if_runner/instruction_following_eval/instructions.py"
    registry_path = livebench_root / "livebench/if_runner/instruction_following_eval/instructions_registry.py"
    assert git_blob_sha(instructions_path) == INSTRUCTIONS_BLOB
    assert git_blob_sha(registry_path) == REGISTRY_BLOB

    sys.path.insert(0, str(brain_root))
    sys.path.insert(0, str(livebench_root / "livebench/if_runner"))

    from canonical.runtime import livebench_frozen_active_legacy15_v1 as active
    from canonical.runtime import livebench_legacy15_joint_witness_v1 as subject
    from instruction_following_eval import instructions_registry as registry

    active_receipt = active.verify()
    assert active_receipt["status"] == "PASS__EXISTING_TERMINAL_SET_COMMITMENT_OPENED"
    active_ids = tuple(active.ACTIVE_IDS)
    assert len(active_ids) == 15 and len(set(active_ids)) == 15

    conflicts = projected_conflict_pairs(registry, active_ids)
    ordered = tuple(sorted(active_ids))
    subsets = [
        subset
        for size in range(1, 6)
        for subset in combinations(ordered, size)
        if valid_subset(subset, conflicts)
    ]
    assert len(subsets) == 928, ("VALID_SUBSET_COUNT_DRIFT", len(subsets))

    exact_full_pass = 0
    candidate_fail_closed = 0
    exact_fail_after_candidate = 0
    family_failures = Counter()
    route_counts = Counter()
    failures = []

    for index, subset in enumerate(subsets):
        prompt, checkers = build_case(registry, subset, seed=202610040000 + index)
        out = subject.solve(prompt)
        route_counts[str(out.get("route") or out.get("status"))] += 1
        if out.get("status") != "PASS_CANDIDATE_JOINT_LEGACY15_WITNESS":
            candidate_fail_closed += 1
            for iid in subset:
                family_failures[iid] += 1
            if len(failures) < 100:
                failures.append({
                    "subset": list(subset),
                    "stage": "SYNTHESIS_FAIL_CLOSED",
                    "error": out.get("error"),
                })
            continue

        response = str(out.get("response") or "")
        checker_results = []
        for iid, checker, _kwargs in checkers:
            try:
                ok = bool(checker.check_following(response))
                err = None
            except Exception as exc:
                ok = False
                err = type(exc).__name__ + ":" + str(exc)
            checker_results.append((iid, ok, err))

        if all(ok for _iid, ok, _err in checker_results):
            exact_full_pass += 1
        else:
            exact_fail_after_candidate += 1
            failed_ids = [iid for iid, ok, _err in checker_results if not ok]
            for iid in failed_ids:
                family_failures[iid] += 1
            if len(failures) < 100:
                failures.append({
                    "subset": list(subset),
                    "stage": "EXACT_POSTVALIDATION_FAIL",
                    "failed_ids": failed_ids,
                    "checker_errors": {
                        iid: err for iid, ok, err in checker_results if not ok and err
                    },
                    "route": out.get("route"),
                })

    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_LEGACY15_JOINT_EXHAUSTIVE_INDEPENDENT_VERIFICATION_V1",
        "status": "PASS_AUDIT_COMPLETE",
        "bindings": {
            "livebench_commit": LIVEBENCH_COMMIT,
            "instructions_blob": INSTRUCTIONS_BLOB,
            "registry_blob": REGISTRY_BLOB,
            "subject_blobs": SUBJECT_BLOBS,
            "active_set_commitment": active.EXPECTED_COMMITMENT,
        },
        "source_geometry": {
            "active_identity_count": 15,
            "historical_generator_initial_draw_max": 5,
            "conflict_valid_subsets_size_1_to_5": len(subsets),
            "projected_conflict_pair_count": len(conflicts),
        },
        "audit": {
            "exact_full_pass": exact_full_pass,
            "candidate_fail_closed": candidate_fail_closed,
            "exact_fail_after_candidate": exact_fail_after_candidate,
            "exact_full_pass_rate": exact_full_pass / len(subsets),
            "family_failure_counts": dict(sorted(family_failures.items())),
            "route_counts": dict(sorted(route_counts.items())),
            "failure_samples": failures,
        },
        "proved": [
            "ALL_928_CONFLICT_VALID_ACTIVE15_IDENTITY_SUBSETS_OF_CARDINALITY_1_TO_5_WERE_EXERCISED_ON_SOURCE_GENERATED_VISIBLE_DESCRIPTIONS",
            "EVERY_CANDIDATE_RESPONSE_WAS_POSTVALIDATED_BY_THE_EXACT_PINNED_LEGACY_CHECKER_CLASSES",
            "ZERO_ACTIVE_TERMINAL_PROMPTS_KWARGS_RESPONSES_SCORES_OR_CASE_COMBINATIONS_WERE_READ",
        ],
        "hard_nonclaims": [
            "SYNTHETIC_SOURCE_VALID_PARAMETER_DRAWS_DO_NOT_PROVE_ACTIVE_TERMINAL_DISTRIBUTION",
            "A_FAIL_CLOSED_SYNTHESIS_CASE_DOES_NOT_PROVE_THE_CONSTRAINT_SET_IS UNSATISFIABLE",
            "NO_LIVEBENCH_ACCEPTANCE_CAPABILITY_OR_OWNERSHIP_CREDIT",
            "NO_FRESH_TERMINAL_REALITY",
        ],
        "accounting": {
            "incremental_spend_usd": 0,
            "active_terminal_rows_read": 0,
            "acceptance_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        },
    }

    Path(args.output).write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "tested": len(subsets),
        "exact_full_pass": exact_full_pass,
        "candidate_fail_closed": candidate_fail_closed,
        "exact_fail_after_candidate": exact_fail_after_candidate,
        "top_family_failures": family_failures.most_common(8),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
