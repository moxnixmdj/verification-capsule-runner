from __future__ import annotations

import itertools
from canonical.runtime.brain_first_differential_prewave_v1 import (
    SCHEMA,
    compile_brain_first_prewave,
)

SHA = "a" * 40


def receipt(path: str):
    return {"path": path, "git_blob_sha": SHA}


def doc(brain_bits, comparator_by_failure):
    cases = []
    for i, b in enumerate(brain_bits):
        row = {
            "case_id": f"C{i}",
            "brain": {
                "success": bool(b),
                "verified": True,
                "receipt": receipt(f"brain/{i}.json"),
            },
        }
        if not b:
            c = comparator_by_failure.get(i, None)
            if c is not None:
                row["comparator"] = {
                    "exact_opus55": True,
                    "interface_conformant": True,
                    "verified": True,
                    "success": bool(c),
                    "receipt": receipt(f"opus/{i}.json"),
                }
        cases.append(row)
    return {
        "schema": SCHEMA,
        "scope": {
            "finite": True,
            "complete": True,
            "frozen": True,
            "content_addressed": True,
            "shared_binary_success_criterion": True,
            "case_generation_outcome_independent": True,
            "post_freeze_generation": True,
            "contamination_clean": True,
            "case_outcomes_isolated_or_reset_equivalent": True,
            "receipt": receipt("scope.json"),
        },
        "freeze": {
            "brain_commit_frozen": True,
            "brain_runtime_frozen": True,
            "dependencies_frozen": True,
            "scorer_frozen": True,
            "tool_authority_boundary_frozen": True,
            "target_identity_exact_opus55_frozen": True,
            "comparator_neutral_interface_frozen": True,
            "future_comparator_must_conform": True,
            "no_brain_repair_after_exposure": True,
            "no_brain_replay_after_exposure": True,
            "receipt": receipt("freeze.json"),
        },
        "reducer": {
            "monotone_under_success_set_inclusion": True,
            "same_reducer_for_brain_and_comparator": True,
            "receipt": receipt("reducer.json"),
        },
        "cases": cases,
    }


checked = 0
for brain_bits in itertools.product([False, True], repeat=3):
    failures = [i for i, b in enumerate(brain_bits) if not b]
    if not failures:
        out = compile_brain_first_prewave(doc(brain_bits, {}))
        assert out["status"] == "CANDIDATE_COMPARATOR_FREE_DIFFERENTIAL_DOMINANCE", out
        assert out["comparator_cases_required"] == [], out
        checked += 1
        continue

    # No comparator results: exactly the Brain-failure set must remain.
    out = compile_brain_first_prewave(doc(brain_bits, {}))
    assert out["status"] == "RESIDUAL_COMPARATOR_OPEN", out
    assert set(out["unresolved_residual_ids"]) == {f"C{i}" for i in failures}, out
    checked += 1

    # Exhaust every exact comparator outcome assignment on the Brain failures.
    for comp_bits in itertools.product([False, True], repeat=len(failures)):
        comp = {i: bit for i, bit in zip(failures, comp_bits)}
        out = compile_brain_first_prewave(doc(brain_bits, comp))
        has_counterexample = any(comp.values())
        if has_counterexample:
            assert out["status"] == "VERIFIED_DIFFERENTIAL_COUNTEREXAMPLE", out
            assert out["differential_dominance_proved"] is False, out
        else:
            assert out["status"] == "CANDIDATE_RESIDUAL_ONLY_DIFFERENTIAL_DOMINANCE", out
            assert out["differential_dominance_proved"] is True, out
        checked += 1

# Independent premise falsifiers.
x = doc((True, True, True), {})
x["scope"]["case_outcomes_isolated_or_reset_equivalent"] = False
assert compile_brain_first_prewave(x)["status"] == "FAIL_CLOSED"

x = doc((True, True, True), {})
x["scope"]["case_generation_outcome_independent"] = False
assert compile_brain_first_prewave(x)["status"] == "FAIL_CLOSED"

x = doc((True, True, True), {})
x["reducer"]["monotone_under_success_set_inclusion"] = False
assert compile_brain_first_prewave(x)["status"] == "FAIL_CLOSED"

print(f"PASS: independent exhaustive differential truth-table checks={checked}")
