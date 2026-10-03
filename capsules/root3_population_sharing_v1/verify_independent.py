import json
from pathlib import Path

R=Path(__file__).resolve().parent/"brain"
c=json.loads((R/"canonical/governance/ROOT3_TARGET_POPULATION_COALESCENCE_V1.json").read_text())
p=json.loads((R/"canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json").read_text())
r=json.loads((R/"canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json").read_text())
prot={x["family"]:x for x in p["protocols"]}
reg={x["id"]:x for x in r["predicates"]}
groups=c["population_groups"]
assert len(groups)==4
all_ids=[]
shared=0
for g in groups:
    fam=g["family"]; ids=g["predicate_ids"]; lit=g["protocol_literal"]
    a=prot[fam]["acceptance"]
    assert (a==lit) if isinstance(a,str) else (lit in a)
    for pid in ids:
        assert reg[pid]["family"]==fam
    all_ids.extend(ids)
    shared += int(len(ids)>1)
assert len(all_ids)==7 and len(set(all_ids))==7
assert shared==3
assert c["accounting"]["duplicate_population_definitions_eliminated"]==3
assert c["accounting"]["scope_completeness_predicates_closed"]==0
assert c["accounting"]["acceptance_predicates_closed"]==0
assert c["fresh_reality_authority"] is False
print("ROOT3_POPULATION_SHARING_INDEPENDENT_PASS")
