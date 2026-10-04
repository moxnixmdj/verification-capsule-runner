#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
import pathlib
import sys
from itertools import combinations

LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
SUBJECT_BLOB = "6b22db0a42010d2f810734aa57169a9950a99678"

ROOT = pathlib.Path(__file__).resolve().parent
SUBJECT_ROOT = ROOT / "subject/livebench_union25_extension_cut_v1_20261005"


def git_blob(path: pathlib.Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def main() -> int:
    live = pathlib.Path("/tmp/LiveBench")
    registry_path = live / "livebench/if_runner/instruction_following_eval/instructions_registry.py"
    instructions_path = live / "livebench/if_runner/instruction_following_eval/instructions.py"
    if git_blob(registry_path) != REGISTRY_BLOB:
        raise AssertionError("REGISTRY_BLOB_DRIFT")
    if git_blob(instructions_path) != INSTRUCTIONS_BLOB:
        raise AssertionError("INSTRUCTIONS_BLOB_DRIFT")

    subject_path = SUBJECT_ROOT / "canonical/runtime/livebench_union25_extension_cut_v1.py"
    if git_blob(subject_path) != SUBJECT_BLOB:
        raise AssertionError("SUBJECT_BLOB_DRIFT")

    sys.path.insert(0, str(SUBJECT_ROOT))
    sys.path.insert(0, str(live / "livebench/if_runner"))

    from canonical.runtime import livebench_union25_extension_cut_v1 as cut
    from instruction_following_eval import instructions_registry as registry

    exact_ids = tuple(registry.INSTRUCTION_DICT.keys())
    if set(exact_ids) != set(cut.UNION25) or len(exact_ids) != 25:
        raise AssertionError("UNION25_IDENTITY_DRIFT")

    exact_conflicts = registry.conflict_make(copy.deepcopy(registry.INSTRUCTION_CONFLICTS))
    exact_pairs = {
        frozenset((left, right))
        for left, rights in exact_conflicts.items()
        for right in rights
        if left != right
    }
    if len(exact_pairs) != 97:
        raise AssertionError(f"EXACT_CONFLICT_PAIR_COUNT_DRIFT:{len(exact_pairs)}")

    subject_pairs = {
        frozenset((left, right))
        for left, rights in cut.CONFLICTS.items()
        for right in rights
        if left != right
    }
    if subject_pairs != exact_pairs:
        raise AssertionError(
            "SUBJECT_CONFLICT_GRAPH_MISMATCH:"
            + repr({
                "missing": sorted(map(sorted, exact_pairs - subject_pairs)),
                "extra": sorted(map(sorted, subject_pairs - exact_pairs)),
            })
        )

    exact_sets = []
    for size in range(1, 6):
        for ids in combinations(exact_ids, size):
            s = set(ids)
            if all(not ((exact_conflicts[iid] - {iid}) & s) for iid in s):
                exact_sets.append(tuple(ids))

    subject_sets = list(cut.enumerate_compatible_sets())
    if {frozenset(x) for x in subject_sets} != {frozenset(x) for x in exact_sets}:
        raise AssertionError("SUBJECT_EXACT_COMPATIBLE_SET_MISMATCH")
    if len(exact_sets) != 14559:
        raise AssertionError(f"EXACT_SET_COUNT_DRIFT:{len(exact_sets)}")

    out = cut.verify()
    if out["hard_extension_signature_count"] != 21:
        raise AssertionError("HARD_SIGNATURE_COUNT_NOT_21")
    if out["raw_new_family_signature_count"] != 157:
        raise AssertionError("RAW_NEW_SIGNATURE_COUNT_NOT_157")
    if out["active15_only_set_count"] != 928:
        raise AssertionError("ACTIVE15_SET_COUNT_NOT_928")
    if out["new_family_containing_set_count"] != 13631:
        raise AssertionError("NEW_CONTAINING_SET_COUNT_NOT_13631")
    if out["word_channel"]["conservative_unpadded_global_ceiling_over_WORDS_sets"] != 63:
        raise AssertionError("WORD_CEILING_NOT_63")
    if out["word_channel"]["margin_words"] != 37:
        raise AssertionError("WORD_MARGIN_NOT_37")

    # Recompute the word ceiling independently from the exact set population.
    ceiling = max(
        sum(cut.WORD_CONTRIBUTION_CEILINGS[iid] for iid in ids)
        for ids in exact_sets if cut.WORDS in ids
    )
    if ceiling != 63:
        raise AssertionError(f"INDEPENDENT_WORD_CEILING_DRIFT:{ceiling}")

    receipt = {
        "schema": "LIVEBENCH_UNION25_EXTENSION_CUT_INDEPENDENT_VERIFICATION_V1",
        "status": "PASS__EXACT_PINNED_REGISTRY25_COLLAPSES_TO_21_HARD_EXTENSION_MODES",
        "pinned_livebench_commit": LIVEBENCH_COMMIT,
        "pinned_registry_blob": REGISTRY_BLOB,
        "pinned_instructions_blob": INSTRUCTIONS_BLOB,
        "subject_blob": SUBJECT_BLOB,
        "exact_registry_family_count": len(exact_ids),
        "exact_conflict_pair_count": len(exact_pairs),
        "exact_compatible_set_count": len(exact_sets),
        "active15_only_set_count": out["active15_only_set_count"],
        "new_family_containing_set_count": out["new_family_containing_set_count"],
        "raw_new_family_signature_count": out["raw_new_family_signature_count"],
        "hard_extension_signature_count": out["hard_extension_signature_count"],
        "hard_extension_signatures": out["hard_extension_signatures"],
        "route_counts": out["route_counts"],
        "word_ceiling": ceiling,
        "public_minimum_word_threshold": 100,
        "word_margin": 100 - ceiling,
        "theorem": (
            "THE_RAW_14559_SET_UNION25_STRUCTURAL_PROBLEM_HAS_ONLY_21_"
            "LOAD_BEARING_NEW_FAMILY_HARD_INTERACTION_SIGNATURES_AFTER_"
            "PASSIVE_DECORATOR_QUOTIENT"
        ),
        "terminal_rows_read": 0,
        "hidden_kwargs_read": 0,
        "terminal_instruction_ids_read": 0,
        "target_scores_read": 0,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
    }
    pathlib.Path("livebench_union25_extension_cut_v1_verification.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
