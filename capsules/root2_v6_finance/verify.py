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


# Finance Agent v2 zero-spend harness adapter
import os, subprocess, sys
A=Path(__file__).with_name("adapter")
def blob3(p):
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

EXPECTED_ADAPTER={
 "canonical/runtime/finance_agent_v2_zero_spend_adapter_v1.py":"c90d2e693621ae0a268e3c4f96bbdbfdcc827ec2",
 "canonical/runtime/zero_spend_provider_guard_v1.py":"356af559fc74ac3eab5532b2d8fee9ddfb98f962",
 "canonical/tests/test_finance_agent_v2_zero_spend_adapter_v1.py":"81d49edb2e7d265a14d2780eb8cad7b6adcb6435",
 "FINANCE_AGENT_V2_ZERO_SPEND_HARNESS_ADAPTER_V1.json":"280fc9b41221f6b4fa58ac50b18a0a4d6fceb5ec",
 "upstream/tools.py":"19b85ce4e110e39f410c52b2efa0e33f651fa6d1",
 "upstream/get_agent.py":"22c012241a430975266fb7f8d2fe7af8e9f1b8d4",
}
for rel,h in EXPECTED_ADAPTER.items():
    got=blob3(A/rel)
    assert got==h,(rel,h,got)

tools_src=(A/"upstream/tools.py").read_text()
get_agent_src=(A/"upstream/get_agent.py").read_text()
assert "response = await self.client.search(" in tools_src
assert 'self.sec_api_url: str = "https://api.sec-api.io/full-text-search"' in tools_src
assert "async with session.post(" in tools_src and "self.sec_api_url" in tools_src
assert 'EQUITY_URL = "https://api.tiingo.com/tiingo/daily/{ticker}/prices"' in tools_src
assert "async with session.get(" in tools_src
assert '"web_search": TavilyWebSearch' in get_agent_src
assert '"edgar_search": EDGARSearch' in get_agent_src
assert '"price_history": PriceHistory' in get_agent_src

gov=json.loads((A/"FINANCE_AGENT_V2_ZERO_SPEND_HARNESS_ADAPTER_V1.json").read_text())
assert gov["brain_subject"]["adapter_runtime"]["git_blob_sha"]==EXPECTED_ADAPTER["canonical/runtime/finance_agent_v2_zero_spend_adapter_v1.py"]
assert gov["exact_upstream_source"]["tools_py_git_blob_sha"]==EXPECTED_ADAPTER["upstream/tools.py"]
assert gov["exact_upstream_source"]["get_agent_py_git_blob_sha"]==EXPECTED_ADAPTER["upstream/get_agent.py"]
assert gov["fresh_reality_authority"] is False
assert gov["accounting"]["acceptance_credit_delta"]==0

env=dict(os.environ)
env["PYTHONPATH"]=str(A)
cp=subprocess.run(
    [sys.executable,"-m","unittest","-v","canonical.tests.test_finance_agent_v2_zero_spend_adapter_v1"],
    cwd=A,
    env=env,
    text=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
)
print(cp.stdout)
assert cp.returncode==0,cp.stdout
print("PASS__FINANCE_AGENT_ZERO_SPEND_ADAPTER__EXACT_VALS_BOUNDARIES__RETRY_SAFE__UNIT_TESTS_PASS__ZERO_CREDIT")
