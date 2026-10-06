from __future__ import annotations

import hashlib
import importlib.util
import itertools
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "source"
RUNTIME = SRC / "matched_success_finite_scope_reducer_v1.py"
GOV = SRC / "MATCHED_SUCCESS_FINITE_SCOPE_REDUCER_V1.json"

EXPECTED_RUNTIME_BLOB = "9f669bed2bcceed7a47a892c7603892152a5cb6f"
EXPECTED_GOV_BLOB = "6b2696d70f9d4a9d9768dbd7bd097d62e7d4fd67"


def git_blob(path: Path) -> str:
    b = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()


assert git_blob(RUNTIME) == EXPECTED_RUNTIME_BLOB
assert git_blob(GOV) == EXPECTED_GOV_BLOB

spec = importlib.util.spec_from_file_location("reducer", RUNTIME)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
assert spec.loader is not None
spec.loader.exec_module(mod)

gov = json.loads(GOV.read_text())
assert gov["reducer"]["id"] == "EXACT_COMPLETE_FINITE_SCOPE_SUCCESS_FRACTION_V1"
assert gov["reducer"]["same_reducer_for_brain_and_opus"] is True
assert "FORBIDDEN__NO_CLAIM_OUTSIDE_THE_FROZEN_CASE_UNIVERSE" == gov["reducer"]["population_generalization"]
assert gov["execution_authority"] is False
assert gov["fresh_reality_authority"] is False

predicates = [
    "AGENCY_MATCHED_SUCCESS_NONINFERIOR",
    "IF_SCOPE_BOUNDARY_NONINFERIOR",
    "COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR",
]

# Exhaustively prove success-set inclusion transport for all subsets through n=8.
for n in range(1, 9):
    cases = [f"C{i}" for i in range(n)]
    subsets = []
    for mask in range(1 << n):
        subsets.append({cases[i] for i in range(n) if mask & (1 << i)})
    for brain in subsets:
        for opus in subsets:
            if not opus.issubset(brain):
                continue
            for predicate in predicates:
                doc = {
                    "schema": mod.INPUT_SCHEMA,
                    "predicate_id": predicate,
                    "scope": {
                        "finite": True,
                        "complete": True,
                        "frozen": True,
                        "content_addressed": True,
                        "same_case_universe_for_brain_and_opus": True,
                        "binary_success_criterion": True,
                        "no_population_extrapolation": True,
                        "fixed_case_count_before_first_result": True,
                        "no_sequential_early_stop": True,
                        "case_ids": cases,
                    },
                    "brain_success_case_ids": sorted(brain),
                    "opus_success_case_ids": sorted(opus),
                }
                out = mod.compile_reducer(doc)
                assert out["status"] == "PASS__EXACT_FINITE_SCOPE_REDUCER"
                assert out["brain_noninferior"] is True
                assert out["monotonicity_transport_proved_for_this_input"] is True
                assert out["brain_success_count"] >= out["opus_success_count"]
                assert out["population_generalization_claimed"] is False
                assert out["brain_exact_finite_scope_interval"]["lower"] == out["brain_exact_finite_scope_interval"]["upper"]
                assert out["opus_exact_finite_scope_interval"]["lower"] == out["opus_exact_finite_scope_interval"]["upper"]

# General count monotonicity beyond exhaustive subset enumeration.
for n in list(range(1, 101)) + [128, 256, 512, 1024]:
    assert mod.monotonicity_theorem(n) is True

# Fail-closed adversarial mutations.
base = {
    "schema": mod.INPUT_SCHEMA,
    "predicate_id": predicates[0],
    "scope": {
        "finite": True,
        "complete": True,
        "frozen": True,
        "content_addressed": True,
        "same_case_universe_for_brain_and_opus": True,
        "binary_success_criterion": True,
        "no_population_extrapolation": True,
        "fixed_case_count_before_first_result": True,
        "no_sequential_early_stop": True,
        "case_ids": ["A", "B"],
    },
    "brain_success_case_ids": ["A"],
    "opus_success_case_ids": ["A"],
}
for key in [
    "finite",
    "complete",
    "frozen",
    "content_addressed",
    "same_case_universe_for_brain_and_opus",
    "binary_success_criterion",
    "no_population_extrapolation",
    "fixed_case_count_before_first_result",
    "no_sequential_early_stop",
]:
    x = json.loads(json.dumps(base))
    x["scope"][key] = False
    assert mod.compile_reducer(x)["status"] == "FAIL_CLOSED"

x = json.loads(json.dumps(base))
x["brain_success_case_ids"] = ["A", "X"]
assert mod.compile_reducer(x)["status"] == "FAIL_CLOSED"

print(json.dumps({
    "status": "PASS",
    "verified_runtime_blob": EXPECTED_RUNTIME_BLOB,
    "verified_governance_blob": EXPECTED_GOV_BLOB,
    "exhaustive_subset_n_max": 8,
    "general_monotonicity_n_max": 1024,
    "predicates": predicates,
    "population_generalization_claimed": False,
    "authority_delta": 0
}, indent=2, sort_keys=True))
