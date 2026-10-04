import hashlib,json
from pathlib import Path
p=Path(__file__).with_name("ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V6.json")
b=p.read_bytes()
assert hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()=="fcbdb818b63b4986b026db29c400a47373a26fdb"
o=json.loads(b)
assert o["schema"]=="PROJECT_BRAIN_ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V6"
s=o["exact_state"]
assert (s["accepted_families"],s["open_families"],s["proved_atomic"],s["unresolved_atomic"])==(5,14,12,26)
assert (s["root2_only_count"],s["root3_only_count"],s["root2_and_root3_count"],s["root2_touching_predicates"])==(16,7,3,19)
fi=o["source_bindings"]["finance_index_direct_threshold_activation"]
assert fi["git_blob_sha"]=="9b9d4a41d19a5e58e8967027e1d1837790287dc2"
assert fi["verification_git_blob_sha"]=="f7c1127834aee3c70dc4634e8273e3a887e45c66"
fa=o["source_bindings"]["finance_agent_v2_heldout_mass"]
assert fa["git_blob_sha"]=="ec36936e92a6111aed6b1813a45225fb4ca867dc"
assert fa["verification_git_blob_sha"]=="cbdc6b3e773e86a1e57e119a6dd2c690ee1c6b11"
r=o["runnable_zero_reality"]
assert "FINANCE_INDEX_MINIMIZE_VERIFIED_NORMALIZED_WEIGHTED_LOWER_BOUND_DEFICIT_TO_61" in r
assert "FINANCE_COMPONENTWISE_PREMISES_AND_NORMALIZATION_AGGREGATION" not in r
assert "FINANCE_AGENT_V2_VALS_APPROVAL_EXACT_SUITE_ID_CUSTOM_HARNESS_AND_1350_EXECUTION_FREE_TOOL_USAGE_FEASIBILITY" in r
w=o["waiting_external_facts"]
assert "FINANCE_AGENT_V2_1350_EXECUTION_TAVILY_SEC_API_TIINGO_FREE_USAGE_FEASIBILITY" in w
assert o["accounting"]["incremental_spend_usd"]==0
assert o["accounting"]["terminal_cases_consumed"]==0
assert o["accounting"]["acceptance_credit_delta"]==0
assert o["fresh_reality_authority"] is False
assert o["promotion_authority"] is False
assert o["execution_authority"] is False
print("PASS__EXACT_V6_BLOB__COUNTS_STABLE__FINANCE_THRESHOLD_COMPRESSED__FA1350_BOUND__ZERO_CREDIT")
