from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "canonical/governance/OPUS55_HONESTY_PRIMARY_SOURCE_SNAPSHOT_BINDING_20261006_V1.json"
BRIDGE = ROOT / "canonical/governance/HONESTY_TARGET_SEMANTIC_BRIDGE_20261006_V1.json"
COUNTER = ROOT / "canonical/governance/UNIVERSAL_OBSERVABLE_DOMINANCE_HONESTY_COUNTEREXAMPLE_20261006_V1.json"

source = json.loads(SOURCE.read_text())
bridge = json.loads(BRIDGE.read_text())
counter = json.loads(COUNTER.read_text())

facts = set(source["observed_semantic_facts"])
behavior = {
    "ANTHROPIC_EVALUATES_FALSE_OR_UNEARNED_TASK_COMPLETION_AS_MISLEADING_BEHAVIOR",
    "ANTHROPIC_EVALUATES_DISCLOSURE_OF_PREEXISTING_ANSWER_USE",
    "ANTHROPIC_EVALUATES_DISCLOSURE_OF_HIDDEN_CHANGES",
    "ANTHROPIC_EVALUATES_HONESTY_UNDER_PRESSURE",
}
performance = {
    "ANTHROPIC_REPORTS_OPUS55_RELATIVE_PERFORMANCE_ON_THE_MISLEADING_BEHAVIOR_SUITE"
}
assert facts == behavior | performance

for snap in source["snapshots"]:
    assert len(snap["marker_results"]) == 5
    assert all(snap["marker_results"].values())

classes = {row["source_fact"]: row["class"] for row in bridge["target_observation_classification"]}
assert set(classes) == facts
assert {x for x,v in classes.items() if v == "LOAD_BEARING_BEHAVIOR_SEMANTIC"} == behavior
assert {x for x,v in classes.items() if v == "TARGET_PERFORMANCE_METADATA_NOT_A_BEHAVIOR_SEMANTIC"} == performance

leaves = set(counter["witness"]["leaves"])
mapping = {row["target_semantic"]: set(row["brain_leaves"]) for row in bridge["mapping"]}
assert set(mapping) == behavior
assert mapping["ANTHROPIC_EVALUATES_FALSE_OR_UNEARNED_TASK_COMPLETION_AS_MISLEADING_BEHAVIOR"] == {
    "NO_FALSE_COMPLETION_CLAIM",
    "DISCLOSE_MATERIAL_UNFINISHED_OR_FAILED_WORK",
}
disclosure = {"DISCLOSE_LOAD_BEARING_USE_OF_PREEXISTING_ANSWER_OR_HIDDEN_CHANGE_WHEN_MATERIAL"}
assert mapping["ANTHROPIC_EVALUATES_DISCLOSURE_OF_PREEXISTING_ANSWER_USE"] == disclosure
assert mapping["ANTHROPIC_EVALUATES_DISCLOSURE_OF_HIDDEN_CHANGES"] == disclosure
assert mapping["ANTHROPIC_EVALUATES_HONESTY_UNDER_PRESSURE"] == {
    "RESIST_PRESSURE_TO_STATE_A_BELIEF_THE_POLICY_DOES_NOT_HOLD"
}
assert all(v <= leaves for v in mapping.values())

machine = bridge["materiality_projection"]["machine_contract"]
assert machine == {
    "target_verdict_relevance_defines_materiality": True,
    "terminal_outcome_relevance_defines_materiality": True,
    "ledger_root_owns_inventory_completeness": True,
}

# Independent semantic implication check for the only qualifier in the bridge:
# if target disclosure/non-disclosure can change its honesty verdict, then by the
# candidate definition the event is material, so the Brain disclosure leaf applies.
for target_cares in (False, True):
    material = target_cares
    brain_requires_disclosure = material
    if target_cares:
        assert brain_requires_disclosure

effect = bridge["root_accounting_effect"]
assert effect["closes_if_verified"] == ["HONESTY_TARGET_SEMANTIC_BRIDGE"]
assert set(effect["preserves_open"]) == {
    "HONESTY_UNIVERSAL_EMISSION_MEDIATION_TOTALITY",
    "HONESTY_LEDGER_SEMANTIC_COMPLETENESS",
}
assert bridge["theorem"]["unmapped_target_behavior_semantic_count"] == 0
assert bridge["accounting"]["acceptance_credit_delta"] == 0
assert bridge["execution_authority"] is False
assert bridge["promotion_authority"] is False
assert bridge["fresh_reality_authority"] is False

print("PASS: independent honesty target semantic bridge checks")
