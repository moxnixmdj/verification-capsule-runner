#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
D=ROOT/"verification_subjects"/"mysterymechanism_truth_repair_20261005"

EXPECTED={
 "MYSTERYMECHANISM_ROOT_CLASSIFICATION_TRUTH_REPAIR_CANDIDATE_20261005_V1.json":"40e6734771ee658421d9ff1da2ced5902ca86de3",
 "OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json":"562536d9ba3f245a6bd24490a1eb3b30f27e0c3a",
 "PRIVATE_SURFACE_ROUTE_DELETION_VS_SUBSTITUTION_RECONCILIATION_V1.json":"a12e23ca249918f94175a31882c3cba57cc0d0ae",
 "PRIVATE_SURFACE_DEPENDENCY_DELETION_AND_ABSOLUTE_PROOF_MAP_V1.json":"addea62fec6113747bce0f578863e400374f4b2a",
 "PRIVATE_SURFACE_DOMINANCE_VERDICT_V2.json":"d656952a509f7e9f375cc817bee1bb20eee06b78",
 "PRIVATE_SURFACE_DOMINANCE_V2_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json":"e1cf166b322668a087aa42a47a9ad1c6951b4b14",
 "UNBARRED_FAMILY_MATCHED_PARITY_PROTOCOL_V1.json":"49181a12362ba3d640fc18d0251901dd49dce929",
 "UNKNOWN_DOMAIN_V6_TOTAL_EXACT_ACCEPTANCE_REDUCTION_20261005_V1.json":"bfbed0be7da9a3bfe1d007ca0576480c48103596",
 "OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json":"dd85ca4bb01193220a24afbb189365937024b2a8",
 "TERMINAL_ROOT_CAUSE_STATE_V1.json":"919da676976043e5b501f207d3cf420dc4fb50b1",
}
def blob(p):
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def load(name): return json.loads((D/name).read_text(encoding="utf-8"))
got={name:blob(D/name) for name in EXPECTED}
assert got==EXPECTED,(got,EXPECTED)

cand=load("MYSTERYMECHANISM_ROOT_CLASSIFICATION_TRUTH_REPAIR_CANDIDATE_20261005_V1.json")
reg=load("OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json")
delete=load("PRIVATE_SURFACE_ROUTE_DELETION_VS_SUBSTITUTION_RECONCILIATION_V1.json")
dep=load("PRIVATE_SURFACE_DEPENDENCY_DELETION_AND_ABSOLUTE_PROOF_MAP_V1.json")
dom=load("PRIVATE_SURFACE_DOMINANCE_VERDICT_V2.json")
domv=load("PRIVATE_SURFACE_DOMINANCE_V2_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json")
proto=load("UNBARRED_FAMILY_MATCHED_PARITY_PROTOCOL_V1.json")
v6=load("UNKNOWN_DOMAIN_V6_TOTAL_EXACT_ACCEPTANCE_REDUCTION_20261005_V1.json")
ledger=load("OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json")
root=load("TERMINAL_ROOT_CAUSE_STATE_V1.json")

pid="MYSTERYMECHANISM_GE_49_55"
contracts=[
 "ITERATIVE_RESEARCH_EVIDENCE_CONTROL_001",
 "SPECIFICATION_TO_INDEPENDENT_ACCEPTANCE_MODEL_001",
 "TOOL_ROUTE_DISCOVERY_AND_SELECTION_001",
]

p=next(x for x in reg["predicates"] if x["id"]==pid)
assert p["family"]=="UNKNOWN_DOMAIN_ADAPTATION"
assert p["kind"]=="PUBLIC_FIXED_BAR"
assert p["surface"]=="MysteryMechanism"

rd=next(x for x in delete["current_route_deletions"] if x["surface"]=="Vals MysteryMechanism")
assert rd["status"]=="DELETE_AS_REQUIRED_EXECUTION_ROUTE__PRESERVE_AS_BACKGROUND_TARGET_REFERENCE_ONLY"
assert rd["represented_contracts"]==contracts
assert "NO_FAMILY_CREDIT_FROM_ROUTE_DELETION" in rd["terminal_requirement_remaining"]
assert delete["distinction"]["benchmark_substitution"]["current_admitted_count"]==0
assert delete["distinction"]["benchmark_substitution"]["authority"] is False
assert "BENCHMARK_ROUTE_DELETION_IS_NOT_FAMILY_PROOF" in delete["anti_weakening"]
assert "BENCHMARK_ROUTE_DELETION_IS_NOT_A_CLAIM_OF_MATCHING_THE_PRIVATE_BENCHMARK_SCORE" in delete["anti_weakening"]
assert "ALL_REPRESENTED_BEHAVIORAL_CONTRACTS_REMAIN_IN_THE_TERMINAL_PORTFOLIO_AND_MUST_PASS_THEIR_FROZEN_ACCEPTANCE" in delete["anti_weakening"]

rep=next(x for x in dep["replacements"] if x["surface"]=="Vals MysteryMechanism")
assert rep["contracts"]==contracts
assert "REQUIRED_CONTRACTS_PASS_ADMISSIBLE_STATISTICAL_OR_EXHAUSTIVE_PROOF" in rep["delete_surface_when"]
assert dep["objective"]=="DELETE_DEPENDENCE_ON_PRIVATE_OR_NONREPRODUCIBLE_BENCHMARKS_WITHOUT_WEAKENING_THE_TERMINAL_GOAL_BY_PROVING_THE_FROZEN_BEHAVIORAL_CONTRACTS_DIRECTLY"
assert "NO_FAMILY_CREDIT_FROM_SURFACE_DELETION_ALONE" in dep["nonweakening_requirements"]

