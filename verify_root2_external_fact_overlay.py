import json, pathlib, subprocess

BASE="subject/root2_external_fact_overlay_20261004_sol"
FILES={
  "v8":f"{BASE}/V8.json",
  "v8ver":f"{BASE}/V8_VERIFICATION.json",
  "v8act":f"{BASE}/V8_ACTIVATION.json",
  "gate":f"{BASE}/OUTREACH_GATE.json",
  "router":f"{BASE}/FACT_ROUTER.json",
  "fanout":f"{BASE}/OWNER_FANOUT_V2.json",
  "overlay":f"{BASE}/OVERLAY.json",
}
EXPECTED={
  "v8":"2eaeb74fe306ee2507145e26eb731f69f46e6153",
  "v8ver":"7e2d71144853c41fadab55f4074d484edf46e651",
  "v8act":"e0c0b2a25e764c875e4af4cffb3a61f05a7a58bc",
  "gate":"3868d99a7dbddb4a78f9adb5cd083d81cd90241e",
  "router":"3833d97f1febbdc1766182778b3c4ba23c9daa85",
  "fanout":"9b59f951f5b7135bb167f2aaebc35e9960172fa4",
  "overlay":"ebbfd05e58abc398a50998f9b9e4bdedacf205e1",
}

def blob(path):
    return subprocess.check_output(["git","rev-parse",f"HEAD:{path}"],text=True).strip()

for k,p in FILES.items():
    got=blob(p)
    assert got==EXPECTED[k], (k,got,EXPECTED[k])

objs={k:json.loads(pathlib.Path(p).read_text()) for k,p in FILES.items()}
v8,v8ver,v8act=objs["v8"],objs["v8ver"],objs["v8act"]
gate,router,fanout,overlay=objs["gate"],objs["router"],objs["fanout"],objs["overlay"]

# Active parent must be independently verified scheduling-only authority.
assert v8ver["independent_runner"]["conclusion"]=="success"
assert v8ver["subject"]["git_blob_sha"]==EXPECTED["v8"]
assert v8act["frontier"]["git_blob_sha"]==EXPECTED["v8"]
assert v8act["verification"]["git_blob_sha"]==EXPECTED["v8ver"]
assert v8act["authority"]=={
    "scheduling":True,"effective_scheduling":True,
    "execution":False,"promotion":False,"fresh_reality":False
}
assert v8["exact_state"]=={
    "accepted_families":5,"open_families":14,"proved_atomic":12,
    "unresolved_atomic":26,"root1_positive_gap_count":0,
    "root2_only_count":16,"root3_only_count":7,
    "root2_and_root3_count":3,"root2_touching_predicates":19
}

# Exact partition of every active V8 external fact.
wait=set(v8["waiting_external_facts"])
self_service=set(router["self_service_pending_facts"])
owner=set(router["owner_exclusive_or_owner_receipt_facts"])
owner_direct=set(router["owner_or_direct_platform_receipt_facts"])
dormant=set(router["dormant_conditions"])
parts=[self_service,owner,owner_direct,dormant]
for i,a in enumerate(parts):
    for b in parts[i+1:]:
        assert a.isdisjoint(b), (a & b)
union=set().union(*parts)
assert union==wait, {"missing":sorted(wait-union),"extra":sorted(union-wait)}
assert [len(x) for x in parts]==[6,6,1,1]
assert len(wait)==14

# User-mandated anti-wishful-outreach invariant.
assert "NO_EMAIL_WHOSE_LOAD_BEARING_CONTENT_IS_ONLY_A_FREE_TRIAL_FREE_TIER_FREE_QUOTA_FREE_CREDIT_OR_BASIC_SUPPORT_QUERY" in gate["hard_rules"]
assert "NO_SUPPORT_EMAIL_WHEN_THE_FACT_CAN_BE_MECHANICALLY_OBSERVED_WITH_ZERO_CASE_PREFLIGHT_OR_ACCOUNT_STATE" in gate["hard_rules"]
assert "AN_ALREADY_SENT_LOW_VALUE_EMAIL_MUST_NOT_CREATE_A_WAIT_DEPENDENCY" in gate["hard_rules"]

buildkite="BUILDKITE_RUNTIME_DISK_DOCKER_HARD_STOP_AND_PROTOCOL_PREFLIGHT"
cursor="CURSOR_POLICY_CHANGE_OR_STRONGER_PROOF"
assert buildkite in self_service and buildkite not in owner and buildkite not in owner_direct
assert cursor in dormant and cursor not in owner

# Owner fanout preserves only load-bearing owner-exclusive channels; Buildkite support is historical/nonblocking.
reclass=fanout["channel_reclassification"]
assert set(reclass["preserved_owner_exclusive"])=={"Artificial Analysis","Vals AI","Cognition","Zapier"}
assert reclass["closed"]==["Cursor"]
assert fanout["deduplication"]["self_service_support_channels_waiting"]==0
bk=[x for x in fanout["already_sent_nonblocking_support_threads"] if x["provider"]=="Buildkite"]
assert len(bk)==1
assert bk[0]["state"]=="HISTORICAL_SENT__REPLY_OPTIONAL__NOT_A_SCHEDULING_DEPENDENCY"
assert bk[0]["replacement_action"]=="SELF_SERVICE_ACCOUNT_AND_ZERO_CASE_PREFLIGHT"

# Overlay must bind exact components and preserve terminal accounting/authority.
assert overlay["active_parent"]["frontier_git_blob_sha"]==EXPECTED["v8"]
assert overlay["active_parent"]["verification_git_blob_sha"]==EXPECTED["v8ver"]
assert overlay["active_parent"]["activation_git_blob_sha"]==EXPECTED["v8act"]
assert overlay["components"]["outreach_gate"]["git_blob_sha"]==EXPECTED["gate"]
assert overlay["components"]["fact_router"]["git_blob_sha"]==EXPECTED["router"]
assert overlay["components"]["owner_fanout"]["git_blob_sha"]==EXPECTED["fanout"]
assert overlay["invariant_partition_counts"]=={
    "active_v8_waiting_external_fact_count":14,
    "self_service":6,
    "owner_exclusive_or_owner_receipt":6,
    "owner_or_direct_platform_receipt":1,
    "dormant":1,
    "sum":14
}
assert overlay["accounting"]=={
    "incremental_spend_usd":0,"new_reality_units_consumed":0,
    "terminal_cases_consumed":0,"acceptance_credit_delta":0,
    "family_credit_delta":0,"capability_credit_delta":0,
    "ownership_credit_delta":0
}
assert overlay["execution_authority"] is False
assert overlay["promotion_authority"] is False
assert overlay["fresh_reality_authority"] is False

print("PASS: active V8 external facts partition exactly 6 self-service + 6 owner-exclusive + 1 owner/direct + 1 dormant")
print("PASS: low-value free-tier/trial/quota/basic-support outreach is not a scheduling dependency")
print("PASS: Buildkite support thread is historical/nonblocking; self-service zero-case preflight is the replacement")
print("PASS: Cursor is dormant, owner route closed")
print("PASS: terminal truth remains 5/19 families, 12/38 predicates, 26 unresolved; zero credit; no fresh reality")
