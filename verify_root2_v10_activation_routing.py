import json, pathlib, subprocess
BASE="subject/root2_v10_activation_routing_20261004_sol"
FILES={
 "root":f"{BASE}/ROOT_STATE_PRE.json",
 "v10":f"{BASE}/V10.json",
 "v10ver":f"{BASE}/V10_VERIFICATION.json",
 "router":f"{BASE}/ROUTER_V2.json",
 "overlay":f"{BASE}/OVERLAY_V2.json",
 "gate":f"{BASE}/OUTREACH_GATE.json",
 "owner":f"{BASE}/OWNER_FANOUT_V2.json",
 "candidate":f"{BASE}/ACTIVATION_CANDIDATE.json",
}
EXPECTED={
 "root":"e163d8b6fdd86afe9759defb24d920172de12afb",
 "v10":"2012926814d0d06405da56da64e589b06fef1756",
 "v10ver":"226832c5e9d5f4121f26d93bd645ed51dce474fe",
 "router":"4f8a547f1ade8231a705d3d028966c107e805a90",
 "overlay":"e41024fc8588ee5e4292ad38c758c202b1d31d38",
 "gate":"3868d99a7dbddb4a78f9adb5cd083d81cd90241e",
 "owner":"9b59f951f5b7135bb167f2aaebc35e9960172fa4",
 "candidate":"0de6c383030501e5141c754ce821e17a3709bcd7",
}
def blob(p):
 return subprocess.check_output(["git","rev-parse",f"HEAD:{p}"],text=True).strip()
for k,p in FILES.items():
 got=blob(p); assert got==EXPECTED[k],(k,got,EXPECTED[k])
o={k:json.loads(pathlib.Path(p).read_text()) for k,p in FILES.items()}
root,v10,v10ver,router,overlay,gate,owner,cand=[o[k] for k in ("root","v10","v10ver","router","overlay","gate","owner","candidate")]

