from __future__ import annotations
import json
from pathlib import Path

from canonical.runtime import harbor_science_agent_v1 as science
from canonical.runtime import harbor_science_planner_v1 as planner

PROMPT = """Return one JSON object only. Synthetic preflight, not a benchmark task.
You are only a proposal source; Brain owns execution and finish authority.
On this first cycle provide material_requirements as exactly ["R1"].
Provide one safe candidate object with action_id "A1", covers ["R1"],
command "printf synthetic > /tmp/brain_science_synthetic",
and verify_command "test -s /tmp/brain_science_synthetic".
Do not provide finish_summary yet."""

planned = planner.plan(PROMPT, timeout_s=30)
raw = planner.extract_json_object(planned["text"])
requirements, candidates, finish_summary = science._extract_contract(raw, None)

assert requirements == ["R1"], requirements
assert candidates, raw
candidate = candidates[0]
assert candidate["covers"] == ["R1"], candidate
assert isinstance(candidate["command"], str) and candidate["command"]
assert isinstance(candidate["verify_command"], str) and candidate["verify_command"]
assert finish_summary is None, finish_summary

out = {
    "schema": "PROJECT_BRAIN_TB_SCIENCE_REPAIRED_LIVE_PROPOSAL_BOUNDARY_V1",
    "status": "PASS",
    "planner_model_alias": planned.get("model"),
    "planner_endpoint": planned.get("endpoint"),
    "transport": planned.get("transport"),
    "requirements": requirements,
    "candidate_count": len(candidates),
    "brain_command_policy_admitted_candidate": True,
    "brain_extract_contract_pass": True,
    "synthetic_prompt_only": True,
    "terminal_task_content_read": 0,
    "terminal_trials_executed": 0,
    "terminal_results_observed": 0,
    "incremental_spend_usd": 0,
    "capability_credit_delta": 0,
    "family_credit_delta": 0,
}
Path("TB_SCIENCE_REPAIRED_LIVE_PROPOSAL_BOUNDARY_V1.json").write_text(
    json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
print(json.dumps(out, sort_keys=True))
