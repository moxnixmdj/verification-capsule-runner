from __future__ import annotations
import hashlib,json,pathlib,urllib.request
ROOT=pathlib.Path(__file__).resolve().parent
AUTH={"LIVEBENCH_IF_GE_65_7","TB_SCIENCE_GE_58_7"}

def load(rel):
    return json.loads((ROOT/rel).read_text(encoding="utf-8"))

m=load("EXPECTED_BRAIN_BLOBS.json")
for rel,expected in m["exact_brain_blobs"].items():
    b=(ROOT/rel).read_bytes()
    got=hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
    assert got==expected,(rel,got,expected)

cand=load("canonical/governance/LOCAL_ZERO_REALITY_FIXED_POINT_CANDIDATE_V1.json")
vr=load("canonical/verification/LOCAL_ZERO_REALITY_FIXED_POINT_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json")
v12=load("canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V12.json")
aa=load("canonical/governance/LOCAL_ZERO_REALITY_FIXED_POINT_ACTIVE_AUTHORITY_V1.json")
ptr=load("canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_ACTIVE_POINTER_V1.json")
term=load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")
mx=load("canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json")

# Prior theorem receipt must point to a genuinely successful public job.
assert vr["independent_runner"]["workflow_run_id"]==37158244145
assert vr["independent_runner"]["workflow_job_id"]==111306055369
req=urllib.request.Request(
  "https://api.github.com/repos/moxnixmdj/verification-capsule-runner/actions/runs/37158244145",
  headers={"Accept":"application/vnd.github+json","User-Agent":"Brain-V12-Independent-Verifier"})
with urllib.request.urlopen(req,timeout=30) as r:
    run=json.load(r)
assert run["status"]=="completed" and run["conclusion"]=="success"

# Exact truth is unchanged by scheduling.
s=v12["exact_state"]
assert (s["accepted_families"],s["open_families"],s["proved_atomic"],s["unresolved_atomic"])==(5,14,12,26)
assert s["terminal"] is False
assert v12["acceptance_credit_delta"]==0 and v12["family_credit_delta"]==0
assert v12["capability_credit_delta"]==0 and v12["ownership_credit_delta"]==0

# Authority is exactly local, never global.
assert v12["global_fresh_reality_authority"] is False
assert v12["scoped_fresh_reality_authority"] is True
assert set(v12["scoped_authorized_predicates"])==AUTH
assert v12["fresh_reality_authority"] is False
assert v12["execution_authority"] is False
assert aa["global_fresh_reality_authority"] is False
assert aa["scoped_fresh_reality_authority"] is True
assert set(aa["scoped_authorized_predicates"])==AUTH
assert aa["all_other_unresolved_predicates_authorized"] is False
assert set(term["local_fixed_point_execution_authority"]["authorized_predicates"])==AUTH
assert term["local_fixed_point_execution_authority"]["global_fresh_reality_authority"] is False
assert term["local_fixed_point_execution_authority"]["unauthorized_unresolved_predicate_count"]==24

# Only the two intended work rows are marked scoped-authorized.
rows={x["surface"]:x["work"] for x in v12["active_zero_reality_work"]}
assert "SCOPED_FRESH_REALITY_AUTHORIZED" in rows["LiveBench IF"]
assert "SCOPED_FRESH_REALITY_AUTHORIZED" in rows["Terminal-Bench-Science 0.1"]
for name,work in rows.items():
    if name not in {"LiveBench IF","Terminal-Bench-Science 0.1"}:
        assert "SCOPED_FRESH_REALITY_AUTHORIZED" not in work,(name,work)

# Pointer is exact.
assert ptr["active_cut"]["path"]=="canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V12.json"
assert ptr["active_cut"]["git_blob_sha"]==m["exact_brain_blobs"]["canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V12.json"]
assert ptr["scoped_fresh_reality_authority"] is True
assert ptr["global_fresh_reality_authority"] is False
assert set(ptr["scoped_authorized_predicates"])==AUTH

# Ownership summary is a pure projection of current row truth.
owned=sorted(x["family"] for x in mx["rows"] if x["status"]=="VERIFIED_OWNED_EQUAL_OR_BETTER")
components=sorted(x["family"] for x in mx["rows"] if x["status"]=="OWNED_COMPONENT_NOT_FULL_FAMILY")
assert len(owned)==5
assert mx["summary"]["verified_owned_equal_or_better_capabilities"]==owned
assert mx["summary"]["owned_components_not_full_family"]==components
assert mx["postwave_acceptance_summary"]["verified_owned_family_count"]==5
assert mx["summary_reconciliation_20261004"]["verified_owned_equal_or_better_count"]==5
assert term["truth"]["opus55_verified_owned"].startswith("5/19_")

print(json.dumps({
 "status":"INDEPENDENT_PUBLIC_PASS__V12_EXACT_SCOPED_AUTHORITY_AND_OWNERSHIP_SUMMARY_RECONCILIATION",
 "acceptance":"5/19",
 "atomic":"12/38",
 "verified_owned":"5/19",
 "scoped_authorized_predicates":sorted(AUTH),
 "global_fresh_reality_authority":False,
 "acceptance_credit_delta":0
},indent=2,sort_keys=True))
