from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

EXPECTED = {
    "subject.py": "b5f016bfd8e2c49f0ba4e399b549b268556ffdd6",
    "tests.py": "014a4c5c0e16ab0ee88a37dd1f1a86373c1e600e",
    "governance.json": "7102f0d0fef813c209a54246bcf7e221d060572f",
    "control_loop.json": "da8803584bc1e2bea672bcd1833e526ec489ac81",
    "observable_scope.json": "333bdc8306a19f005a600a47b415a4bd9cf9868c",
}


def blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def load_subject():
    spec = importlib.util.spec_from_file_location("subject", HERE / "subject.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("SUBJECT_IMPORT_SPEC_FAILED")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> None:
    for name, expected in EXPECTED.items():
        got = blob_sha(HERE / name)
        assert got == expected, (name, got, expected)

    subject = load_subject()
    gov = json.loads((HERE / "governance.json").read_text())
    control = json.loads((HERE / "control_loop.json").read_text())
    scope = json.loads((HERE / "observable_scope.json").read_text())

    # Bind the exact current theorem semantics being falsified.
    useful = scope["first_principles_definition"]["externally_useful_capability"]
    assert "changes the distribution of at least one externally observable trace" in useful
    assert scope["theorem"]["statement"] == (
        "EVERY_EXTERNALLY_USEFUL_OPUS55_CAPABILITY_IS_REPRESENTABLE_AS_A_PROPERTY_OF_THE_OBSERVABLE_TRACE_SUPERSET"
    )

    claims = {row["id"]: row for row in control["claims"]}
    current = claims["C_UNIVERSAL_OBSERVABLE_BEHAVIOR_DOMINANCE_BINDING_V1"]
    assert current["status"] == "ACTIVE"
    assert "full observable-trace scope" in current["claim"]
    assert "every externally useful trace property" in current["proof_requirement"]

    # Countermodel 0: observable trace difference without terminal utility difference.
    utility = subject.utility_semantics_countermodel()
    assert utility["observable_difference"] is True
    assert utility["terminal_utility_equal"] is True
    assert utility["observable_difference_not_sufficient_for_useful_capability"] is True

    # Under the exact current source definition, the observable emission difference
    # is enough to satisfy the trace-change side of the usefulness definition.
    # Yet all enumerated terminal-relevant outcomes in the countermodel are equal.
    # Therefore trace difference alone is not sufficient to justify a distinct
    # useful-capability obligation without an explicit utility/outcome criterion.

    # Countermodel 1: literal representational-superset dominance is not necessary
    # if a represented property is outside the actual useful target.
    over = subject.overreach_countermodel()
    assert over["terminal_goal_true"] is True
    assert over["literal_full_superset_dominance"] is False
    assert over["falsifies_necessity_of_full_superset_dominance"] is True

    # Countermodel 2: target-relative proof is insufficient without target completeness.
    under = subject.underbinding_countermodel()
    assert under["declared_certificate_w1"] is True
    assert under["declared_certificate_w2"] is True
    assert under["terminal_w1"] is True
    assert under["terminal_w2"] is False
    assert under["same_declared_certificate_different_terminal_truth"] is True
    assert under["proves_target_completeness_binding_is_necessary"] is True

    compiled = subject.compile_falsification()
    assert compiled["status"] == "PASS__CURRENT_THEOREM_MUST_BE_TARGET_RELATIVE_AND_TARGET_COMPLETE"
    assert compiled["utility_relevance_and_outcome_ordering_required"] is True
    assert compiled["target_completeness_binding_required"] is True
    assert compiled["terminal_credit"] is False
    assert compiled["classification"] == "TRUTH_REPAIR"

    # Bind the PR's own truth boundary so verification cannot be laundered into closure.
    assert gov["accounting"]["classification"] == "TRUTH_REPAIR"
    assert gov["accounting"]["terminal_progress_credit"] is False
    assert "NO_CLAIM_THE_REPAIRED_THEOREM_IS_PROVED" in gov["hard_nonclaims"]
    assert "NO_CLAIM_THE_CURRENT_32_OBLIGATIONS_ARE_REDUNDANT" in gov["hard_nonclaims"]

    print(json.dumps({
        "status": "PASS",
        "exact_source_blobs": EXPECTED,
        "verified": [
            "CURRENT_USEFULNESS_DEFINITION_IS_TOO_BROAD_IF_OBSERVABLE_TRACE_CHANGE_ALONE_IS_TREATED_AS_SUFFICIENT",
            "LITERAL_FULL_REPRESENTATIONAL_SUPERSET_DOMINANCE_IS_NOT_NECESSARY",
            "TARGET_RELATIVE_DOMINANCE_REQUIRES_TARGET_COMPLETENESS_OR_STRONGER_COMPLETE_QUOTIENT",
            "REPAIRED_TERMINAL_THEOREM_REMAINS_UNPROVED",
            "ZERO_TERMINAL_CREDIT",
        ],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
