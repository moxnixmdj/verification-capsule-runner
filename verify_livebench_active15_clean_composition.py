#!/usr/bin/env python3
from __future__ import annotations

import collections
import json
import pathlib
import random
import subprocess
import sys
import tempfile

LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"

ROOT = pathlib.Path(__file__).resolve().parent
SUBJECT_ROOT = ROOT / "subject/livebench_active15_clean_composition_20261005"
BLOBS = {
    "canonical/runtime/livebench_legacy15_unified_composer_v1.py": "08a715147e23d27cb243b216c988e09134e12808",
    "canonical/runtime/livebench_legacy15_general_composer_v1.py": "ced56b94e472a615f70180a4797fda178358e7fe",
    "canonical/runtime/livebench_legacy15_special_composer_v1.py": "8510c3790edd48e4bf4427c5b093e3f71325aa1d",
    "canonical/runtime/livebench_legacy15_composition_archetypes_v1.py": "0dbef76a6189a3cdc21ce3dae97ef6921e333b34",
    "canonical/runtime/livebench_legacy_visible_constraint_compiler_v4.py": "721207ba39d502e3f610289578e9d5bab78b1fcc",
    "canonical/runtime/livebench_legacy_visible_constraint_compiler_v1.py": "e986035ff68b53c0dc7a7eb478f6e3d8882214aa",
}
SEEDS = (1701, 1702, 1703)
REPEAT_MARKER = (
    "First repeat the request word for word without change,"
    " then give your answer (1. do not say any words or characters"
    " before repeating the request; 2. the request you need to repeat"
    " does not include this sentence)"
)


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, text=True, **kw)


def make_case(active, ids, seed, ordinal):
    order = list(ids)
    local = random.Random(seed * 1000003 + ordinal)
    local.shuffle(order)
    random.seed(seed * 1000003 + ordinal)

    kwargs_by_id = {}
    descriptions = []
    for iid in order:
        checker = active[iid](iid)
        desc = checker.build_description()
        kwargs = checker.get_instruction_args()
        kwargs_by_id[iid] = dict(kwargs or {})
        descriptions.append(desc)

    prompt = (
        "The following are the beginning sentences of a news article from the Guardian.\n"
        "-------\n"
        "Synthetic public article text for source-only composition verification.\n"
        "-------\n"
        "Please summarize based on the sentences provided."
        + "".join(" " + d for d in descriptions)
    )
    if "combination:repeat_prompt" in order:
        kwargs_by_id["combination:repeat_prompt"]["prompt_to_repeat"] = prompt.split(REPEAT_MARKER)[0]
    return order, kwargs_by_id, prompt


def score(active, order, kwargs_by_id, response):
    failed = []
    for iid in order:
        checker = active[iid](iid)
        checker.build_description(**kwargs_by_id[iid])
        if not bool(checker.check_following(response)):
            failed.append(iid)
    return failed


