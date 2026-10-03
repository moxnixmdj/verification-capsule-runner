from canonical.runtime.current_26_zero_reality_frontier_v1 import evaluate

x=evaluate()
assert x["pass"] is True, x
w=x["live_world"]
assert w["registry_predicates"]==38
assert w["proved_predicates"]==12
assert w["unresolved_predicates"]==26
assert w["opus55_acceptance"]=="5/19_PASS__14/19_OPEN"
assert w["active_zero_reality_requirements"]==16
assert w["active_nondominated_certificates"]==13
assert w["zero_reality_covered_predicates"]==24
assert w["primitive_zero_reality_work_units"]==30
assert w["matched_priority_child_facts"]==16
assert w["direct_reality_blocked_predicates"]==[
    "FINANCE_UNCOVERED_SCOPE_AUDIT",
    "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",
]
assert "TOOL_DISCOVERY_PROTOCOL_SCOPE_COMPLETENESS_CERTIFICATE" not in x["active_nondominated_certificate_ids"]
assert x["new_reality_units_consumed"]==0
assert x["acceptance_credit_delta"]==0
assert x["family_credit_delta"]==0
assert x["ownership_credit_delta"]==0
assert x["execution_authority"] is False
assert x["promotion_authority"] is False
assert x["fresh_reality_authority"] is False
print("PASS current26 frontier: 12/38 proved, 26 unresolved, 16 reqs, 13 certs, 30 work units")
