import hashlib,json
from pathlib import Path
p=Path(__file__).with_name("ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V10.json")
b=p.read_bytes()
assert hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()=="a5a77b44abb44fc7f047db0f3bc3ed6a504f5e2b"
o=json.loads(b)
assert o["schema"]=="PROJECT_BRAIN_ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V10"
assert o["exact_state"]["accepted_families"]==5
assert o["exact_state"]["unresolved_atomic"]==26
w=o["waiting_external_facts"]
assert len(w)==14 and len(set(w))==14
old="FINANCE_AGENT_V2_CUSTOM_FUNCTION_COMPARABILITY_TO_PUBLISHED_SHARED_DEFAULT_HARNESS"
new="VALS_OWNER_CUSTOM_HARNESS_COMPARABILITY_ACCEPTANCE_OR_PRIMARY_METHODOLOGY_CHANGE"
assert old not in w and new in w
x=o["external_fact_acquisition"]
assert x["total_waiting_external_facts"]==14
assert x["counts"]=={"self_service":6,"owner_exclusive_or_owner_receipt":6,"owner_or_direct_platform_receipt":1,"dormant":1,"sum":14}
flat=x["self_service"]+x["owner_exclusive_or_owner_receipt"]+x["owner_or_direct_platform_receipt"]+x["dormant"]
assert len(flat)==14 and len(set(flat))==14 and set(flat)==set(w)
assert o["accounting"]["incremental_spend_usd"]==0
assert o["accounting"]["terminal_cases_consumed"]==0
assert o["accounting"]["acceptance_credit_delta"]==0
assert o["execution_authority"] is False
assert o["promotion_authority"] is False
assert o["fresh_reality_authority"] is False
print("PASS__EXACT_V10_BLOB__14_UNIQUE_EXTERNAL_FACTS__6_6_1_1_PARTITION__STALE_WAIT_DELETED__ZERO_CREDIT")
