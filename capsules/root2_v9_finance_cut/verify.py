import hashlib,json
from pathlib import Path
p=Path(__file__).with_name("ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V9.json")
b=p.read_bytes()
assert hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()=="ea5923e8a90ca115c8149266c4c37cc7e6c40a2a"
o=json.loads(b)
assert o["schema"]=="PROJECT_BRAIN_ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V9"
assert o["exact_state"]["accepted_families"]==5
assert o["exact_state"]["unresolved_atomic"]==26
assert o["accounting"]["incremental_spend_usd"]==0
assert o["accounting"]["terminal_cases_consumed"]==0
assert o["accounting"]["acceptance_credit_delta"]==0
assert o["fresh_reality_authority"] is False
assert o["promotion_authority"] is False
assert "FINANCE_AGENT_V2_CUSTOM_ROUTE__COMPARABILITY_AND_VALS_PLATFORM_JURY_ZERO_SPEND_PROOF" not in o["runnable_zero_reality"]
assert "VALS_OWNER_CUSTOM_HARNESS_COMPARABILITY_ACCEPTANCE_OR_PRIMARY_METHODOLOGY_CHANGE" in o["waiting_external_facts"]
c=o["finance_agent_v2_dual_route"]["custom_function"]
assert c["state"]=="DORMANT__PUBLIC_COMPARABILITY_ROUTE_SATURATED"
d=o["finance_agent_v2_dual_route"]["default_shared_harness"]
assert d["state"].startswith("OPEN__")
print("PASS__EXACT_V9_BLOB__DEFAULT_ROUTE_PRESERVED__CUSTOM_ROUTE_DORMANT__ZERO_CREDIT")
