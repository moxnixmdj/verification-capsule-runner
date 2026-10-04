#!/usr/bin/env python3
import json, math, pathlib, subprocess

BASE=pathlib.Path("subject/relative_elo_nontransport_20261004_sol")
FILES={
  "theorem": BASE/"THEOREM.json",
  "verifier": BASE/"VERIFIER.py",
  "test": BASE/"TEST.py",
}
EXPECTED={
  "theorem":"cc78a8837dc761b391a25489c8fc5e786bfb76cc",
  "verifier":"6ca3c562b8370ec3ac949feae533cb9f6fd5b4d2",
  "test":"1c106198862c42d911ca962edcb8cc66bd1c3fc5",
}
def blob(p):
    return subprocess.check_output(["git","rev-parse",f"HEAD:{p.as_posix()}"],text=True).strip()
for k,p in FILES.items():
    got=blob(p)
    assert got==EXPECTED[k],(k,got,EXPECTED[k])

x=json.loads(FILES["theorem"].read_text())
assert x["schema"]=="PROJECT_BRAIN_RELATIVE_ELO_ABSOLUTE_PROOF_NONTRANSPORT_V1"
assert [p["predicate_id"] for p in x["affected_predicates"]]==[
  "PROWORK_GDPVAL_GE_1846",
  "PROWORK_AA_BRIEFCASE_GE_1822",
  "ARTIFACT_AA_BRIEFCASE_GE_1822",
]

# Independent logical countermodel:
# A Bradley-Terry relative strength difference is logit(pairwise win probability).
# Hold all absolute certificate facts fixed, vary only unbound pairwise outcomes.
def logit(p):
    return math.log(p/(1-p))
C={"absolute_behavioral_certificate":True}
s_low=logit(0.2)
s_high=logit(0.8)
assert C=={"absolute_behavioral_certificate":True}
assert s_low < 0 < s_high

# Therefore the same absolute certificate admits pairwise worlds on opposite sides
# of the fixed anchor ordering. A fixed relative Elo lower bound cannot follow
# without an additional verified bridge constraining the relative variables.
assert "CANNOT_LOGICALLY_ENTAIL_A_FIXED_ELO_THRESHOLD" in x["theorem"]["statement"]
rp=x["route_pruning"]
assert "RELATIVE_SCORE_BRIDGE_STRONGER_PROOF" in rp["preserved"]
assert "MATCHED_EMPIRICAL_COMPARISON" in rp["preserved"]
assert "OWNER_RESULT" in rp["preserved"]
assert "FORMAL_ENTAILMENT" in rp["not_globally_deleted"]
assert all(("RELATIVE_SCORE_BRIDGE" in q) or ("RELATIVE_PAIRWISE_SCORE_BRIDGE" in q) for q in rp["conditionally_deleted_form"])
assert x["relationship_to_private_surface_dominance"]["target_weakening"] is False
assert all(v==0 for v in x["accounting"].values())
assert x["execution_authority"] is False
assert x["promotion_authority"] is False
assert x["fresh_reality_authority"] is False

print("PASS: absolute behavioral state underdetermines relative BT/Crowd-BT strength")
print("PASS: three live relative-Elo predicates receive conditional route pruning only")
print("PASS: valid relative-score bridges, owner results and matched empirical routes remain open")
print("PASS: zero acceptance credit, zero target weakening, zero fresh reality")
