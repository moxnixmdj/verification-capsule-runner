import copy
import json
import pathlib
import subprocess

BASE="subject/root2_v8_current_v7_20261004_sol"
FILES={
 "v7":f"{BASE}/V7.json",
 "v7ver":f"{BASE}/V7_VERIFICATION.json",
 "v7act":f"{BASE}/V7_ACTIVATION.json",
 "v8":f"{BASE}/V8.json",
 "custom":f"{BASE}/CUSTOM_ROUTE.json",
 "customver":f"{BASE}/CUSTOM_ROUTE_VERIFICATION.json",
}
EXPECTED={
 "v7":"35e8b578aca1290bcf469d6350ae085ba8a86c64",
 "v7ver":"c2b96c9d48b7ef6508ea77dc6983da12eaf099c3",
 "v7act":"ccfc97ca8f5586d583990f0e37277b88c12227e9",
 "v8":"2eaeb74fe306ee2507145e26eb731f69f46e6153",
 "custom":"79a60cb1c407fdabe68643ca91fcc2836ea000b1",
 "customver":"01eeac7d1d096d7dcbb1e401e013d85d8d4aaaa3",
}
def blob(p):
    return subprocess.check_output(["git","rev-parse",f"HEAD:{p}"],text=True).strip()
for k,p in FILES.items():
    got=blob(p)
    assert got==EXPECTED[k], (k,got,EXPECTED[k])

v7=json.loads(pathlib.Path(FILES["v7"]).read_text())
v7ver=json.loads(pathlib.Path(FILES["v7ver"]).read_text())
v7act=json.loads(pathlib.Path(FILES["v7act"]).read_text())
v8=json.loads(pathlib.Path(FILES["v8"]).read_text())
custom=json.loads(pathlib.Path(FILES["custom"]).read_text())
customver=json.loads(pathlib.Path(FILES["customver"]).read_text())

# Current V7 authority must be independently verified and scheduling-only.
assert v7ver["status"]=="INDEPENDENT_PUBLIC_RUNNER_PASS__ZERO_CREDIT__NO_FRESH_REALITY"
assert v7ver["subject_git_blob_sha"]==EXPECTED["v7"]
assert v7ver["verifier"]["conclusion"]=="success"
assert v7ver["counts"]=={"accepted_families":5,"proved_atomic":12,"unresolved_atomic":26,"root2_touching":19}
assert v7ver["authority"]=={"scheduling_only":True,"execution":False,"promotion":False,"fresh_reality":False}
assert v7act["status"]=="ACTIVE__INDEPENDENT_PASS__SCHEDULING_ONLY__ZERO_CREDIT"
assert v7act["frontier_git_blob_sha"]==EXPECTED["v7"]
assert v7act["verification_git_blob_sha"]==EXPECTED["v7ver"]
assert v7act["authority"]=={"scheduling":True,"effective_scheduling":True,"execution":False,"promotion":False,"fresh_reality":False}

