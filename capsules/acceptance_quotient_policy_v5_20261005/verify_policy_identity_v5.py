from __future__ import annotations

import copy

from canonical.runtime.acceptance_quotient_simulation_v5 import (
    verify_acceptance_quotient_certificate_v5 as verify_v5,
)
from canonical.tests.test_acceptance_quotient_simulation_v5 import (
    POLICY_A,
    POLICY_B,
    base,
    receipt,
)


def require(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)


good = base()
good["acceptance_semantics_class"] = "UNIVERSAL_TOP_SUPPORT"
good["distribution_free_dominance_receipt"] = receipt(
    "d",
    class_wide_top_support_dominance_proved=True,
    scope_complete=True,
    target_distribution_irrelevant=True,
    independent_or_objective=True,
    universal_over_all_admissible_brain_policies=True,
)
verdict = verify_v5(good)
require(verdict["status"] == "PASS", "GOOD_UNIVERSAL_CERT_MUST_PASS")
require(verdict["policy_commitment_sha256"] == POLICY_A, "GLOBAL_POLICY_COMMITMENT_MUST_SURVIVE")
require(verdict["all_edge_bindings_same_policy"] is True, "EDGE_BINDINGS_MUST_BE_UNIFORM")

edge_mismatch = copy.deepcopy(good)
edge_mismatch["brain_macro_edges"][0]["causal_policy_binding_receipt"]["policy_commitment_sha256"] = POLICY_B
verdict = verify_v5(edge_mismatch)
require(verdict["status"] == "FAIL_CLOSED", "EDGE_POLICY_ALIAS_MUST_FAIL")

stochastic = base()
stochastic["acceptance_semantics_class"] = "STOCHASTIC_MATCHED_NONINFERIORITY"
stochastic["policy_distribution_bridge_receipt"] = receipt(
    "d",
    policy_choice_coherent=True,
    scope_complete=True,
    distribution_or_expected_utility_order_proved=True,
    independent_or_objective=True,
    policy_commitment_sha256=POLICY_A,
)
require(verify_v5(stochastic)["status"] == "PASS", "MATCHED_STOCHASTIC_POLICY_MUST_PASS")

stochastic_alias = copy.deepcopy(stochastic)
stochastic_alias["policy_distribution_bridge_receipt"]["policy_commitment_sha256"] = POLICY_B
require(verify_v5(stochastic_alias)["status"] == "FAIL_CLOSED", "STOCHASTIC_POLICY_ALIAS_MUST_FAIL")

unsupported = base()
unsupported["acceptance_semantics_class"] = "UNCLASSIFIED"
require(verify_v5(unsupported)["status"] == "FAIL_CLOSED", "V4_UNSUPPORTED_CLASS_MUST_REMAIN_FAIL_CLOSED")

print("PASS: independent V5 policy-identity checks")


from verify_task_acceptance_inventory_v1 import main as verify_task_acceptance_inventory
verify_task_acceptance_inventory()
