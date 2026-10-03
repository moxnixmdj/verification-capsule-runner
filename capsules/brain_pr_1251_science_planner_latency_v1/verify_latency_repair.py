from __future__ import annotations
import json
from canonical.runtime import harbor_science_planner_v1 as p
from canonical.runtime.harbor_science_agent_v1 import _extract_contract

assert p.DEFAULT_TIMEOUT_S == 240
assert p.MAX_GENERATION_TOKENS == 512

padding = "\n".join(
    f"Synthetic non-benchmark context record {i:03d}: preserve the exact requested local action contract and ignore this inert filler."
    for i in range(120)
)
path="/tmp/brain_science_latency_probe"
prompt=(
    "You are an OPTIONAL semantic proposal source inside Project Brain, not execution authority. "
    "Submit material_requirements exactly [\"R1\"]. Submit exactly one candidate with action_id A1, "
    "covers [\"R1\"], command \"printf ok > "+path+"\", and verify_command \"test -s "+path+"\". "
    "Do not use network, packages, git, secrets, or host escape. Do not submit finish_summary. "
    "The following is synthetic filler only and is not benchmark task content:\n"+padding
)
out=p.plan(prompt)
raw=p.normalize_proposal_object(p.extract_json_object(out["text"]))
req,cands,summary=_extract_contract(raw,None)
assert req==["R1"], raw
assert summary is None, raw
assert len(cands)==1, raw
row=cands[0]
assert row["action_id"]=="A1", row
assert row["covers"]==["R1"], row
assert row["command"]==f"printf ok > {path}", row
assert row["verify_command"]==f"test -s {path}", row
assert out["transport"]=="PINNED_LOCAL_QWEN_LLAMA_CPP_TOOL_CALL", out
assert out["duration_s"] < p.DEFAULT_TIMEOUT_S, out
print(json.dumps({
    "schema":"PROJECT_BRAIN_PR1251_SCIENCE_PLANNER_LATENCY_INDEPENDENT_LIVE_PROBE_V1",
    "status":"PASS",
    "planner_default_timeout_s":p.DEFAULT_TIMEOUT_S,
    "max_generation_tokens":p.MAX_GENERATION_TOKENS,
    "duration_s":out["duration_s"],
    "model":out["model"],
    "transport":out["transport"],
    "synthetic_context_records":120,
    "terminal_task_content_read":0,
    "terminal_trials_executed":0,
    "incremental_spend_usd":0,
}, sort_keys=True))