# V8 must bind exact active V7 parent and exact independently verified custom route.
assert v8["supersedes_for_scheduling_if_verified"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V7.json"
parent=v8["source_bindings"]["active_parent_v7"]
assert parent=={
 "path":"canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V7.json",
 "git_blob_sha":EXPECTED["v7"],
 "verification_path":"canonical/verification/ROOT2_FRONTIER_V7_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json",
 "verification_git_blob_sha":EXPECTED["v7ver"],
 "activation_path":"canonical/governance/ROOT2_FRONTIER_V7_ACTIVATION_V1.json",
 "activation_git_blob_sha":EXPECTED["v7act"],
 "state":"ACTIVE_CURRENT_PARENT",
}
src=v8["source_bindings"]["finance_agent_v2_custom_function_alternative_route"]
assert src["git_blob_sha"]==EXPECTED["custom"]
assert src["verification_git_blob_sha"]==EXPECTED["customver"]

assert customver["independent_verifier"]["conclusion"]=="success"
assert "CUSTOM_FUNCTION_EXISTENCE_ALONE_DOES_NOT_PROVE_COMPARABILITY" in customver["verified"]
assert "CUSTOM_FUNCTION_ROUTE_IS_CONDITIONAL_ON_COMPARABILITY_AND_PLATFORM_ZERO_SPEND" in customver["verified"]
assert "NO_CLAIM_CUSTOM_FUNCTION_SCORE_IS_CURRENTLY_COMPARABLE" in customver["hard_nonclaims"]
assert "NO_CLAIM_VALS_PLATFORM_EXECUTION_IS_FREE" in customver["hard_nonclaims"]

# State/accounting are identical.
assert v8["exact_state"]==v7["exact_state"]
assert v8["accounting"]==v7["accounting"]
for obj in (v7,v8,custom,customver):
    assert obj["execution_authority"] is False
    assert obj["promotion_authority"] is False
    assert obj["fresh_reality_authority"] is False

# All V7 deltas must be byte-semantically preserved; V8 adds exactly one.
v7d={(x["target"],x["deletion"]):x for x in v7["projection_deltas"]}
v8d={(x["target"],x["deletion"]):x for x in v8["projection_deltas"]}
for k,x in v7d.items():
    assert k in v8d and v8d[k]==x, k
extra=[x for x in v8["projection_deltas"] if (x["target"],x["deletion"]) not in v7d]
assert len(extra)==1, extra
x=extra[0]
assert x["target"]=="FINANCE_AGENT_V2_GE_58_59"
assert x["deletion"]=="DEFAULT_TAVILY_SEC_API_TIINGO_STACK_AS_UNIQUE_TECHNICAL_VALS_SUITE_EXECUTION_ROUTE"
assert "CUSTOM_ROUTE_COMPARABILITY" in x["reason"]

# Default route remains open; custom route is conditional.
dual=v8["finance_agent_v2_dual_route"]
assert dual["default_shared_harness"]["state"]=="OPEN__ZERO_SPEND_GUARD_AND_RETRY_SAFE_ADAPTER_VERIFIED"
assert dual["custom_function"]["state"]=="CONDITIONALLY_OPEN__ROUTE_EXISTENCE_INDEPENDENTLY_VERIFIED"
assert "CUSTOM_FUNCTION_OR_CUSTOM_HARNESS_COMPARABILITY_TO_PUBLISHED_SHARED_DEFAULT_HARNESS_VERIFIED" in dual["custom_function"]["requires"]
assert "VALS_PLATFORM_AND_EVALUATOR_JURY_ZERO_INCREMENTAL_SPEND_RECEIPT_OR_OWNER_NO_COST_ROUTE" in dual["custom_function"]["requires"]
assert dual["route_selection_rule"]=="PROMOTE_FIRST_FULLY_ADMISSIBLE_ZERO_INCREMENTAL_SPEND_COMPARABLE_ROUTE__DO_NOT_MERGE_SCORE_EVIDENCE_ACROSS_NONCOMPARABLE_HARNESSES"

for req in (
 "CURRENT_FREE_ONLY_ACCOUNT_SNAPSHOT_TAVILY",
 "CURRENT_FREE_ONLY_ACCOUNT_SNAPSHOT_SEC_API",
 "CURRENT_FREE_ONLY_ACCOUNT_SNAPSHOT_TIINGO",
 "ZERO_COST_OUTCOME_TELEMETRY_BINDING",
):
    assert req in dual["default_shared_harness"]["requires"]

for fact in (
 "FINANCE_AGENT_V2_CUSTOM_FUNCTION_COMPARABILITY_TO_PUBLISHED_SHARED_DEFAULT_HARNESS",
 "FINANCE_AGENT_V2_VALS_PLATFORM_AND_EVALUATOR_JURY_ZERO_INCREMENTAL_SPEND_ROUTE",
):
    assert fact in v8["waiting_external_facts"]

for rule in (
 "NO_FINANCE_AGENT_V2_CUSTOM_FUNCTION_SCORE_COMPARABILITY_INFERENCE_FROM_GENERIC_VALS_SDK_SUPPORT_ALONE",
 "NO_FINANCE_AGENT_V2_DEFAULT_PROVIDER_QUOTA_ROUTE_DELETION_UNTIL_CUSTOM_FUNCTION_COMPARABILITY_IS_VERIFIED",
 "NO_FINANCE_AGENT_V2_VALS_PLATFORM_OR_JURY_ZERO_SPEND_ASSUMPTION_WITHOUT_RECEIPT_OR_OWNER_CONFIRMATION",
):
    assert rule in v8["hard_rules"]

# No semantic drift outside the admitted current-parent/custom-route fields.
norm=copy.deepcopy(v8)
norm["schema"]=v7["schema"]
norm["status"]=v7["status"]
norm["supersedes_for_scheduling_if_verified"]=v7["supersedes_for_scheduling_if_verified"]
norm["source_bindings"].pop("active_parent_v7",None)
norm["source_bindings"].pop("finance_agent_v2_custom_function_alternative_route",None)
norm["projection_deltas"]=v7["projection_deltas"]
norm["runnable_zero_reality"]=v7["runnable_zero_reality"]
norm["waiting_external_facts"]=v7["waiting_external_facts"]
norm["hard_rules"]=v7["hard_rules"]
norm.pop("finance_agent_v2_dual_route",None)
assert norm==v7, "V8 contains drift beyond the one admitted custom-route scheduling delta"

print("PASS: active verified V7 -> V8 is exactly one conditional Finance Agent custom-function route")
print("PASS: default zero-spend harness remains intact and mandatory unless custom comparability is proven")
print("PASS: custom comparability and Vals platform/jury zero-spend remain open")
print("PASS: 5/19 families, 12/38 predicates, 26 unresolved; zero credit; no fresh reality")