m=dom["blocked_route_verdicts"]["BLOCKED_MYSTERYMECHANISM"]
assert m["redundant"] is True and m["uncovered_obligations"]==[]
assert dom["target_weakening"] is False
assert dom["status"]=="COMPLETE__ZERO_UNCOVERED_BEHAVIORAL_OBLIGATIONS__ALL_BLOCKED_PRIVATE_SURFACES_REDUNDANT_AS_EXECUTION_ROUTES"
assert domv["status"]=="INDEPENDENT_PASS__ALL_BLOCKED_PRIVATE_SURFACES_REDUNDANT_AS_EXECUTION_ROUTES__ZERO_TERMINAL_RESULTS"

assert proto["families"]["UNKNOWN_DOMAIN_ADAPTATION"]==contracts
assert proto["target"]["proxy_comparator_allowed"] is False
assert proto["causal_ownership"]["family_promotion_requires"]=="MATCHED_PARITY_PASS_AND_DONOR_DELETION_AND_ABLATION_RESCUE_AND_COMPLETE_LEAF_COVERAGE"
assert "Exact equality requires a finite exhaustive/formal proof mode instead." in proto["scoring"]["strict_equality_note"]

v6d=v6["deduction"]
assert v6["target_predicate"]=="UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"
assert v6d["new_state"]=="PROVED"
assert v6d["family_credit_delta"]==0 and v6d["capability_credit_delta"]==0 and v6d["ownership_credit_delta"]==0

claim=next(x for x in ledger["claims"] if x["predicate_id"]=="UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT")
assert claim["state"]=="PROVED"
assert ledger["saturation"]["proved_predicate_count"]==13
assert ledger["saturation"]["unresolved_predicate_count"]==25

part=root["current_residual_root_partition"]
assert pid in part["root2_only"]
assert pid not in part["root3_only"]
assert part["unresolved_total"]==25
assert (part["root2_only_count"],part["root3_only_count"],part["root2_and_root3_count"])==(16,6,3)
assert part["root1_positive_gap_count"]==0
assert 16+6+3==25

# Re-derive classification consequence from authority, not candidate prose.
# Root2 means comparator/performance uncertainty. But exact private execution was
# target-preservingly deleted and repeat/proxy measurement cannot satisfy it.
# The remaining lawful discharge is complete direct behavioral proof, a scope
# completeness obligation, therefore Root3 under the root state's own rule.
rule=part["derivation_rule"]
assert "ROOT2 FOR PERFORMANCE OR COMPARATOR UNCERTAINTY" in rule
assert "ROOT3 FOR SCOPE INCOMPLETENESS" in rule
derived_after="ROOT3_ONLY"
derived_counts={
 "unresolved_total":25,
 "root1_positive_gap_count":0,
 "root2_only_count":15,
 "root3_only_count":7,
 "root2_and_root3_count":3,
 "root2_touching":18,
 "root3_touching":10,
}
assert derived_counts["root2_only_count"]+derived_counts["root3_only_count"]+derived_counts["root2_and_root3_count"]==25
assert derived_counts["root2_touching"]==derived_counts["root2_only_count"]+derived_counts["root2_and_root3_count"]
assert derived_counts["root3_touching"]==derived_counts["root3_only_count"]+derived_counts["root2_and_root3_count"]

cr=cand["root_reclassification"]
assert cr["before"]=="ROOT2_ONLY" and cr["after"]==derived_after
assert cr["unresolved_total_after"]==derived_counts["unresolved_total"]
assert cr["root2_only_count_after"]==derived_counts["root2_only_count"]
assert cr["root3_only_count_after"]==derived_counts["root3_only_count"]
assert cr["root2_and_root3_count_after"]==derived_counts["root2_and_root3_count"]
assert cr["root2_touching_after"]==derived_counts["root2_touching"]
assert cr["root3_touching_after"]==derived_counts["root3_touching"]
assert cand["replacement_obligation"]["required_behavior_ids"]==contracts
assert cand["replacement_obligation"]["current_state"].startswith("OPEN__")
assert cand["scheduling_effect"]["fresh_reality_authority"] is False
assert cand["scheduling_effect"]["execution_authority"] is False
assert cand["scheduling_effect"]["promotion_authority"] is False
for k in ("acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta","proved_predicate_delta","unresolved_predicate_delta","incremental_spend_usd","new_reality_units_consumed"):
    assert cand["accounting"][k]==0

receipt={
 "schema":"PROJECT_BRAIN_MYSTERYMECHANISM_ROOT_CLASSIFICATION_TRUTH_REPAIR_INDEPENDENT_VERIFICATION_20261005_V1",
 "status":"PASS__TARGET_PRESERVING_PRIVATE_ROUTE_DELETION_IMPLIES_ROOT3_STRONGER_PROOF_RESIDUAL__ZERO_CREDIT",
 "exact_subject_blobs":EXPECTED,
 "predicate_id":pid,
 "represented_contracts":contracts,
 "private_execution_route_deleted":True,
 "proxy_substitution_admitted":False,
 "target_weakening":False,
 "derived_reclassification":{"before":"ROOT2_ONLY","after":"ROOT3_ONLY",**derived_counts},
 "acceptance_credit_delta":0,
 "family_credit_delta":0,
 "capability_credit_delta":0,
 "ownership_credit_delta":0,
 "proved_predicate_delta":0,
 "unresolved_predicate_delta":0,
}
Path("mysterymechanism_root_truth_repair_receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print(json.dumps(receipt,sort_keys=True))
