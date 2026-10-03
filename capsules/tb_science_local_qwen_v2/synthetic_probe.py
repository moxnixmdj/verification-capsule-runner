from __future__ import annotations
import json
from canonical.runtime import harbor_science_planner_v2 as planner
from canonical.runtime import harbor_science_agent_v2 as agent

FIRST_GOALS = [
    "Create a tiny local text artifact containing the word alpha and independently verify its exact content.",
    "Inspect the current local directory and record a deterministic local-only observation, then verify the observation command succeeds.",
    "Compute the integer sum of 17 and 25 using only the task environment and independently verify the produced result.",
]

CONTINUATION_GOALS = [
    "Continue a bounded local analysis for frozen requirement R1. Propose one local-only action that advances R1 and an independent verification command.",
    "Continue a local file-inspection task for frozen requirement R1. Do not use network acquisition. Propose an action and independent verifier covering R1.",
    "Continue a deterministic local computation for frozen requirement R1. Propose one safe action and verifier covering only R1.",
]

records=[]
for idx,goal in enumerate(FIRST_GOALS):
    prompt=(
        "You are an OPTIONAL semantic proposal source inside Project Brain, not execution authority. "
        "On this first cycle provide material_requirements (1-16 stable short IDs) and 1-8 candidate actions "
        "as {action_id,covers,command,verify_command}. No network acquisition, package installation, "
        "git fetch/clone/pull, secrets, or host escape. Brain owns verification and finish authority. "
        f"Goal: {goal}\nFrozen requirements: None\nUnresolved: []\nRecent observations: []"
    )
    out=planner.plan(prompt,timeout_s=180)
    raw=planner.normalize_proposal_object(planner.extract_json_object(out["text"]))
    requirements,candidates,summary=agent._extract_contract(raw,None)
    assert requirements, raw
    assert candidates, raw
    records.append({
        "kind":"first_cycle",
        "index":idx,
        "requirements":requirements,
        "candidate_count":len(candidates),
        "model":out["model"],
        "transport":out["transport"],
        "external_network_fallback":out["external_network_fallback"],
    })

for idx,goal in enumerate(CONTINUATION_GOALS):
    prompt=(
        "You are an OPTIONAL semantic proposal source inside Project Brain, not execution authority. "
        "Frozen material requirements are already ['R1']; do not mutate them. Provide 1-8 candidate actions "
        "as {action_id,covers,command,verify_command}, with covers naming only R1. No network acquisition, "
        "package installation, git fetch/clone/pull, secrets, or host escape. "
        f"Goal: {goal}\nFrozen requirements: ['R1']\nUnresolved: ['R1']\nRecent observations: []"
    )
    out=planner.plan(prompt,timeout_s=180)
    raw=planner.normalize_proposal_object(planner.extract_json_object(out["text"]))
    requirements,candidates,summary=agent._extract_contract(raw,["R1"])
    assert requirements==["R1"], raw
    assert candidates, raw
    assert all(set(c["covers"]).issubset({"R1"}) for c in candidates), candidates
    records.append({
        "kind":"continuation",
        "index":idx,
        "requirements":requirements,
        "candidate_count":len(candidates),
        "model":out["model"],
        "transport":out["transport"],
        "external_network_fallback":out["external_network_fallback"],
    })

assert len(records)==6
assert all(r["model"]=="brain-qwen3.5-9b" for r in records)
assert all(r["transport"]=="PINNED_LOCAL_OPENAI_TOOL_CALL" for r in records)
assert all(r["external_network_fallback"] is False for r in records)
print(json.dumps({
    "schema":"PROJECT_BRAIN_TB_SCIENCE_LOCAL_QWEN_SYNTHETIC_CONTRACT_RESULT_V1",
    "status":"PASS",
    "synthetic_contracts":len(records),
    "terminal_task_content_read":0,
    "terminal_trials_executed":0,
    "records":records,
},sort_keys=True))
