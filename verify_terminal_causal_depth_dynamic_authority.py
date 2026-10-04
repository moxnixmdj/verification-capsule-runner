from __future__ import annotations
import hashlib, importlib.util, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SUB=ROOT/"subject"/"terminal_causal_depth_dynamic_authority_20261004_sol"
EXPECTED={
 "POLICY.json":"ed50678f56dc873eda5aada1c5509286d216ab94",
 "RUNTIME.py":"85fc1b377a63f3f318d9e8f229c9476292ad05d9",
 "ACTIVATION.json":"1c4400af63533e236847189b17b11e8dd7f80107",
 "ARENA.json":"4f4fc3fc610f043e8328093ef11e7057c319229c",
}
def git_blob_sha(path: Path)->str:
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
for n,s in EXPECTED.items():
    got=git_blob_sha(SUB/n)
    assert got==s,(n,got,s)

policy=json.loads((SUB/"POLICY.json").read_text())
act=json.loads((SUB/"ACTIVATION.json").read_text())
arena=json.loads((SUB/"ARENA.json").read_text())

spec=importlib.util.spec_from_file_location("candidate_runtime",SUB/"RUNTIME.py")
mod=importlib.util.module_from_spec(spec); assert spec and spec.loader
spec.loader.exec_module(mod)

state=policy["exact_live_state"]
mod.validate_live_state(state)
assert state["accepted_families"]==5 and state["proved_atomic"]==12 and state["unresolved_atomic"]==26
assert state["terminal"] is False
assert len(mod.UNRESOLVED)==26

rp=policy["root2_projection"]
assert rp["effective_authority_source"].endswith("active_closure_controller")
assert rp["latest_observed_frontier_path"].endswith("ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V12.json")
assert "DO_NOT_HARDCODE_FRONTIER_VERSION" in rp["compatibility_rule"]
assert "MUST_BE_READ_FROM_CANONICAL_ROOT_STATE" in rp["fresh_reality_rule"]
assert "ROOT2_FRONTIER_VERSION_IS_DYNAMIC_INPUT_NOT_A_POLICY_CONSTANT" in policy["cut_rules"]

for p in mod.RELATIVE_ELO:
    assert mod.route_admissible(p,"FORMAL_ENTAILMENT") is False
    assert mod.route_admissible(p,"SCOPE_SAFE_STRONGER_PROOF") is False
    assert mod.route_admissible(p,"RELATIVE_SCORE_BRIDGE") is True
    assert mod.route_admissible(p,"OWNER_RESULT") is True

routes=[
 {"predicate_id":"LIVEBENCH_IF_GE_65_7","route_kind":"FIXED_BAR_SCORE"},
 {"predicate_id":"PROWORK_GDPVAL_GE_1846","route_kind":"FORMAL_ENTAILMENT"},
 {"predicate_id":"PROWORK_GDPVAL_GE_1846","route_kind":"RELATIVE_SCORE_BRIDGE"},
]
blocked=mod.compile_waves(state,routes,generic_isolation_proved=True,fresh_reality_authorized=False)
assert blocked["wave2"]["actions"]==[]
assert [x["route_kind"] for x in blocked["wave0"]["typed_evidence_collapse"]]==["RELATIVE_SCORE_BRIDGE"]
opened=mod.compile_waves(state,routes,generic_isolation_proved=True,fresh_reality_authorized=True)
assert [x["route_kind"] for x in opened["wave2"]["actions"]]==["FIXED_BAR_SCORE"]

assert act["status"]=="ACTIVATION_CONTRACT__ACTIVE_ONLY_WITH_CURRENT_INDEPENDENT_POLICY_RECEIPT_AND_ROOT_PROJECTION_PASS__ZERO_CREDIT"
assert "verification_contract" in act and "verification" not in act
assert act["authority"]=={"scheduling":True,"meta_scheduling":True,"execution":False,"promotion":False,"fresh_reality":False}
assert all(v==0 for v in act["accounting"].values())
assert "ROOT2_FRONTIER_VERSION_READ_DURING_SCHEDULING_FROM_CURRENT_CANONICAL_ROOT_STATE" in act["effects"]

claims={x["claim"] for x in arena["public_observations"]}
assert claims=={"AUTHENTICATED_ARENA_API_PORTAL_EXISTS","HUMAN_DIRECT_MODE_SUPPORTS_SPECIFIC_MODEL_SELECTION"}
assert "NO_CLAIM_LOGIN_GATED_MODEL_ROUTING_OR_FALLBACK_SEMANTICS_ARE_PUBLICLY_VERIFIED" in arena["hard_nonclaims"]
assert all(v==0 for v in arena["accounting"].values())

print(json.dumps({
 "status":"PASS",
 "exact_candidate_blobs":EXPECTED,
 "root2_authority_dynamic":True,
 "latest_observed_root2":"V12",
 "relative_elo_fail_closed":True,
 "fresh_reality_fail_closed":True,
 "activation_contract_fail_closed":True,
 "arena_account_residual_preserved":True,
 "acceptance_credit_delta":0,
},sort_keys=True))
