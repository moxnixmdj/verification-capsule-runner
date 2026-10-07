#!/usr/bin/env bash
set -euo pipefail
cd capsules/terminal_one_shot_attack_v1
test "$(git hash-object canonical/runtime/terminal_autopilot_v1.py)" = "3ebdcdac161d818f88d2a864f9cfce061190f846"
test "$(git hash-object canonical/tests/test_terminal_autopilot_v1.py)" = "94dd8ce92561cc15061c20891beab6df281a23da"
test "$(git hash-object canonical/governance/TERMINAL_ONE_SHOT_ATTACK_CURRENT_MANIFEST_20261007_V1.json)" = "c2c221799a28c7f2c60d178445091c0a6e413041"
python -m unittest -v canonical.tests.test_terminal_autopilot_v1
python canonical/runtime/terminal_autopilot_v1.py canonical/governance/TERMINAL_ONE_SHOT_ATTACK_CURRENT_MANIFEST_20261007_V1.json > verdict.json
python - <<'PY'
import json
v=json.load(open("verdict.json"))
assert v["pass"] is True, v
assert v["classification"]=="AUTOPILOT_PLAN", v
assert v["open_obligation_count"]==13, v
assert v["active_target_count"]==1, v
routes=[x for x in v["dispatch"] if x["kind"]=="ROUTE_RACE"]
evidence=[x for x in v["dispatch"] if x["kind"]=="EVIDENCE"]
assert len(routes)==6, routes
assert len(evidence)==12, evidence
assert len(v["dispatch"])==18, v["dispatch"]
assert v["dispatch"][0]["route_id"]=="SCOPE_COMPLETE_UNIVERSAL_COVER", v["dispatch"][0]
assert "TB_SCIENCE_GE_58_7" not in [x["obligation_ids"][0] for x in evidence], evidence
assert {x["route_id"] for x in routes}=={
  "SCOPE_COMPLETE_UNIVERSAL_COVER",
  "OBJECTIVE_ACCEPTANCE_COMMON_LAW",
  "PROFESSIONAL_QUALITATIVE_ROBUST_DOMINANCE",
  "CODING_TRIAD_SCOPE_COMPLETE_COVER",
  "FINANCE_MYSTERY_COMMON_POLICY_COVER",
  "GDPVAL_FINITE_PUBLIC_ACCEPTANCE_COVER",
}, routes
assert v["verify"]==[] and v["promote"]==[], v
assert v["terminal_credit"] is False, v
print("TERMINAL_ONE_SHOT_CURRENT_PLAN_PASS")
PY
