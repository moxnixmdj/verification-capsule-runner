import hashlib, json, pathlib, importlib.util

EXPECTED = {
  "runtime": "0150744f8e2024421c94c1ec4944368cf72a59b9",
  "tests": "c9b581e265835a5d1840701b39f87bed3dd30ad8",
  "governance": "328d58eddbaf0198128973e06af7ca68c3527e27",
  "intent": "4244e8a7cf3c7c56875e64d7fff5521c2723d880",
  "frontier": "76805d5f7a7fdcd753296564370ef0b2408033e8"
}

FILES = {
 "runtime":"subject/root2_closure_controller_v2.py",
 "tests":"subject/test_root2_closure_controller_v2.py",
 "governance":"subject/ROOT2_CLOSURE_CONTROLLER_V2.json",
 "intent":"subject/ACTION_INTENT_ROOT2_SYNTHESIS_COVERAGE_V2_RECONCILIATION_20261004.json",
 "frontier":"subject/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V1.json",
}

def blob_sha(path):
    b=pathlib.Path(path).read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

for k,p in FILES.items():
    got=blob_sha(p)
    assert got==EXPECTED[k], (k,got,EXPECTED[k])

spec=importlib.util.spec_from_file_location("r2",FILES["runtime"])
r=importlib.util.module_from_spec(spec); spec.loader.exec_module(r)

# Preserve fail-closed controller semantics.
assert r.validate_comparator([{
 "predicate_id":"p","surface":"s","target":"1","model":"m","population":"pop",
 "harness":"h","scorer":"sc","provenance":"src","name_only_equivalence":True
}])["status"]=="FAIL_CLOSED"
f=r.compile_frontier([
 {"id":"truth","class":"TRUTH_REPAIR","closes":["p"],"incremental_spend_usd":0},
 {"id":"score","class":"BRAIN_SCORE","closes":["q"],"incremental_spend_usd":0},
 {"id":"dead","class":"FORMAL_DOMINANCE","closes":["r"],"incremental_spend_usd":0,"saturated":True}
],open_predicates=["p","q","r"],zero_reality_fixed_point=False)
assert f["zero_reality_parallel"]==["truth"]
assert f["fresh_reality_authorized"]==[]
assert f["waiting"]==["score"]
assert f["deleted"]==["dead"]

g=json.loads(pathlib.Path(FILES["governance"]).read_text())
i=json.loads(pathlib.Path(FILES["intent"]).read_text())
fr=json.loads(pathlib.Path(FILES["frontier"]).read_text())

# Exact terminal counts must not move from a sub-predicate reduction.
assert g["exact_state"]=={
 "root2_only":16,"root2_and_root3":3,"root2_touching":19,
 "unique_fixed_bar_surfaces":14,"accepted_families":5,"proved_atomic":12,"unresolved_atomic":26
}
s=g["algebraic_compression"]["synthesis"]
assert s["root2_residuals"]==["metric:matched_quality","matched_quality_noninferiority"]
assert s["required_claim_coverage"]["state"]=="PROVED_BY_INDEPENDENT_CEILING_PLUS_SUPERSET_SCOPE"
assert s["required_claim_coverage"]["verifier_pull_request"]==1526
assert s["required_claim_coverage"]["workflow_run_id"]==37164910933
assert s["required_claim_coverage"]["workflow_job_id"]==111325748211
assert g["accounting"]["incremental_spend_usd"]==0
assert g["accounting"]["acceptance_credit_delta"]==0

# The current frontier must bind the exact new controller blob and preserve
# the same two residuals without granting fresh-reality authority.
assert fr["source_bindings"]["controller"]["git_blob_sha"]==EXPECTED["governance"]
cv=fr["source_bindings"]["synthesis_coverage_v2"]
assert cv["git_blob_sha"]=="f2ef80facb39264b1e12b81e451eb4499a3b987f"
assert cv["workflow_run_id"]==37164910933 and cv["workflow_job_id"]==111325748211
syn=next(x for x in fr["zero_reality_parallel"] if x["id"]=="SYNTHESIS_METRIC_NONINFERIORITY_PROOF")
assert syn["state"]=="ROOT2_ONLY__REQUIRED_CLAIM_COVERAGE_DISCHARGED__OPEN_RESIDUALS_MATCHED_QUALITY_ATOM_AND_MATCHED_QUALITY_NONINFERIORITY"
assert "NO_FRESH_REALITY_AUTHORITY" in fr["hard_rules"]
assert fr["accounting"]["acceptance_credit_delta"]==0

assert i["execution_authority"] is False
assert i["promotion_authority"] is False
assert i["fresh_reality_authority"] is False
assert i["acceptance_credit_delta"]==0
print("ROOT2_SYNTHESIS_COVERAGE_V2_RECONCILIATION_PUBLIC_RUNNER_PASS")
