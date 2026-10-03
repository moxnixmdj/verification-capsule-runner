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

v12=load("canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V12.json")
vr=load("canonical/verification/CURRENT_ZERO_REALITY_MINIMUM_CUT_V12_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json")
act=load("canonical/governance/LOCAL_ZERO_REALITY_FIXED_POINT_ACTIVATION_V1.json")
ptr=load("canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_ACTIVE_POINTER_V1.json")
term=load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")
mx=load("canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json")

# Prior V12 exact transaction verification is genuine.
assert vr["independent_runner"]["workflow_run_id"]==37158592587
req=urllib.request.Request("https://api.github.com/repos/moxnixmdj/verification-capsule-runner/actions/runs/37158592587",headers={"User-Agent":"Brain-V12-Final-Activation-Verifier","Accept":"application/vnd.github+json"})
with urllib.request.urlopen(req,timeout=30) as r: run=json.load(r)
assert run["status"]=="completed" and run["conclusion"]=="success"

# Immutable verified V12 remains unchanged.
assert m["exact_brain_blobs"]["canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V12.json"]=="755bf5efce7e7e5f6b1c0462eb824755ab8c3138"
assert v12["exact_state"]["accepted_families"]==5
assert v12["exact_state"]["proved_atomic"]==12
assert v12["exact_state"]["unresolved_atomic"]==26
assert v12["exact_state"]["terminal"] is False
assert v12["global_fresh_reality_authority"] is False
assert set(v12["scoped_authorized_predicates"])==AUTH

# Promotion edge is exact and narrow.
assert act["status"].startswith("ACTIVE_MAIN__")
assert act["active_cut"]["git_blob_sha"]=="755bf5efce7e7e5f6b1c0462eb824755ab8c3138"
assert act["exact_transaction_verification"]["git_blob_sha"]==m["exact_brain_blobs"]["canonical/verification/CURRENT_ZERO_REALITY_MINIMUM_CUT_V12_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json"]
assert act["global_fresh_reality_authority"] is False
assert act["scoped_fresh_reality_authority"] is True
assert set(act["scoped_authorized_predicates"])==AUTH
assert act["all_other_unresolved_predicates_authorized"] is False

assert ptr["status"].startswith("ACTIVE__V12_")
assert ptr["active_cut"]["git_blob_sha"]=="755bf5efce7e7e5f6b1c0462eb824755ab8c3138"
assert ptr["activation"]["git_blob_sha"]==m["exact_brain_blobs"]["canonical/governance/LOCAL_ZERO_REALITY_FIXED_POINT_ACTIVATION_V1.json"]
assert ptr["global_fresh_reality_authority"] is False
assert ptr["scoped_fresh_reality_authority"] is True
assert set(ptr["scoped_authorized_predicates"])==AUTH

assert term["truth"]["opus55_acceptance"]=="5/19_PASS__14/19_OPEN"
assert term["truth"]["achieved"] is False
assert set(term["local_fixed_point_execution_authority"]["authorized_predicates"])==AUTH
assert term["authorities"]["local_zero_reality_fixed_point"]["git_blob_sha"]==m["exact_brain_blobs"]["canonical/governance/LOCAL_ZERO_REALITY_FIXED_POINT_ACTIVATION_V1.json"]

owned=sorted(x["family"] for x in mx["rows"] if x["status"]=="VERIFIED_OWNED_EQUAL_OR_BETTER")
assert len(owned)==5
assert mx["summary"]["verified_owned_equal_or_better_capabilities"]==owned

print(json.dumps({"status":"INDEPENDENT_PUBLIC_PASS__FINAL_V12_ACTIVATION_EDGE","scoped_authorized_predicates":sorted(AUTH),"global_fresh_reality_authority":False,"acceptance":"5/19","atomic":"12/38","verified_owned":"5/19"},indent=2,sort_keys=True))
