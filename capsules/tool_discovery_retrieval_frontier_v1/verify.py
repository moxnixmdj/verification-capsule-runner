#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, pathlib

ROOT=pathlib.Path(__file__).resolve().parent

def j(name):
    return json.loads((ROOT/name).read_text())

def git_blob(path):
    raw=(ROOT/path).read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

expected={
    "frontier.json":"5a7a2ddf2bb36b2b2ef8e01189d09550a7304e4a",
    "intent.json":"94c3ca1e24d5bb12cc9dab0bc99a6275378148d4",
    "retrieval_control_receipt.json":"f0a68c8219d704875535543060f63b9ecaca6dd5",
    "backend_router_receipt.json":"34512250b7bc7a69a03ab7d4e9b4d1ef4d2c8bfc",
    "six_class_receipt.json":"a0e5b7793a91e1848fac90247d00772544b87165",
    "apt_interface.py":"f280459525655fdf5f5284efb40118374e5949fb",
    "toolathlon_bridge.json":"a5445019120433ca445468306b7364b938e80a9a",
    "opus_reference.json":"d1993b078e2a97dee6e1e8498ce01b591306a9b1",
    "harness_cut.json":"2206e62d9a9d892474f016f592e4bfaf01c224d2",
}
for name,sha in expected.items():
    assert git_blob(name)==sha,(name,git_blob(name),sha)

frontier=j("frontier.json")
intent=j("intent.json")
retrieval=j("retrieval_control_receipt.json")
backend=j("backend_router_receipt.json")
six=j("six_class_receipt.json")
bridge=j("toolathlon_bridge.json")
opus=j("opus_reference.json")
cut=j("harness_cut.json")
apt=(ROOT/"apt_interface.py").read_text()

assert retrieval["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"),retrieval
assert backend["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"),backend
assert retrieval["verified"]["no_result_nonexistence_firewall"] is True,retrieval
assert retrieval["verified"]["first_verified_witness_stop"] is True,retrieval
assert backend["verified"]["candidate_sufficiency_firewall"] is True,backend
assert backend["verified"]["fake_completeness_rejected"] is True,backend
assert backend["verified"]["independent_witness_receipt_required"] is True,backend

assert six["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"),six
assert six["verified"]["frozen_generator_semantic_classes"]==6,six
assert six["verified"]["all_six_classes_pass"] is True,six
assert six["verified"]["open_domain_scope_relation_closed"] is False,six
assert six["verified"]["strict_acceptance_closed"] is False,six

epoch=frontier["residual_epoch"]
assert epoch["source_blob"]==expected["six_class_receipt.json"],epoch
assert epoch["semantic_state"]["frozen_generator_semantic_classes"]==6,epoch
assert epoch["semantic_state"]["all_six_classes_pass"] is True,epoch
assert epoch["semantic_state"]["open_domain_scope_relation_closed"] is False,epoch

assert 'declared_target_scope = "PUBLIC_APT_PACKAGES_FROM_ALL_ENABLED_APT_SOURCES"' in apt
assert "NO_CLAIM_ABOUT_NON_APT_TOOLS_OR_ECOSYSTEMS" in apt
apt_row=next(x for x in frontier["evaluated_witness_classes"] if x["witness_class"]=="APT_COMPLETE_INTERFACE_INSTANCE_CANDIDATE")
assert "SCOPE_MISMATCH" in apt_row["disposition"],apt_row
assert "UNVERIFIED_INSTANCE_CANDIDATE" in apt_row["disposition"],apt_row

assert bridge["status"].startswith("CANDIDATE"),bridge
assert "INDEPENDENT_VERIFICATION_REQUIRED" in bridge["status"],bridge
scope=bridge["target_local_callable_surface_theorem"]["scope_boundary"]
assert scope=="TARGET_LOCAL_CALLABLE_SURFACE_ONLY__NO_CLAIM_THAT_ALL_OPEN_WORLD_TOOLS_OR_SERVERS_ARE_ENUMERABLE",scope
bridge_row=next(x for x in frontier["evaluated_witness_classes"] if x["witness_class"]=="TOOLATHLON_TARGET_LOCAL_CALLABLE_SURFACE")
assert "BRIDGE_NOT_INDEPENDENTLY_PROMOTED" in bridge_row["disposition"],bridge_row
assert "NOT_UNIVERSAL_SCOPE_PROOF" in bridge_row["disposition"],bridge_row

assert opus["matched_reference"]["pass_at_1_percent"]==77.8,opus
assert "ANY_VALID_ROUTE_TOP1_COMPARATOR_NOT_PUBLISHED_BY_FIRST_PARTY_SOURCE" in opus["remains_open"],opus
assert "SAME_HARNESS_AND_COMMON_TOOL_AUTHORITY_COMPARABILITY" in opus["remains_open"],opus

facts=cut["independently_verified_source_facts"]
assert facts["exact_internal_vs_public_harness_byte_identity_proved"] is False,cut
assert facts["valid_route_top1_opus55_published"] is False,cut
assert cut["deduction"]["same_harness_common_tool_authority_comparability_closed"] is False,cut
assert cut["search_boundary"]["opus55_public_matched_trajectory_found"] is False,cut
assert "NOT_A_CLAIM_OF_GLOBAL_NONEXISTENCE" in cut["search_boundary"]["claim"],cut

policy=frontier["search_policy"]
assert policy["current_state"]=="UNKNOWN_SCOPE_RELATION__NO_SCOPE_CLOSING_WITNESS_IN_CURRENT_ADMISSIBLE_EVIDENCE_SET",policy
assert policy["no_result_semantics"]=="UNKNOWN__NOT_NONEXISTENCE",policy
assert policy["repeat_same_source_set"] is False,policy
assert len(policy["wake_conditions"])>=4,policy
assert policy["next_action_without_wake"].startswith("DO_NOT_SPEND_ADDITIONAL_RETRIEVAL_ACTIONS_ON_THIS_RESIDUAL"),policy

snapshot=frontier["acceptance_snapshot_at_creation_base"]
assert snapshot["snapshot_only"] is True,snapshot
assert snapshot["accepted_families"]=="3_OF_19",snapshot
assert snapshot["proved_atomic_predicates"]=="8_OF_38",snapshot
assert snapshot["terminal_goal_achieved"] is False,snapshot

assert frontier["capability_credit_delta"]==0,frontier
assert frontier["family_credit_delta"]==0,frontier
assert frontier["execution_authority"] is False,frontier
assert frontier["promotion_authority"] is False,frontier
assert intent["capability_credit_delta"]==0,intent
assert intent["family_credit_delta"]==0,intent
assert intent["execution_authority"] is False,intent
assert intent["promotion_authority"] is False,intent

print(json.dumps({
    "status":"PASS",
    "exact_blobs_verified":True,
    "six_class_execution_proved":True,
    "open_domain_scope_preserved":True,
    "apt_scope_mismatch_preserved":True,
    "toolathlon_bridge_candidate_status_preserved":True,
    "opus_matched_gaps_preserved":True,
    "no_result_unknown_firewall_preserved":True,
    "redundant_same_epoch_search_deleted":True,
    "zero_credit_preserved":True,
},sort_keys=True))
