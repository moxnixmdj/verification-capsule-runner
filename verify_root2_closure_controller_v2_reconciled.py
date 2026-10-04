import hashlib,json,pathlib,importlib.util
EXPECTED={"runtime":"0150744f8e2024421c94c1ec4944368cf72a59b9","tests":"1afcbbf63be5d8d0d577a279572e9fa0bdc87c68","governance":"3638e78e42a869f29f69c3697de78169cbca7699","intent":"c9b73e65c7d84c9e22bad414c407d94fc4f8d0f1"}
FILES={"runtime":"subject/root2_closure_controller_v2.py","tests":"subject/test_root2_closure_controller_v2.py","governance":"subject/ROOT2_CLOSURE_CONTROLLER_V2.json","intent":"subject/ROOT2_CLOSURE_CONTROLLER_V2_20261004.json"}
def blob_sha(p):
 b=pathlib.Path(p).read_bytes(); return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
for k,p in FILES.items(): assert blob_sha(p)==EXPECTED[k],(k,blob_sha(p),EXPECTED[k])
spec=importlib.util.spec_from_file_location("r2",FILES["runtime"]); r=importlib.util.module_from_spec(spec); spec.loader.exec_module(r)
assert r.validate_comparator([{"predicate_id":"p","surface":"s","target":"1","model":"m","population":"p","harness":"h","scorer":"s","provenance":"x","name_only_equivalence":True}])["status"]=="FAIL_CLOSED"
assert r.derive_nodes(open_predicates=["FIN"],proved=["a","b"],derivations=[{"target":"FIN","premises":["a","b"],"monotone_or_implication_verified":True}])["closed"]==["FIN"]
f=r.compile_frontier([{"id":"truth","class":"TRUTH_REPAIR","closes":["p"],"incremental_spend_usd":0},{"id":"score","class":"BRAIN_SCORE","closes":["q"],"incremental_spend_usd":0},{"id":"dead","class":"FORMAL_DOMINANCE","closes":["r"],"incremental_spend_usd":0,"saturated":True}],open_predicates=["p","q","r"])
assert f["zero_reality_parallel"]==["truth"] and f["fresh_reality_authorized"]==[] and f["waiting"]==["score"] and f["deleted"]==["dead"]
g=json.loads(pathlib.Path(FILES["governance"]).read_text())
assert (g["exact_state"]["root2_only"],g["exact_state"]["root2_and_root3"],g["exact_state"]["root2_touching"])==(16,3,19)
assert g["reconciliation"]["acceptance_delta"]==0
assert g["accounting"]["acceptance_credit_delta"]==0
assert "SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR" not in g["algebraic_compression"]["matched_superportfolio"]["predicates"]
assert g["algebraic_compression"]["synthesis"]["current_class"]=="ROOT2_ONLY"
print("ROOT2_CLOSURE_CONTROLLER_V2_RECONCILED_PUBLIC_RUNNER_PASS")