def main() -> int:
    for rel, expected in BLOBS.items():
        path = SUBJECT_ROOT / rel
        got = run(["git", "hash-object", str(path)], capture_output=True).stdout.strip()
        assert got == expected, (rel, got, expected)

    sys.path.insert(0, str(SUBJECT_ROOT))
    from canonical.runtime import livebench_legacy15_unified_composer_v1 as subject
    from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as shapes

    all_sets = shapes.enumerate_compatible_sets()
    assert len(all_sets) == 928
    assert set(shapes.archetype(x) for x in all_sets) == set(shapes.ARCHETYPE_ORDER)

    with tempfile.TemporaryDirectory(prefix="livebench-active15-clean-") as td:
        checkout = pathlib.Path(td) / "LiveBench"
        run(["git", "clone", "--quiet", "--filter=blob:none", "--no-checkout",
             "https://github.com/LiveBench/LiveBench.git", str(checkout)])
        run(["git", "-C", str(checkout), "fetch", "--quiet", "--depth=1", "origin", LIVEBENCH_COMMIT])
        run(["git", "-C", str(checkout), "checkout", "--quiet", "--detach", LIVEBENCH_COMMIT])

        registry_path = "livebench/if_runner/instruction_following_eval/instructions_registry.py"
        instructions_path = "livebench/if_runner/instruction_following_eval/instructions.py"
        got_registry = run(["git", "-C", str(checkout), "rev-parse", f"HEAD:{registry_path}"],
                           capture_output=True).stdout.strip()
        got_instructions = run(["git", "-C", str(checkout), "rev-parse", f"HEAD:{instructions_path}"],
                               capture_output=True).stdout.strip()
        assert got_registry == REGISTRY_BLOB, (got_registry, REGISTRY_BLOB)
        assert got_instructions == INSTRUCTIONS_BLOB, (got_instructions, INSTRUCTIONS_BLOB)

        sys.path.insert(0, str(checkout / "livebench/if_runner"))
        from instruction_following_eval import instructions_registry

        active = instructions_registry.INSTRUCTION_DICT
        assert set(shapes.ACTIVE_IDS) <= set(active)

        error_counts = collections.Counter()
        checker_failure_counts = collections.Counter()
        archetype_failures = collections.Counter()
        archetype_totals = collections.Counter()
        successes = 0
        generated = 0
        total = 0
        first_examples = {}

        for seed in SEEDS:
            for ordinal, ids in enumerate(all_sets):
                total += 1
                mode = shapes.archetype(ids)
                archetype_totals[mode] += 1
                order, kwargs_by_id, prompt = make_case(active, ids, seed, ordinal)
                result = subject.compose_visible_prompt(prompt)
                if result.get("response") is None:
                    error = str(result.get("error") or result.get("status") or "UNKNOWN_FAIL_CLOSED")
                    error_counts[error] += 1
                    archetype_failures[mode] += 1
                    first_examples.setdefault(
                        "composer:" + error,
                        {"seed": seed, "ids": list(ids), "archetype": mode},
                    )
                    continue

                generated += 1
                response = str(result["response"])
                failed = score(active, order, kwargs_by_id, response)
                if failed:
                    archetype_failures[mode] += 1
                    for iid in failed:
                        checker_failure_counts[iid] += 1
                    key = "checker:" + ",".join(sorted(failed))
                    first_examples.setdefault(
                        key,
                        {"seed": seed, "ids": list(ids), "archetype": mode},
                    )
                else:
                    successes += 1

        receipt = {
            "schema": "PROJECT_BRAIN_LIVEBENCH_ACTIVE15_CLEAN_COMPOSITION_PUBLIC_GRID_VERIFICATION_V1",
            "status": "PASS" if successes == total else "FAIL_WITH_PUBLIC_SYNTHETIC_RESIDUALS",
            "pinned_livebench_commit": LIVEBENCH_COMMIT,
            "registry_blob": REGISTRY_BLOB,
            "instructions_blob": INSTRUCTIONS_BLOB,
            "subject_blobs": BLOBS,
            "active15_identity_sets": len(all_sets),
            "seeds": list(SEEDS),
            "public_synthetic_compositions_tested": total,
            "responses_generated": generated,
            "all_contracts_passed": successes,
            "all_contracts_pass_rate": successes / total,
            "composer_fail_closed_count": sum(error_counts.values()),
            "checker_failed_case_count": total - successes - sum(error_counts.values()),
            "composer_errors": dict(error_counts.most_common()),
            "checker_failure_counts": dict(checker_failure_counts.most_common()),
            "archetype_totals": dict(sorted(archetype_totals.items())),
            "archetype_failures": dict(sorted(archetype_failures.items())),
            "first_public_synthetic_examples_by_failure_class": first_examples,
            "terminal_case_content_read": False,
            "terminal_case_metadata_read": False,
            "terminal_instruction_ids_read": False,
            "terminal_kwargs_read": False,
            "terminal_scores_read": False,
            "acceptance_credit_delta": 0,
            "semantic_capability_credit_delta": 0,
        }
        pathlib.Path("livebench_active15_clean_composition_public_grid_verification.json").write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(json.dumps(receipt, sort_keys=True))
        return 0 if successes == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
