from __future__ import annotations
import html, json, math, re, sys, tomllib
from pathlib import Path

root=Path(sys.argv[1])
anthropic=Path(sys.argv[2]).read_text(encoding="utf-8",errors="replace")
dataset_path=root/"tasks/dataset.toml"
readme_path=root/"README.md"
workflow_path=root/".github/workflows/run-trials.yml"

d=tomllib.loads(dataset_path.read_text(encoding="utf-8"))
tasks=d.get("tasks") or []
names=[str(x["name"]) for x in tasks]
digests=[str(x["digest"]) for x in tasks]
assert len(names)==70, len(names)
assert len(set(names))==70
assert len(set(digests))==70
assert all(x.startswith("terminal-bench-science/") for x in names)
assert all(x.startswith("sha256:") and len(x)==71 for x in digests)

readme=readme_path.read_text(encoding="utf-8")
assert "currently contains <!--TOTAL_COUNT--> **70** expert-curated tasks" in readme

wf=workflow_path.read_text(encoding="utf-8")
assert 'REWARD >= 1.0' in wf
assert 'Harbor outputs "Mean: X.XXX"' in wf
assert "sed -n 's/.*Mean" in wf

plain=html.unescape(re.sub(r"<[^>]+>"," ",anthropic))
plain=re.sub(r"\\s+"," ",plain)
assert "Terminal-Bench-Science 0.1" in plain
assert re.search(r"58[.]7%",plain), "OPUS55_BAR_NOT_FOUND"
assert re.search(r"3 trials/task",plain,re.I), "TRIAL_MULTIPLICITY_NOT_FOUND"

task_count=70
trials_per_task=3
slots=task_count*trials_per_task
bar_percent=58.7
required_successes=math.ceil((bar_percent/100.0)*slots-1e-12)
failure_lock=slots-required_successes+1
assert slots==210
assert required_successes==124
assert failure_lock==87
assert (required_successes/slots)*100 >= bar_percent
assert ((required_successes-1)/slots)*100 < bar_percent

out={
  "schema":"PROJECT_BRAIN_TB_SCIENCE_POPULATION_SCORER_BINDING_V1",
  "status":"PASS__ZERO_CASE_POPULATION_SCORER_AND_INTEGER_THRESHOLD_BOUND",
  "frozen_source_commit":"f81afac4f11048e77a15dfc8fb1dbfb897fea0ce",
  "git_blobs":{
    "tasks/dataset.toml":"b506a7777d2dd5ae3e70c590366ceac4ee59ae28",
    "README.md":"7411791c338ede3e125bc207358bbcda804b24cf",
    ".github/workflows/run-trials.yml":"84d3c4ec560c0d87f3687819d1d07e9c92c982ed",
  },
  "population":{"tasks":task_count,"trials_per_task":trials_per_task,"trial_slots":slots},
  "scoring":{
    "task_trial_pass_rule":"HARBOR_REWARD_GTE_1_0",
    "published_opus55_bar_percent":bar_percent,
    "required_successes":required_successes,
    "pass_lock":"SUCCESS_COUNT_GTE_124",
    "fail_lock":"FAILURE_COUNT_GTE_87",
  },
  "primary_reference":"https://www.anthropic.com/claude-opus-5-5",
  "terminal_task_instruction_files_read":0,
  "terminal_trials_executed":0,
  "terminal_results_observed":0,
  "incremental_spend_usd":0,
  "capability_credit_delta":0,
  "family_credit_delta":0,
}
Path("TB_SCIENCE_POPULATION_SCORER_BINDING_V1.json").write_text(json.dumps(out,indent=2,sort_keys=True)+"\\n",encoding="utf-8")
print(json.dumps(out,sort_keys=True))
