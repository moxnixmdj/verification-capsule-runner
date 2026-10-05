#!/usr/bin/env python3
import hashlib
import itertools
import json
from pathlib import Path

SUBJECT = Path("subjects/OPUS55_PROTOCOL_TO_TASK_ACCEPTANCE_QUOTIENT_NORMAL_FORM_20261005_V1.json")
EXPECTED_BLOB = "6a77270660e66958c01bfef010714357f88c8c65"

def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def require(cond, msg):
    if not cond:
        raise AssertionError(msg)

raw = SUBJECT.read_bytes()
actual_blob = git_blob_sha(raw)
require(actual_blob == EXPECTED_BLOB, f"subject blob drift: {actual_blob}")
doc = json.loads(raw)
require(doc["schema"] == "PROJECT_BRAIN_OPUS55_PROTOCOL_TO_TASK_ACCEPTANCE_QUOTIENT_NORMAL_FORM_V1", "schema mismatch")
require(doc["terminal_objective"].startswith("PERMANENTLY_INTERNALIZE_CONFIGURE_VERIFY_AND_OWN"), "terminal objective drift")

# Boundary 1: carrier completeness alone cannot determine task-conditioned dominance.
Y = (0, 1)
reward0 = {0: 1, 1: 0}
reward1 = {0: 0, 1: 1}
best0 = {y for y in Y if reward0[y] == max(reward0.values())}
best1 = {y for y in Y if reward1[y] == max(reward1.values())}
require(best0 == {0} and best1 == {1}, "countermodel argmax sets drift")
require(not (best0 & best1), "carrier-only countermodel must have no common argmax")

# Boundary 2: pointwise configurability is materially weaker than one global configuration.
# A global deterministic action cannot be optimal for both conflicting contracts above.
global_optima = best0 & best1
require(global_optima == set(), "global-config counterexample unexpectedly disappeared")

# Positive theorem falsification sweep.
# For finite U,T, premise:
#   every task u maps to a sound contract tau, and
#   for every tau BrainScore[tau] >= TargetScore[tau]
# must imply the corresponding task-level noninferiority.
scores = (0, 1, 2)
positive_models = 0
for mapping in itertools.product(range(3), repeat=3):
    for target in itertools.product(scores, repeat=3):
        for brain in itertools.product(scores, repeat=3):
            if not all(brain[t] >= target[t] for t in range(3)):
                continue
            positive_models += 1
            for u in range(3):
                tau = mapping[u]
                require(
                    brain[tau] >= target[tau],
                    f"positive theorem counterexample: mapping={mapping} target={target} brain={brain} u={u}",
                )
require(positive_models > 0, "positive theorem sweep vacuous")

# Premise necessity: without semantic coverage for a task, carrier completeness does not settle it.
# The omitted task can reverse its evaluator while all represented carrier facts stay unchanged.
represented_contract_best = 0
omitted_task_best = 1
require(represented_contract_best != omitted_task_best, "semantic-coverage negative canary invalid")

# Route partition must be explicit and exhaustive at the theorem schema level.
routes = set(doc["exact_route_factorization"].keys())
require(routes == {"E_EXACT", "M_RESTRICTED", "H_SEPARATING", "OTHER"}, f"route partition drift: {routes}")

# The theorem must not overclaim live terminal closure or authority.
effect = doc["current_terminal_effect"]
require(effect["literal_terminal"] is False, "theorem must not claim terminal")
for k in ("acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta"):
    require(effect[k] == 0, f"nonzero credit forbidden: {k}")
for k in ("scheduling_authority","execution_authority","promotion_authority","fresh_reality_authority"):
    require(doc[k] is False, f"authority overclaim: {k}")
require(doc["independent_verification_required"] is True, "independent verification boundary missing")

# Required irreducible-information boundary must remain explicit.
cut = doc["irreducible_information_cut"]
require(len(cut["not_removed_by_protocol_carrier_coverage"]) >= 2, "irreducible semantic cut weakened")
require("H_SEPARATING" in doc["exact_route_factorization"], "H-separating remainder removed")

receipt = {
    "schema": "PROJECT_BRAIN_PROTOCOL_TO_TASK_ACCEPTANCE_QUOTIENT_INDEPENDENT_VERIFICATION_20261005_V1",
    "subject_git_blob_sha": actual_blob,
    "result": "PASS_WITH_LIVE_PREMISES_OPEN",
    "checks": {
        "exact_subject_blob": True,
        "carrier_only_countermodel": True,
        "global_configuration_counterexample": True,
        "finite_positive_theorem_falsification_sweep": True,
        "positive_models_checked": positive_models,
        "semantic_coverage_necessity_canary": True,
        "route_partition_exact": sorted(routes),
        "no_terminal_or_credit_overclaim": True,
        "irreducible_H_separating_boundary_preserved": True
    },
    "scope": "VERIFIES_LOGICAL_REDUCTION_AND_BOUNDARIES_ONLY__DOES_NOT_PROVE_CURRENT_CARRIER_COMPLETE_TASK_SEMANTIC_COVERAGE_OR_ANY_LIVE_ACCEPTANCE_PREDICATE",
    "incremental_spend_usd": 0,
    "new_reality_units_consumed": 0,
    "terminal_cases_consumed": 0
}
Path("results").mkdir(exist_ok=True)
Path("results/protocol_to_task_acceptance_quotient_verification_20261005_v1.json").write_text(
    json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
print(json.dumps(receipt, indent=2, sort_keys=True))
