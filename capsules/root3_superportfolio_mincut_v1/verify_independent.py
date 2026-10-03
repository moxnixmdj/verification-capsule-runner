import json
from pathlib import Path
R=Path(__file__).resolve().parent/"brain"
c=json.loads((R/"canonical/governance/ROOT3_MATCHED_SUPERPORTFOLIO_MINIMUM_REALITY_BINDING_V1.json").read_text())
s=json.loads((R/"canonical/governance/OPUS55_MATCHED_COMPARATOR_SUPERPORTFOLIO_V1.json").read_text())
r=json.loads((R/"canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json").read_text())
reg={x["id"]:x for x in r["predicates"]}
rows=c["matched_scope_targets"]
assert len(rows)==8 and len({x["predicate_id"] for x in rows})==8
core={x["family"] for x in s["core_families"]}
optional={x["family"] for x in s["optional_scope_extensions"]}
for x in rows:
    assert reg[x["predicate_id"]]["family"]==x["family"]
    if x["superportfolio_role"]=="CORE":
        assert x["family"] in core
    else:
        assert x["superportfolio_role"]=="OPTIONAL_SCOPE_EXTENSION"
        assert x["family"] in optional
assert c["execution_compression"]["shared_future_superportfolio_wave_count"]==1
assert c["execution_compression"]["per_family_verdicts_remain_independent"] is True
assert c["root3_reality_fallback"]["batch_class_count"]==2
assert s["case_generation"]["generated_now"] is False
assert s["case_generation"]["exposed_now"] is False
assert s["comparator_admissibility"]["current_state"]=="BLOCKED"
assert c["fresh_reality_authority"] is False
print("ROOT3_SUPERPORTFOLIO_MINCUT_INDEPENDENT_PASS")
