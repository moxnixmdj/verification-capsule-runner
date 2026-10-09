from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent/"source"
FILES={
 "r2":ROOT/"canonical__governance__CURRENT_R2_DECISION_INTELLIGENCE.json",
 "act":ROOT/"canonical__governance__R2_DIRECT_END_TO_END_ADEQUACY_ROUTES_ACTIVATION_20261009_V28.json",
 "cut":ROOT/"canonical__governance__ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V55.json",
 "terminal":ROOT/"canonical__governance__CURRENT_TERMINAL_AUTHORITY.json",
 "fixed":ROOT/"canonical__runtime__general_adequate_decision_fixed_point_v2.py",
 "v19":ROOT/"canonical__runtime__r2_direct_end_to_end_adequacy_v19.py",
}
EXPECTED={
 "r2":"c40e8e27fe27ad9974e790f7a128bfe76fb7d65a",
 "act":"4ad15d84c046f673c68cbc81d35f842c1adf918c",
 "cut":"a7c04b0ceb3b28deacfa078c11e70e7841445d78",
 "terminal":"21c43c3b72ce7695e2387cf974ca3261909154a2",
 "fixed":"7c6b28754fa8851f220395df1615dd6afe193b3a",
 "v19":"39e7a6b7298b17d55e7bda551d6125c1f1c4000e",
}
SUCCESSORS={
 "DIRECT_ADEQUACY::CROSS_DOCUMENT_NATURAL_EFFECT_LATTICE_V3",
 "DIRECT_ADEQUACY::CROSS_DOCUMENT_SEMANTIC_EDGE_LATTICE_V4",
 "DIRECT_ADEQUACY::CROSS_DOCUMENT_SEMANTIC_REGISTRY_LATTICE_V5",
 "DIRECT_ADEQUACY::SOURCE_BOUND_REGCAP_IDENTITY_NYFED_CCOB_V1",
}
def blob(p):
 raw=p.read_bytes()
 return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
actual={k:blob(v) for k,v in FILES.items()}
assert actual==EXPECTED,(actual,EXPECTED)

r2=json.loads(FILES["r2"].read_text())
act=json.loads(FILES["act"].read_text())
cut=json.loads(FILES["cut"].read_text())
term=json.loads(FILES["terminal"].read_text())
fixed=FILES["fixed"].read_text()

assert "__V57__" in r2["status"],r2["status"]
assert "r2_direct_end_to_end_adequacy_v19 as direct_adequacy" in fixed
d=r2["direct_adequacy"]
assert d["direct_runtime_path"]=="canonical/runtime/r2_direct_end_to_end_adequacy_v19.py"
assert d["direct_runtime_git_blob_sha"]==EXPECTED["v19"]
assert d["fixed_point_controller_git_blob_sha"]==EXPECTED["fixed"]
assert r2["controller"]["fixed_point_git_blob_sha"]==EXPECTED["fixed"]
assert d["activation_path"]=="canonical/governance/R2_DIRECT_END_TO_END_ADEQUACY_ROUTES_ACTIVATION_20261009_V28.json"
assert d["activation_git_blob_sha"]==EXPECTED["act"]
assert d["current_route_count"]==39 and d["bounded_family_count"]==36

ids=[row["route_id"] for row in act["current_routes"]]
assert len(ids)==39 and len(set(ids))==39
assert SUCCESSORS.issubset(set(ids)), sorted(SUCCESSORS-set(ids))
assert act["runtime"]=="canonical/runtime/r2_direct_end_to_end_adequacy_v19.py"

assert r2["scheduler_cut"]["path"]=="canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V55.json"
assert r2["scheduler_cut"]["git_blob_sha"]==EXPECTED["cut"]
for obj in (r2["scheduler_result"],cut["scheduler_result"]):
 assert obj["direct_route_count"]==39 and obj["bounded_family_count"]==36,obj

assert "CURRENT_R2_V57" in term["status"],term["status"]
assert term["live_truth"]["r2_direct_adequacy_route_count"]==39
assert term["live_truth"]["r2_direct_adequacy_bounded_family_count"]==36
assert term["live_truth"]["current_r2_scheduler_cut"]=="ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V55"
assert term["r2_scheduler_precedence"]["current_scheduler_git_blob_sha"]==EXPECTED["cut"]
src=term["authoritative_sources"]["current_r2_decision_intelligence"]
assert src["status"]==r2["status"]
assert src["scheduler_cut"]["git_blob_sha"]==EXPECTED["cut"]

print("PASS__PR3701_V57_V19_AUTHORITY_RECONCILIATION")
print(json.dumps({
 "exact_blob_bindings":"6_OF_6_PASS",
 "live_controller_import":"V19",
 "activation_route_count":39,
 "bounded_family_count":36,
 "v16_to_v19_successor_ids":"4_OF_4_PRESENT",
 "scheduler_projection":"V55_39_36_PASS",
 "terminal_projection":"V57_39_36_PASS",
 "full_private_repo_regression_claimed":False,
 "terminal_credit_delta":0
},sort_keys=True))
