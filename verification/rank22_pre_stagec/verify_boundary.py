import json
from pathlib import Path

p=Path(__file__).parent/"ledger.json"
x=json.loads(p.read_text())
assert x["task"]=="freecad-spring-clip"
assert x["rank"]==22
assert x["state"]=="EXPOSED__STAGE_B_POST_INSTRUCTION_PRE_EXECUTION"
assert x["instruction_read"] is True
assert x["hidden_verifier_read"] is False
assert x["task_specific_hints_read"] is False
assert x["task_specific_web_or_repo_search"] is False
assert x["task_command_executed"] is False
assert x["disqualifying_exposure_events"]==[]
assert x["source_boundary_status"]=="PASS__EXACT_ALLOWLISTED_READS_ONLY__NO_DISCOVERY_SEARCH_AFTER_EXPOSURE__NO_TESTS_SOLUTION_VERIFIER_HINTS"
reads=x["allowed_stage_b_reads"]
assert len(reads)==3
assert reads[0]["path"]=="tasks/freecad-spring-clip/instruction.md" and reads[0]["blob"]=="4d80d20b8d6404e68728efda4dfd79d315a9d20d"
assert reads[1]["path"]=="tasks/freecad-spring-clip/task.toml" and reads[1]["blob"]=="4fa89d7788a5d56f3d073ce54d46dcdad0a7b012"
assert reads[2]["path"]=="tasks/freecad-spring-clip/environment/" and reads[2]["tree"]=="1bb433cd0994aa4f88e4e9d52040fd880e59b919"
print(json.dumps({
 "pass": True,
 "task": x["task"],
 "rank": x["rank"],
 "state": x["state"],
 "allowlisted_reads": len(reads),
 "disqualifying_events": 0,
 "task_commands": 0,
 "hidden_verifier_reads": 0,
 "source_boundary": "PASS"
},sort_keys=True))
