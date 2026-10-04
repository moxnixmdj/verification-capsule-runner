import hashlib,json
from pathlib import Path
S=Path(__file__).parent/"subject"/"structural_parallel_root_20261004_sol"
E={"ROOT.json":"e353d54f4608d25b7f0ea06fba5d8fbf2ddfbb59","ACTIVATION.json":"89b3d8cbbc3b9e0822870ee803fb99c37a82d209","GENERIC_VERIFICATION.json":"e9e07a85e7a932ba7ce024c77897ab9016c72ce4","TYPED_VERIFICATION.json":"069ac4d25f82b62e0ae03e7eb9ae30a3c1a96628"}
def g(p):
 d=p.read_bytes();return hashlib.sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()
for n,h in E.items(): assert g(S/n)==h
r=json.loads((S/"ROOT.json").read_text());a=json.loads((S/"ACTIVATION.json").read_text());gv=json.loads((S/"GENERIC_VERIFICATION.json").read_text());tv=json.loads((S/"TYPED_VERIFICATION.json").read_text())
assert r["current_acceptance"]=={"accepted_families":5,"open_families":14,"proved_atomic":12,"unresolved_atomic":26,"total_families":19,"total_atomic":38,"terminal":False}
p=r["current_residual_root_partition"];assert (p["unresolved_total"],p["root1_positive_gap_count"],p["root2_only_count"],p["root3_only_count"],p["root2_and_root3_count"])==(26,0,16,7,3)
s=r["scheduler_policy"];t=s["typed_minimum_certificate_basis"];i=s["generic_precommit_isolation"]
assert (t["typed_obligations"],t["comparator_strength_obligations"],t["scope_completeness_obligations"])==(29,19,10)
assert t["runtime_git_blob_sha"]=="b42c81e04109e1ff081517672b397390bb3749e0" and t["verification_git_blob_sha"]==E["TYPED_VERIFICATION.json"]
assert i["activation_git_blob_sha"]==E["ACTIVATION.json"] and i["verification_git_blob_sha"]==E["GENERIC_VERIFICATION.json"]
assert i["generic_conditional_adaptation_independence_proved"] is True and i["current_benchmark_instantiation_receipts_proved"]==0
assert i["benchmark_thin_adapter_still_required"] is True and i["explicit_fresh_reality_authority_still_required"] is True
for x in (t,i): assert x["execution_authority"] is False and x["promotion_authority"] is False and x["fresh_reality_authority"] is False and x["acceptance_credit_delta"]==0
assert gv["independent_runner"]["conclusion"]=="success" and gv["verified"]["generic_conditional_adaptation_independence_theorem"] is True
assert tv["independent_runner"]["conclusion"]=="success" and tv["verified"]["typed_obligations"]==29
assert r["roots"]["root_2_measurement_or_comparator"]["active_closure_controller"]["fresh_reality_authority"] is False
assert r["root3_current_execution_state"]["fresh_reality_authority"] is False
print(json.dumps({"status":"PASS","root":E["ROOT.json"],"typed":29,"generic_isolation":True,"benchmark_instantiations":0,"terminal":False,"fresh_reality":False},sort_keys=True))
