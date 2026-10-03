#!/usr/bin/env bash
set -euo pipefail

python -m unittest -v canonical.tests.test_terminal_projection_consistency_v1
python canonical/runtime/terminal_projection_consistency_v1.py > /tmp/projection.json

python -m unittest -v canonical.tests.test_current_terminal_scheduling_world_v1
python canonical/runtime/current_terminal_scheduling_world_v1.py > /tmp/world.json

python -m unittest -v canonical.tests.test_terminal_next_action_compiler_v1
python canonical/runtime/terminal_next_action_compiler_v1.py > /tmp/next.json

python - <<'PY'
import hashlib,json
from pathlib import Path
root=Path(".")
def load(p): return json.loads((root/p).read_text())
def blob(p):
    b=(root/p).read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
c=load("canonical/governance/CURRENT_TERMINAL_SCHEDULING_WORLD_V2.json")
for key,row in c["exact_inputs"].items():
    p=row.get("path"); h=row.get("git_blob_sha")
    if p and h:
        assert blob(p)==h,(key,p,blob(p),h)
w=json.load(open("/tmp/world.json"))
assert w["pass"] is True,w
assert (w["registry_predicate_count"],w["proved_predicate_count"],w["unresolved_predicate_count"])==(38,11,27),w
assert w["live_action_coverage_count"]==27,w
assert w["uncovered_predicates"]==[],w
for pid in c["expected_live_world"]["newly_removed_predicates"]:
    assert pid in w["proved_predicates"],(pid,w)
    assert pid not in w["unresolved_predicates"],(pid,w)
assert c["expected_live_world"]["still_unresolved_predicate"] in w["unresolved_predicates"],w
assert c["execution_authority"] is False and c["fresh_reality_authority"] is False
print("SCHEDULING_V2_EXACT_INPUTS_AND_WORLD_PASS")
PY

python - <<'PY'
import json
from pathlib import Path
from canonical.runtime.terminal_action_coverage_guard_v1 import evaluate as coverage
from canonical.runtime.reopened_objective_route_compiler_v1 import evaluate as routes
L=lambda p:json.loads(Path(p).read_text())
e=L("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json")
r=L("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json")
h=L("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V1.json")
c=coverage(r,e,h)
assert c["status"]=="PASS",c
assert c["unresolved_predicate_count"]==27,c
assert c["represented_unresolved_predicate_count"]==27,c
assert c["uncovered_unresolved_predicates"]==[],c
o=routes(
 r,
 L("canonical/governance/OPUS55_REOPENED_OBJECTIVE_ROUTE_RESIDUAL_V1.json"),
 L("canonical/verification/CURRENT_OBJECTIVE_BINDINGS_PUBLIC_RUNNER_VERIFICATION_20261002_V2.json"),
 e,
)
assert o["status"]=="PASS",o
proved={x["predicate_id"] for x in e["claims"] if x.get("state")=="PROVED"}
cand=set(o["candidate_predicates"])
assert cand.isdisjoint(proved),(cand,proved,o)
assert set(o["already_proved_matched_predicates"]).issubset(proved),o
assert "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR" in cand,o
for pid in (
 "DELEGATION_TERMINAL_SUCCESS_NONINFERIOR",
 "RECOVERY_CAUSAL_LOCALIZATION_NONINFERIOR",
 "RECOVERY_TERMINAL_NONINFERIOR",
 "RECOVERY_ZERO_CRITICAL_FAIL_CLOSED_MISSES",
):
    assert pid not in cand,(pid,o)
print("ACTION_COVERAGE_AND_REOPENED_ROUTE_PASS")
PY

