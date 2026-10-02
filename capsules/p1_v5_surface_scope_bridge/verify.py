from __future__ import annotations
import copy, hashlib, importlib.util, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def blob(path: Path)->str:
    data=path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()

expected=json.loads((ROOT/"EXPECTED_BRAIN_BLOBS.json").read_text())
mirrors={
 "canonical/runtime/p1_v5_direct_surface_scope_relation_v1.py":ROOT/"bridge.py",
 "canonical/tests/test_p1_v5_direct_surface_scope_relation_v1.py":ROOT/"brain_test.py",
 "canonical/governance/P1_V5_DIRECT_SURFACE_SCOPE_RELATION_V1.json":ROOT/"bridge_governance.json",
 "canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json":ROOT/"binding.json",
 "canonical/governance/TERMINAL_PORTFOLIO_BINDING_MANIFESTS_V1.json":ROOT/"portfolios.json",
 "canonical/governance/FOUR_UNCOVERED_BEHAVIORAL_PROOF_CONTRACTS_V1.json":ROOT/"four_contracts.json",
 "canonical/governance/CONTRACT_NATIVE_ABSOLUTE_PROOF_SUITES_V1.json":ROOT/"absolute_suites.json",
 "canonical/governance/CONTRACT_NATIVE_PRIVATE_SURFACE_PROOF_ROUTES_V1.json":ROOT/"native_routes.json",
 "canonical/governance/P1_TYPED_INTERVENTION_ENVELOPE_V5.json":ROOT/"v5.json",
}
actual={k:blob(v) for k,v in mirrors.items()}
assert actual==expected["exact_brain_blobs"], (actual,expected["exact_brain_blobs"])

spec=importlib.util.spec_from_file_location("bridge",ROOT/"bridge.py")
bridge=importlib.util.module_from_spec(spec); assert spec and spec.loader
spec.loader.exec_module(bridge)

def load(name):
    return json.loads((ROOT/name).read_text())

b=load("binding.json"); p=load("portfolios.json"); fc=load("four_contracts.json")
a=load("absolute_suites.json"); nr=load("native_routes.json"); v=load("v5.json")
g=load("bridge_governance.json")

def ev(**overrides):
    args={"binding":b,"portfolios":p,"four_contracts":fc,"absolute_suites":a,"native_routes":nr,"v5":v}
    args.update(overrides)
    return bridge.evaluate(**args)

out=ev()
assert out["status"].startswith("PASS__"), out
assert out["all_declared_p1_surface_relations_exact_or_superset"] is True
assert out["v5_is_superset_carrier_for_frozen_p1_residual_role"] is True
assert out["full_surface_superset_claim"] is False
assert out["terminal_surface_proof_complete"] is False
assert out["can_clear_p1_scope_quarantine"] is False
assert out["execution_authority"] is False and out["promotion_authority"] is False
assert out["new_reality_units_consumed"]==0
assert len(out["surface_relations"])==3
assert {x["relation"] for x in out["surface_relations"]}=={"SUPERSET"}
assert len({x["claim_id"] for x in out["surface_relations"]})==3
assert all(x["relation_scope"]=="UNRESOLVED_SEMANTICS_WITHIN_EXACT_FROZEN_P1_CONTRACT_ROLE_ONLY" for x in out["surface_relations"])
assert all(x["full_surface_superset_claim"] is False for x in out["surface_relations"])

govrels={x["claim_id"]:(x["direct_surface"],x["relation"],x["scope"]) for x in g["claim_bound_relations"]}
outrels={x["claim_id"]:(x["binding"],x["relation"],x["relation_scope"]) for x in out["surface_relations"]}
assert govrels==outrels

for portfolio_id,surface_id,_ in bridge.EXPECTED_SURFACES.values():
    mp=copy.deepcopy(p)
    target=None
    for s in mp["portfolios"][portfolio_id]["surfaces"]:
        if s["id"]==surface_id:
            target=s; break
    assert target is not None
    target["proof_routes"]=[x for x in target.get("proof_routes",[]) if x!=bridge.ROUTE]
    bad=ev(portfolios=mp)
    assert bad["status"]=="FAIL_CLOSED"
    assert bad["all_declared_p1_surface_relations_exact_or_superset"] is False

mv=copy.deepcopy(v); mv["scope"]["mechanism_classes"].remove("SCOPE")
bad=ev(v5=mv)
assert bad["status"]=="FAIL_CLOSED" and "V5_MECHANISM_SET_DRIFT" in bad["errors"]

ma=copy.deepcopy(a)
for suite in ma["suites"]:
    if suite.get("id")=="P1_TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_DIRECT":
        suite["oracle"].remove("NOMINATED_REPAIR_RESCUES_TERMINAL_OUTCOME")
bad=ev(absolute_suites=ma)
assert bad["status"]=="FAIL_CLOSED" and "P1_ORACLE_SET_DRIFT" in bad["errors"]

mb=copy.deepcopy(b); mb["terminal_acceptance"]["standalone_synthetic_whole_domain_score_forbidden"]=False
bad=ev(binding=mb)
assert bad["status"]=="FAIL_CLOSED" and "SYNTHETIC_TERMINAL_SCORE_FIREWALL_MISSING" in bad["errors"]

print(json.dumps({
 "status":"INDEPENDENT_PASS__THREE_CLAIM_BOUND_SUPERSET_RELATIONS_FOR_FROZEN_P1_ROLE",
 "exact_blob_shas":actual,
 "claim_ids":sorted(outrels),
 "surface_count":3,
 "relation":"SUPERSET",
 "relation_scope":"UNRESOLVED_SEMANTICS_WITHIN_EXACT_FROZEN_P1_CONTRACT_ROLE_ONLY",
 "full_surface_superset_claim":False,
 "terminal_surface_proof_complete":False,
 "p1_scope_quarantine_clearable":False,
 "new_reality_units_consumed":0,
 "credit_delta":0
},indent=2,sort_keys=True))
