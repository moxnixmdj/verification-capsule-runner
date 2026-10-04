import hashlib, json, pathlib, importlib.util

EXPECTED={
 "runtime":"0150744f8e2024421c94c1ec4944368cf72a59b9",
 "tests":"1afcbbf63be5d8d0d577a279572e9fa0bdc87c68",
 "governance":"3638e78e42a869f29f69c3697de78169cbca7699",
 "intent":"c9b73e65c7d84c9e22bad414c407d94fc4f8d0f1",
}
FILES={
 "runtime":"subject/root2_closure_controller_v2.py",
 "tests":"subject/test_root2_closure_controller_v2.py",
 "governance":"subject/ROOT2_CLOSURE_CONTROLLER_V2.json",
 "intent":"subject/ROOT2_CLOSURE_CONTROLLER_V2_20261004.json",
}
def blob_sha(path):
    b=pathlib.Path(path).read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
for k,p in FILES.items():
    got=blob_sha(p)
    assert got==EXPECTED[k], (k,got,EXPECTED[k])

spec=importlib.util.spec_from_file_location("r2","subject/root2_closure_controller_v2.py")
r=importlib.util.module_from_spec(spec); spec.loader.exec_module(r)

assert r.validate_comparator([{
 "predicate_id":"p","surface":"s","target":"1","model":"m","population":"pop",
 "harness":"h","scorer":"sc","provenance":"src","name_only_equivalence":True
}])["status"]=="FAIL_CLOSED"

d=r.derive_nodes(open_predicates=["FIN"],proved=["a","b"],derivations=[{
 "target":"FIN","premises":["a","b"],"monotone_or_implication_verified":True
}])
assert d["closed"]==["FIN"]

f=r.compile_frontier([
 {"id":"truth","class":"TRUTH_REPAIR","closes":["p"],"incremental_spend_usd":0},
 {"id":"score","class":"BRAIN_SCORE","closes":["q"],"incremental_spend_usd":0},
 {"id":"dead","class":"FORMAL_DOMINANCE","closes":["r"],"incremental_spend_usd":0,"saturated":True}
],open_predicates=["p","q","r"],zero_reality_fixed_point=False)
assert f["zero_reality_parallel"]==["truth"]
assert f["fresh_reality_authorized"]==[]
assert set(f["waiting"])=={"score"}
assert f["deleted"]==["dead"]

f2=r.compile_frontier([
 {"id":"score","class":"BRAIN_SCORE","closes":["q"],"incremental_spend_usd":0}
],open_predicates=["q"],zero_reality_fixed_point=True)
assert f2["fresh_reality_authorized"]==["score"]

g=json.loads(pathlib.Path(FILES["governance"]).read_text())
i=json.loads(pathlib.Path(FILES["intent"]).read_text())
assert g["exact_state"]["root2_only"]==16
assert g["exact_state"]["root2_and_root3"]==3
assert g["exact_state"]["root2_touching"]==19
assert g["reconciliation"]["acceptance_delta"]==0
assert g["accounting"]["incremental_spend_usd"]==0
assert g["accounting"]["acceptance_credit_delta"]==0
assert g["independent_verification_required"] is True
assert i["execution_authority"] is False
assert i["promotion_authority"] is False
assert i["fresh_reality_authority"] is False
print("ROOT2_CLOSURE_CONTROLLER_V2_RECONCILED_PUBLIC_RUNNER_PASS")

# synchronize trigger: exact subject bytes unchanged
