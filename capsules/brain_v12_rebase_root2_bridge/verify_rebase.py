from __future__ import annotations
import hashlib,json,pathlib,urllib.request
ROOT=pathlib.Path(__file__).resolve().parent
AUTH={"LIVEBENCH_IF_GE_65_7","TB_SCIENCE_GE_58_7"}

def load(p): return json.loads((ROOT/p).read_text(encoding="utf-8"))
m=load("EXPECTED_BRAIN_BLOBS.json")
for rel,expected in m["exact_brain_blobs"].items():
    b=(ROOT/rel).read_bytes()
    got=hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
    assert got==expected,(rel,got,expected)

bridge=load("canonical/governance/ROOT2_MEASUREMENT_BRIDGE_CURRENT_V1.json")
v12=load("canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V12.json")
act=load("canonical/governance/LOCAL_ZERO_REALITY_FIXED_POINT_ACTIVATION_V1.json")
ptr=load("canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_ACTIVE_POINTER_V1.json")
term=load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")
mx=load("canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json")
finalvr=load("canonical/verification/CURRENT_ZERO_REALITY_MINIMUM_CUT_V12_FINAL_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json")

# The unrelated Root2 bridge survived exactly and remains zero-credit/fail-closed.
assert bridge["schema"]=="PROJECT_BRAIN_ROOT2_MEASUREMENT_BRIDGE_CURRENT_V1"
assert bridge["status"].startswith("ACTIVE_ZERO_CREDIT")
assert bridge["incremental_spend_usd"]==0
assert bridge["terminal_cases_consumed"]==0
assert bridge["acceptance_credit_delta"]==0
assert bridge["execution_authority"] is False
assert bridge["promotion_authority"] is False
assert bridge["fresh_reality_authority"] is False

# Previously verified V12 activation blobs are byte-identical.
assert m["exact_brain_blobs"]["canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V12.json"]=="755bf5efce7e7e5f6b1c0462eb824755ab8c3138"
assert m["exact_brain_blobs"]["canonical/governance/LOCAL_ZERO_REALITY_FIXED_POINT_ACTIVATION_V1.json"]=="af0bd9cf557b5b2628d9183e4bda1b2b90eabce4"
assert m["exact_brain_blobs"]["canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_ACTIVE_POINTER_V1.json"]=="7dc4c1aeeefb5ee426ac6463fbecf6bbee7aa8f2"
assert m["exact_brain_blobs"]["canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json"]=="0915f33a318bf4c8bbeef95f7758e8c8552b9c20"
assert m["exact_brain_blobs"]["canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json"]=="f690c5d99f9e9c43d36fbe47c6cc921f776f3bb5"

assert v12["exact_state"]["accepted_families"]==5
assert v12["exact_state"]["proved_atomic"]==12
assert v12["exact_state"]["unresolved_atomic"]==26
assert v12["exact_state"]["terminal"] is False
assert v12["global_fresh_reality_authority"] is False
assert set(v12["scoped_authorized_predicates"])==AUTH
assert act["global_fresh_reality_authority"] is False
assert set(act["scoped_authorized_predicates"])==AUTH
assert ptr["global_fresh_reality_authority"] is False
assert set(ptr["scoped_authorized_predicates"])==AUTH
assert term["truth"]["achieved"] is False
assert set(term["local_fixed_point_execution_authority"]["authorized_predicates"])==AUTH

owned=sorted(x["family"] for x in mx["rows"] if x["status"]=="VERIFIED_OWNED_EQUAL_OR_BETTER")
assert len(owned)==5
assert mx["summary"]["verified_owned_equal_or_better_capabilities"]==owned

# Final activation receipt points to a real successful public verification.
assert finalvr["independent_runner"]["workflow_run_id"]==37158819540
req=urllib.request.Request("https://api.github.com/repos/moxnixmdj/verification-capsule-runner/actions/runs/37158819540",headers={"User-Agent":"Brain-V12-Rebase-Verifier","Accept":"application/vnd.github+json"})
with urllib.request.urlopen(req,timeout=30) as r: run=json.load(r)
assert run["status"]=="completed" and run["conclusion"]=="success"

print(json.dumps({
 "status":"INDEPENDENT_PUBLIC_PASS__V12_REBASE_COMMUTES_WITH_ROOT2_BRIDGE",
 "root2_bridge_preserved":True,
 "acceptance":"5/19",
 "atomic":"12/38",
 "verified_owned":"5/19",
 "scoped_authorized_predicates":sorted(AUTH),
 "global_fresh_reality_authority":False
},indent=2,sort_keys=True))
