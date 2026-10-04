from __future__ import annotations
import hashlib, importlib.util, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SUB=ROOT/"subject"/"terminal_causal_depth_20261004_sol"
EXPECTED={
 "POLICY.json":"fc8e43a26379d5d04c50f9296a0e6acebe8975c8",
 "RUNTIME.py":"85fc1b377a63f3f318d9e8f229c9476292ad05d9",
 "TEST.py":"fad9fc6fccd0d80dab872cce86750be0e4c78af3",
 "ARENA.json":"4f4fc3fc610f043e8328093ef11e7057c319229c",
}

def git_blob_sha(path: Path)->str:
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

for name,sha in EXPECTED.items():
    got=git_blob_sha(SUB/name)
    assert got==sha,(name,got,sha)

policy=json.loads((SUB/"POLICY.json").read_text())
arena=json.loads((SUB/"ARENA.json").read_text())

spec=importlib.util.spec_from_file_location("candidate_runtime",SUB/"RUNTIME.py")
mod=importlib.util.module_from_spec(spec); assert spec and spec.loader
spec.loader.exec_module(mod)

state=policy["exact_live_state"]
mod.validate_live_state(state)
assert len(mod.UNRESOLVED)==26
assert len(mod.RELATIVE_ELO)==3

# Relative-Elo nontransport must fail closed.
for p in mod.RELATIVE_ELO:
    assert mod.route_admissible(p,"FORMAL_ENTAILMENT") is False
    assert mod.route_admissible(p,"SCOPE_SAFE_STRONGER_PROOF") is False
    assert mod.route_admissible(p,"FORMAL_ENTAILMENT",explicit_relative_bridge=True) is True
    assert mod.route_admissible(p,"RELATIVE_SCORE_BRIDGE") is True
    assert mod.route_admissible(p,"OWNER_RESULT") is True
    assert mod.route_admissible(p,"MATCHED_EMPIRICAL_COMPARISON") is True

# Non-Elo targets retain zero-reality proof options.
assert mod.route_admissible("LIVEBENCH_IF_GE_65_7","FORMAL_ENTAILMENT") is True

routes=[
 {"predicate_id":"LIVEBENCH_IF_GE_65_7","route_kind":"FIXED_BAR_SCORE"},
 {"predicate_id":"FINANCE_ACCOUNTING_INDEX_GE_61","route_kind":"EXISTING_CONTENT_ADDRESSED_COMPARATOR_EVIDENCE"},
 {"predicate_id":"PROWORK_GDPVAL_GE_1846","route_kind":"FORMAL_ENTAILMENT"},
 {"predicate_id":"PROWORK_GDPVAL_GE_1846","route_kind":"RELATIVE_SCORE_BRIDGE"},
]
blocked=mod.compile_waves(state,routes,generic_isolation_proved=False,fresh_reality_authorized=False)
assert blocked["wave2"]["actions"]==[]
assert len(blocked["wave2"]["blocked_actions"])==1
zero_kinds={r["route_kind"] for r in blocked["wave0"]["typed_evidence_collapse"]}
assert zero_kinds=={"EXISTING_CONTENT_ADDRESSED_COMPARATOR_EVIDENCE","RELATIVE_SCORE_BRIDGE"}

half=mod.compile_waves(state,routes,generic_isolation_proved=True,fresh_reality_authorized=False)
assert half["wave2"]["actions"]==[]
half2=mod.compile_waves(state,routes,generic_isolation_proved=False,fresh_reality_authorized=True)
assert half2["wave2"]["actions"]==[]
open_=mod.compile_waves(state,routes,generic_isolation_proved=True,fresh_reality_authorized=True)
assert [x["route_kind"] for x in open_["wave2"]["actions"]]==["FIXED_BAR_SCORE"]

# Dominance deletes only mechanically known dominated actions.
actions=[
 {"id":"slow","phase":"zero","covers":["p1"],"critical_path_seconds":10,"information_class":1},
 {"id":"fast_superset","phase":"zero","covers":["p1","p2"],"critical_path_seconds":9,"information_class":1},
 {"id":"unknown","phase":"zero","covers":["p3"],"critical_path_seconds":None,"information_class":99},
]
ids={x["id"] for x in mod.dominance_prune(actions)}
assert ids=={"fast_superset","unknown"}

assert policy["compiled_from_main"]=="b72891ba413a09618516f67777a5011de2f2ef9a"
assert policy["root2_projection"]["current_effective_authority"]=="ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V11"
assert "INDEPENDENT_PROJECTION_VERIFICATION_REQUIRED" in policy["root2_projection"]["v12_status"]
assert policy["authority"]=={"scheduling_candidate":True,"execution":False,"promotion":False,"fresh_reality":False}
assert all(v==0 for v in policy["accounting"].values())

assert arena["authority"]=={"scheduling_candidate":True,"execution":False,"promotion":False,"fresh_reality":False}
assert all(v==0 for v in arena["accounting"].values())
claims={x["claim"] for x in arena["public_observations"]}
assert claims=={"AUTHENTICATED_ARENA_API_PORTAL_EXISTS","HUMAN_DIRECT_MODE_SUPPORTS_SPECIFIC_MODEL_SELECTION"}
assert "NO_CLAIM_EXACT_OPUS55_IS_AVAILABLE_TO_THE_ACCOUNT" in arena["hard_nonclaims"]
assert "NO_CLAIM_ARENA_API_USE_IS_ZERO_COST_FOR_THE_ACCOUNT" in arena["hard_nonclaims"]
assert "NO_CLAIM_LOGIN_GATED_MODEL_ROUTING_OR_FALLBACK_SEMANTICS_ARE_PUBLICLY_VERIFIED" in arena["hard_nonclaims"]

print(json.dumps({
 "status":"PASS",
 "exact_candidate_blobs":EXPECTED,
 "unresolved":len(mod.UNRESOLVED),
 "relative_elo_predicates":len(mod.RELATIVE_ELO),
 "fresh_reality_fail_closed":True,
 "dominance_unknown_preserved":True,
 "arena_public_claims_limited_to_verified_surface":True,
 "acceptance_credit_delta":0,
},sort_keys=True))