python - <<'PY'
import json,re
from pathlib import Path
L=lambda p:json.loads(Path(p).read_text())
t=L("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")
h=L("canonical/governance/ACTIVE_GOAL_HIERARCHY_V1.json")
u=L("canonical/governance/RESIDUAL_ACTION_UNIVERSE_V2.json")
p=L("canonical/CANONICAL_POINTER.json")
s=L("canonical/governance/REAL_OUTPUT_SCOREBOARD_V1.json")
o=L("canonical/capabilities/frontier/OPUS_5_5_USEFUL_CAPABILITY_OWNERSHIP_V1.json")
m=re.fullmatch(r"(\d+)/(\d+)_PASS__(\d+)/(\d+)_OPEN",t["truth"]["opus55_acceptance"])
assert m and m.group(2)==m.group(4)
accepted,total,open_count=map(int,(m.group(1),m.group(2),m.group(3)))
proved=t["atomic_acceptance_frontier"]["proved"]; unresolved=t["atomic_acceptance_frontier"]["unresolved"]; atom_total=t["atomic_acceptance_frontier"]["total"]
assert (accepted,total,open_count,proved,unresolved,atom_total)==(4,19,15,11,27,38)
n=t["next"]
b=f"TERMINAL_FALSE__{open_count}_OF_{total}_FAMILIES_OPEN__{unresolved}_OF_{atom_total}_ATOMIC_PREDICATES_UNRESOLVED__SEE_CURRENT_TERMINAL_AUTHORITY_NEXT_FOR_EXACT_ACTIVE_ROUTE"
e="CURRENT_TERMINAL_AUTHORITY_NEXT_PASS_OR_FALSIFICATION__OR_ANOTHER_CAUSALLY_BOUND_ZERO_REALITY_DELTA__NO_TERMINAL_PROMOTION_WITHOUT_SEPARATE_INDEPENDENT_REDUCTION"
assert h["current_parent_blocker"]==b and h["next_required_action_class"]==n and h["next_progress_event_target"]==e
assert p["current_frontier"]["critical_blocker"]==b and p["current_frontier"]["highest_leverage_capability_gap"]==b and p["current_frontier"]["next_step"]==n
af=s["active_frontier_accounting"]
assert af["residual_gap"]==b and af["current_parent_blocker"]==b and af["next_required_action"]==n
assert s["next_required_action"]==n and s["next_progress_event_target"]==e
ca=s["canonical_acceptance_truth"]
assert (ca["accepted_families"],ca["open_families"],ca["total_families"])==(4,15,19)
assert (ca["proved_atomic_predicates"],ca["unresolved_atomic_predicates"],ca["total_atomic_predicates"])==(11,27,38)
assert o["residual_gap"]==b and o["current_atomic_blocker"]==b and o["next_action"]==n and o["current_atomic_next_action"]==n and o["next_progress_event_target"]==e
oa=o["acceptance_truth"]
assert (oa["accepted_families"],oa["total_families"],oa["proved_atomic_predicates"],oa["unresolved_atomic_predicates"],oa["total_atomic_predicates"])==(4,19,11,27,38)
assert h["residual_action_universe_v2"]["status"]==u["status"]
assert h["residual_action_universe_v2"]["exact_cut_ready"]==u["exact_cut_ready"]
assert h["residual_action_universe_v2"]["blocking_obligations"]==u["blocking_obligations"]==[]
assert u["exact_cut_ready"] is True
v=L("canonical/governance/RESIDUAL_MINIMUM_REALITY_CUT_VERDICT_V6.json")
assert v["status"].startswith("VERIFIED_EXACT_MINIMUM") and v["observation_count"]==2 and v["total_cost"]==2
print("FRONTIER_PROJECTION_PASS")
PY

PYTHONPATH=. python canonical/tests/test_global_terminal_universe.py

python - <<'PY'
import json
from pathlib import Path
L=lambda p:json.loads(Path(p).read_text())
a=L("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")
m=L("canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json")
e=L("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json")
assert a["truth"]["opus55_acceptance"]=="4/19_PASS__15/19_OPEN"
assert (a["atomic_acceptance_frontier"]["proved"],a["atomic_acceptance_frontier"]["unresolved"])==(11,27)
assert a["atomic_acceptance_frontier"]["source_git_blob_sha"]=="e62c732937d4dae4eb5297dff96d354dcc52236e"
assert e["saturation"]["proved_predicate_count"]==11 and e["saturation"]["unresolved_predicate_count"]==27
assert m["postwave_acceptance_summary"]["calibrated_family_count"]==4
assert m["postwave_acceptance_summary"]["verified_owned_family_count"]==2
rr=next(x for x in m["rows"] if x["family"]=="SELF_VERIFICATION_DEBUGGING_AND_RECOVERY")
assert rr["postwave_ownership_credit"]=="ZERO_DIRECT_CREDIT__PROMOTION_AUTHORITY_FALSE"
assert a["truth"]["achieved"] is False
print("RECOVERY_4_OF_19_PROMOTION_VERIFICATION_PASS")
PY
