import hashlib,importlib.util,sys
from pathlib import Path
S=Path(__file__).parent/"subject"/"tcb1_scheduler_20261004_sol"
def h(p):
 d=p.read_bytes();return hashlib.sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()
R=S/"terminal_minimum_causal_depth_policy_v1.py";B=S/"terminal_typed_minimum_certificate_basis_v1.py"
assert h(R)=="0b613ae0617e51a9f12a771b4c83dd99e4d23da4"
assert h(B)=="b42c81e04109e1ff081517672b397390bb3749e0"
sys.path.insert(0,str(S))
q=importlib.util.spec_from_file_location("m",R);m=importlib.util.module_from_spec(q);q.loader.exec_module(m)
st={"accepted_families":5,"open_families":14,"proved_atomic":12,"unresolved_atomic":26,"total_families":19,"total_atomic":38,"root1_positive_gaps":0,"root2_only":16,"root3_only":7,"root2_and_root3":3,"terminal":False}
rs=[{"predicate_id":"FINANCE_UNCOVERED_SCOPE_AUDIT","route_kind":"SCOPE_CERTIFICATE"},{"predicate_id":"AGENCY_MATCHED_SUCCESS_NONINFERIOR","route_kind":"EXISTING_CONTENT_ADDRESSED_COMPARATOR_EVIDENCE"},{"predicate_id":"PROWORK_GDPVAL_GE_1846","route_kind":"FORMAL_ENTAILMENT"},{"predicate_id":"PROWORK_GDPVAL_GE_1846","route_kind":"OWNER_RESULT"},{"predicate_id":"LIVEBENCH_IF_GE_65_7","route_kind":"FIXED_BAR_SCORE"}]
a=m.filter_routes(rs);d={(x["predicate_id"],x["route_kind"]):x for x in a}
assert len(a)==4
assert d[("FINANCE_UNCOVERED_SCOPE_AUDIT","SCOPE_CERTIFICATE")]["required_proof_dimensions"]==["SCOPE_COMPLETENESS"]
assert d[("AGENCY_MATCHED_SUCCESS_NONINFERIOR","EXISTING_CONTENT_ADDRESSED_COMPARATOR_EVIDENCE")]["required_proof_dimensions"]==["COMPARATOR_STRENGTH","SCOPE_COMPLETENESS"]
assert d[("PROWORK_GDPVAL_GE_1846","OWNER_RESULT")]["required_proof_dimensions"]==["COMPARATOR_STRENGTH"]
o=m.compile_waves(st,rs,generic_isolation_proved=True,fresh_reality_authorized=False);b=o["wave0"]["typed_minimum_certificate_basis"]
assert (b["typed_obligation_count"],b["comparator_strength_obligations"],b["scope_completeness_obligations"])==(29,19,10)
assert o["wave2"]["fresh_reality_authorized"] is False and o["wave2"]["actions"]==[]
print("PASS 26 29 19 10")
