from __future__ import annotations
import hashlib,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parent

def load(rel):
    return json.loads((ROOT/rel).read_text(encoding="utf-8"))

m=load("EXPECTED_BRAIN_BLOBS.json")
for rel,expected in m["exact_brain_blobs"].items():
    b=(ROOT/rel).read_bytes()
    got=hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
    assert got==expected,(rel,got,expected)

cand=load("canonical/governance/LOCAL_ZERO_REALITY_FIXED_POINT_CANDIDATE_V1.json")
routes=load("canonical/governance/ROOT2_FIXED_BAR_ROUTE_INVENTORY_V1.json")
roots=load("canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json")
cut=load("canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V11.json")
front=load("canonical/governance/ROOT2_ROOT3_MINIMUM_EXECUTION_FRONTIER_V1.json")

root2=set(roots["current_residual_root_partition"]["root2_only"])
root3=set(roots["current_residual_root_partition"]["root3_only"])
root23=set(roots["current_residual_root_partition"]["root2_and_root3"])
score_only=set(routes["route_classes"]["brain_score_only_open"])
assert score_only=={"LIVEBENCH_IF_GE_65_7","TB_SCIENCE_GE_58_7"},score_only
assert score_only <= root2
assert not (score_only & root3)
assert not (score_only & root23)

route_by_pred={}
for row in routes["routes"]:
    for p in row["predicate_ids"]:
        route_by_pred[p]=row

live=route_by_pred["LIVEBENCH_IF_GE_65_7"]
tb=route_by_pred["TB_SCIENCE_GE_58_7"]
assert "BRAIN_SCORE_ONLY_OPEN" in live["state"]
assert "BRAIN_SCORE_ONLY_OPEN" in tb["state"]
assert "PREQUALIFIED" in live["state"]
assert "CARRIER_ATTAINABILITY_INDEPENDENT_PASS" in tb["state"]
assert "NO_FRESH_REALITY" in routes["next"]
assert cut["fresh_reality_authority"] is False
assert front["fresh_reality_authority"] is False

authorized={x["predicate_id"] for x in cand["authorized_candidates"] if x.get("fresh_reality_authority_candidate") is True}
assert authorized==score_only,(authorized,score_only)

for row in routes["routes"]:
    for p in row["predicate_ids"]:
        if p not in score_only:
            assert p not in authorized

assert cand["acceptance_credit_delta"]==0
assert cand["ownership_credit_delta"]==0
assert cand["fresh_reality_authority"] is False
assert cand["execution_authority"] is False
print(json.dumps({
 "status":"INDEPENDENT_PUBLIC_PASS__LOCAL_ZERO_REALITY_CONE_AUTHORIZATION_SOUND_FOR_CURRENT_BOUND_STATE",
 "authorized_predicates":sorted(authorized),
 "unauthorized_unresolved_count":roots["current_residual_root_partition"]["unresolved_total"]-len(authorized),
 "acceptance_credit_delta":0,
 "ownership_credit_delta":0
},indent=2,sort_keys=True))
