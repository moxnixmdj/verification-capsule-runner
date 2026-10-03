import hashlib,json,pathlib
R=pathlib.Path(__file__).resolve().parent
def load(n): return json.loads((R/n).read_text())
def blob(n):
 b=(R/n).read_bytes()
 return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
EXPECTED={
 "candidate.json":"e9f0b028eeb6b1a36384bfc4f814f38a5ca79aa2",
 "postdual_verification.json":"f7f60a5932ac305aa0db8aef2643119dd10b33d9",
 "v4_activation_verification.json":"e35dc954e0cf892d5522e62b5948bb64edeed4f7",
 "v4_live_gate_verification.json":"ebb4ab1a05e47e20ecfacba41eb99d1f5c71694d",
}
for p,h in EXPECTED.items(): assert blob(p)==h,(p,blob(p),h)
c=load("candidate.json"); post=load("postdual_verification.json"); a=load("v4_activation_verification.json"); live=load("v4_live_gate_verification.json")
assert str(post["status"]).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
pv=post["verified"]
assert (pv["current_zero_reality_requirements"],pv["current_nondominated_zero_reality_certificates"],pv["zero_reality_covered_predicates"],pv["primitive_zero_reality_work_units"],pv["matched_priority_child_facts"])==(17,14,25,31,16)
assert pv["current_global_fresh_reality_authority"] is False
assert str(a["status"]).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert str(live["status"]).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
lv=live["verified"]
for k in ["exact_dependency_chain_verified","v2_and_v3_base_authority_preserved","v4_activation_mandatory_in_live_gate","v4_federated_router_receipts_mandatory","unknown_preserved","epoch_consumption_nonexistence_inference_forbidden","zero_credit_preserved"]:
 assert lv[k] is True,k
w=c["live_world"]
assert (w["registry_predicates"],w["proved_predicates"],w["unresolved_predicates"],w["active_zero_reality_requirements"],w["active_nondominated_certificates"],w["zero_reality_covered_predicates"],w["primitive_zero_reality_work_units"],w["matched_priority_child_facts"])==(38,11,27,17,14,25,31,16)
assert w["opus55_acceptance"]=="4/19_PASS__15/19_OPEN"
assert w["direct_reality_blocked_predicates"]==["FINANCE_UNCOVERED_SCOPE_AUDIT","UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"]
td=c["mandatory_tool_discovery_retrieval"]
assert td["authority"]=="V4_OVER_VERIFIED_V3_OVER_VERIFIED_V2_BASE"
assert td["mandatory"] is True and td["diversity_preserving_federation_required"] is True
assert td["one_router_attempt_receipt_per_selected_cell_required"] is True
assert td["backend_unbound_counts_as_attempt"] is False
assert td["empty_or_failed_attempt_proves_nonexistence"] is False
assert td["consumed_source_epoch_replay_allowed"] is False
for k in ["new_reality_units_consumed","incremental_spend_usd","acceptance_credit_delta","capability_credit_delta","family_credit_delta","ownership_credit_delta"]: assert c[k]==0,k
for k in ["execution_authority","promotion_authority","fresh_reality_authority"]: assert c[k] is False,k
print("PASS V12 exact post-dual + Retrieval V4 zero-credit scheduling")