# Pre-state must still be active V8 and preserve terminal truth.
assert root["current_acceptance"]=={
 "accepted_families":5,"open_families":14,"proved_atomic":12,
 "unresolved_atomic":26,"total_families":19,"total_atomic":38,"terminal":False
}
pre=root["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]
assert pre["current_frontier_path"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V8.json"
assert pre["fresh_reality_authority"] is False
assert root["scheduler_policy"]["low_value_free_tier_trial_quota_support_outreach_forbidden"] is True

# V10 independently verified exact composition.
assert v10ver["subject"]["git_blob_sha"]==EXPECTED["v10"]
assert v10ver["independent_runner"]["conclusion"]=="success"
assert v10ver["verified"]["exact_state_unchanged"] is True
assert v10ver["verified"]["accounting_unchanged"] is True
assert v10ver["verified"]["finance_custom_route_remains_dormant"] is True
assert v10ver["verified"]["tb4_candidates_exactly_buildkite_and_omc"] is True
assert v10ver["verified"]["execution_authority"] is False
assert v10ver["verified"]["promotion_authority"] is False
assert v10ver["verified"]["fresh_reality_authority"] is False
assert v10["exact_state"]=={
 "accepted_families":5,"open_families":14,"proved_atomic":12,
 "unresolved_atomic":26,"root1_positive_gap_count":0,
 "root2_only_count":16,"root3_only_count":7,
 "root2_and_root3_count":3,"root2_touching_predicates":19
}

# Exact 18-fact partition.
wait=set(v10["waiting_external_facts"])
self_service=set(router["self_service_pending_facts"])
owner_ex=set(router["owner_exclusive_or_owner_receipt_facts"])
owner_direct=set(router["owner_or_direct_platform_receipt_facts"])
dormant=set(router["dormant_conditions"])
parts=[self_service,owner_ex,owner_direct,dormant]
for i,a in enumerate(parts):
 for b in parts[i+1:]:
  assert a.isdisjoint(b),(a & b)
union=set().union(*parts)
assert union==wait,{"missing":sorted(wait-union),"extra":sorted(union-wait)}
assert [len(x) for x in parts]==[9,6,1,2]
assert len(wait)==18

# OMC trial/runtime facts are self-service only.
omc={
 "OMC_CLOUD_TRIAL_ACCOUNT_AND_EXACT_8A16GB_OR_STRONGER_SHAPE_ACCESS",
 "OMC_CLOUD_OBSERVED_NPROC_GE_8_USABLE_MEMORY_MB_GE_16384_FREE_STORAGE_MB_GE_51200",
 "OMC_CLOUD_DOCKER_DOCKER_COMPOSE_NO_PAID_OVERAGE_AND_HARBOR_PROTOCOL_PREFLIGHT",
}
assert omc.issubset(self_service)
assert omc.isdisjoint(owner_ex|owner_direct|dormant)

# Dormant cuts and owner wake are exactly preserved.
assert "CURSOR_POLICY_CHANGE_OR_STRONGER_PROOF" in dormant
assert "FINANCE_AGENT_V2_CUSTOM_FUNCTION_COMPARABILITY_TO_PUBLISHED_SHARED_DEFAULT_HARNESS" in dormant
assert "VALS_OWNER_CUSTOM_HARNESS_COMPARABILITY_ACCEPTANCE_OR_PRIMARY_METHODOLOGY_CHANGE" in owner_ex

# Anti-wishful outreach invariant persists.
assert "NO_EMAIL_WHOSE_LOAD_BEARING_CONTENT_IS_ONLY_A_FREE_TRIAL_FREE_TIER_FREE_QUOTA_FREE_CREDIT_OR_BASIC_SUPPORT_QUERY" in gate["hard_rules"]
assert "NO_FREE_TRIAL_FREE_QUOTA_FREE_CREDIT_OR_BASIC_SUPPORT_OUTREACH" in router["hard_rules"]
assert "OMC_TRIAL_FACTS_ARE_SELF_SERVICE_ONLY__NO_PROVIDER_OUTREACH" in router["hard_rules"]
assert "NO_DUPLICATE_VALS_COMPARABILITY_EMAIL__EXISTING_OWNER_QUESTION_IS_THE_ONLY_ACTIVE_OWNER_WAKE" in router["hard_rules"]

# Overlay binds exact pieces and preserves zero credit.
assert overlay["parent_frontier"]["git_blob_sha"]==EXPECTED["v10"]
assert overlay["parent_verification"]["git_blob_sha"]==EXPECTED["v10ver"]
assert overlay["components"]["outreach_gate"]["git_blob_sha"]==EXPECTED["gate"]
assert overlay["components"]["fact_router"]["git_blob_sha"]==EXPECTED["router"]
assert overlay["components"]["owner_fanout"]["git_blob_sha"]==EXPECTED["owner"]
assert overlay["invariant_partition_counts"]=={
 "v10_waiting_external_fact_count":18,"self_service":9,
 "owner_exclusive_or_owner_receipt":6,"owner_or_direct_platform_receipt":1,
 "dormant":2,"sum":18
}
assert overlay["accounting"]=={
 "incremental_spend_usd":0,"new_reality_units_consumed":0,"terminal_cases_consumed":0,
 "acceptance_credit_delta":0,"family_credit_delta":0,
 "capability_credit_delta":0,"ownership_credit_delta":0
}
assert overlay["execution_authority"] is False and overlay["promotion_authority"] is False and overlay["fresh_reality_authority"] is False

# Activation candidate requests scheduling only, preserves everything else.
assert cand["frontier"]["git_blob_sha"]==EXPECTED["v10"]
assert cand["frontier_verification"]["git_blob_sha"]==EXPECTED["v10ver"]
assert cand["acquisition_overlay"]["git_blob_sha"]==EXPECTED["overlay"]
assert cand["authority_before_terminal_binding"]=={
 "scheduling":False,"effective_scheduling":False,"execution":False,"promotion":False,"fresh_reality":False
}
assert cand["requested_terminal_authority"]=={
 "scheduling":True,"effective_scheduling":True,"execution":False,"promotion":False,"fresh_reality":False
}
assert cand["accounting"]=={
 "incremental_spend_usd":0,"new_reality_units_consumed":0,"terminal_cases_consumed":0,
 "acceptance_credit_delta":0,"family_credit_delta":0,
 "capability_credit_delta":0,"ownership_credit_delta":0
}

print("PASS: verified V10 strictly composes Finance V9 + one OMC TB4 documentary delta with state unchanged")
print("PASS: all 18 V10 external facts partition exactly 9 self-service + 6 owner + 1 owner/direct + 2 dormant")
print("PASS: OMC trial/runtime facts are self-service only; no free-trial/support outreach")
print("PASS: V10 activation candidate requests scheduling authority only; zero credit; no fresh reality")
