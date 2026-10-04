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


# V6 activation coherence
EXP={
 "root_authority.json":"78f70dc63654b7d4be0917fce9405088177a48b5",
 "measurement_bridge.json":"88170a3c3f9fd84e21d9d32142967024c79cd95a",
 "terminal_authority.json":"d791f7306efdcb57a4544e8631fcd64e0b0951d3",
 "activation.json":"9a0ef849b74faa26c07d94035c8455eee8777cdd",
}
def blob2(name):
    p=Path(__file__).with_name(name); b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
for n,h in EXP.items(): assert blob2(n)==h,(n,blob2(n),h)
root=json.loads(Path(__file__).with_name("root_authority.json").read_text())
bridge=json.loads(Path(__file__).with_name("measurement_bridge.json").read_text())
term=json.loads(Path(__file__).with_name("terminal_authority.json").read_text())
act=json.loads(Path(__file__).with_name("activation.json").read_text())
FRONTIER="fcbdb818b63b4986b026db29c400a47373a26fdb"
ACT="9a0ef849b74faa26c07d94035c8455eee8777cdd"
ra=root["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]
ba=bridge["root2_closure_controller_v2"]
ta=term["sources"]["root2_closure_v2_current_frontier"]
assert ra["current_frontier_git_blob_sha"]==FRONTIER
assert ba["frontier_git_blob_sha"]==FRONTIER
assert ta["git_blob_sha"]==FRONTIER
assert ra["current_frontier_activation_git_blob_sha"]==ACT
assert ba["frontier_activation_git_blob_sha"]==ACT
assert ta["activation_git_blob_sha"]==ACT
assert ra["effective_scheduling_authority"] is True
assert ba["effective_scheduling_authority"] is True
assert ta["effective_scheduling_authority"] is True
assert act["authority"]["execution_authority"] is False
assert act["authority"]["promotion_authority"] is False
assert act["authority"]["fresh_reality_authority"] is False
assert root["current_acceptance"]["accepted_families"]==5
assert root["current_acceptance"]["proved_atomic"]==12
assert root["current_acceptance"]["unresolved_atomic"]==26
print("PASS__ROOT2_V6_ACTIVATION_COHERENT__SCHEDULING_ONLY__ZERO_CREDIT")
