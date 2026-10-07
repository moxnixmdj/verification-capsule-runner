from __future__ import annotations

import copy

from canonical.runtime.acceptance_quotient_simulation_v1 import verify_acceptance_quotient_certificate as verify_v1
from canonical.runtime.acceptance_quotient_simulation_v2 import verify_acceptance_quotient_certificate_v2 as verify_v2
from canonical.runtime.acceptance_quotient_simulation_v3 import verify_acceptance_quotient_certificate_v3 as verify_v3
from canonical.tests.test_acceptance_quotient_simulation_v3 import base, receipt


def require(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)


def branching_certificate():
    cert = base()
    cert["target_states"] = ["T0", "T1", "T2"]
    cert["brain_states"] = ["B0", "B1", "B2"]
    cert["terminal_target_states"] = ["T1", "T2"]
    cert["terminal_brain_states"] = ["B1", "B2"]
    cert["relation"] = [["T0", "B0"], ["T1", "B1"], ["T2", "B2"]]
    cert["target_cut_edges"] = [
        {"id": "E0", "from": "T0", "to": "T1"},
        {"id": "E1", "from": "T0", "to": "T2"},
    ]
    shared_scope = receipt(
        "s",
        invariant_holds=True,
        scope_complete=True,
        universal_over_realizations=True,
        independent_or_objective=True,
    )
    cert["brain_macro_edges"] = [
        {
            "from": "B0",
            "to": "B1",
            "covers_target_edge_ids": ["E0"],
            "scope_authority_receipt": copy.deepcopy(shared_scope),
            "scope_authority_invariant": False,
            "realizability_receipt": receipt(
                "r0",
                scope_complete=True,
                universal_from_abstract_class=True,
                independent_or_objective=True,
            ),
        },
        {
            "from": "B0",
            "to": "B2",
            "covers_target_edge_ids": ["E1"],
            "scope_authority_receipt": copy.deepcopy(shared_scope),
            "scope_authority_invariant": False,
            "realizability_receipt": receipt(
                "r1",
                scope_complete=True,
                universal_from_abstract_class=True,
                independent_or_objective=True,
            ),
        },
    ]
    cert.pop("causal_strategy_receipt", None)
    return cert


# Exact finite quantifier falsifier.
pointwise = all(any(b == e for b in (0, 1)) for e in (0, 1))
uniform = any(all(b == e for e in (0, 1)) for b in (0, 1))
require(pointwise is True, "POINTWISE_EXPECTED_TRUE")
require(uniform is False, "UNIFORM_EXPECTED_FALSE")

# Original V3 positive and negative controls.
good = base()
require(verify_v3(good)["status"] == "PASS", "V3_GOOD_CERT_MUST_PASS")

bad = base()
bad["causal_strategy_receipt"]["no_future_or_target_oracle"] = False
require(verify_v3(bad)["status"] == "FAIL_CLOSED", "V3_MUST_REJECT_FUTURE_OR_TARGET_ORACLE")

bad = base()
bad["brain_macro_edges"][0].pop("causal_policy_binding_receipt")
require(verify_v3(bad)["status"] == "FAIL_CLOSED", "V3_MUST_REQUIRE_PER_EDGE_POLICY_BINDING")

# Demonstrate the precise repair boundary:
# V1/V2 graph+semantic checks can accept branch-specific existential matches.
# V3 refuses to treat that as one causal policy without a causal-strategy receipt.
branching = branching_certificate()
v1_input = copy.deepcopy(branching)
for edge in v1_input["brain_macro_edges"]:
    edge["scope_authority_invariant"] = True
require(verify_v1(v1_input)["status"] == "PASS", "V1_POINTWISE_BRANCHING_EXPECTED_PASS")
require(verify_v2(branching)["status"] == "PASS", "V2_POINTWISE_BRANCHING_EXPECTED_PASS")
require(verify_v3(branching)["status"] == "FAIL_CLOSED", "V3_MUST_FAIL_CLOSED_WITHOUT_UNIFORM_POLICY_BINDING")

print("PASS: independent causal-quantifier and V3 fail-closed checks")
