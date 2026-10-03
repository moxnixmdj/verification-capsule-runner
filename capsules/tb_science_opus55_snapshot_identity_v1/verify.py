from __future__ import annotations
import json, re, urllib.request

UA={"User-Agent":"Project-Brain-Independent-Source-Verifier/1.0"}

def get(url:str)->str:
    req=urllib.request.Request(url,headers=UA)
    with urllib.request.urlopen(req,timeout=60) as r:
        assert int(getattr(r,"status",200))==200,(url,getattr(r,"status",None))
        return r.read().decode("utf-8","replace")

# 1. Exact immutable published source release.
releases=json.loads(get("https://api.github.com/repos/harbor-framework/terminal-bench-science/releases"))
assert len(releases)==1,[x.get("tag_name") for x in releases]
rel=releases[0]
assert rel["tag_name"]=="v0.1.0",rel["tag_name"]
assert rel["target_commitish"]=="f81afac4f11048e77a15dfc8fb1dbfb897fea0ce",rel["target_commitish"]
assert "70 expert-curated" in rel.get("body",""),"RELEASE_TASK_COUNT_NOT_70"

ref=json.loads(get("https://api.github.com/repos/harbor-framework/terminal-bench-science/git/ref/tags/v0.1.0"))
assert ref["object"]["sha"]=="f81afac4f11048e77a15dfc8fb1dbfb897fea0ce",ref

# 2. Current official benchmark site names 0.1, 70 tasks, and its run command pins v0.1.
run=get("https://www.terminal-bench-science.ai/run")
plain=re.sub(r"\s+"," ",run)
assert "Terminal-Bench-Science 0.1" in plain
assert "70 tasks" in plain
assert "terminal-bench-science/terminal-bench-science@v0.1" in plain

# 3. Official/current leaderboard source contains the fresh Opus 5.5 row at 63.3.
snorkel=get("https://snorkel.ai/leaderboard/terminal-bench-science/")
snorkel_plain=re.sub(r"\s+"," ",snorkel)
assert "Terminal-Bench-Science 0.1" in snorkel_plain
assert re.search(r"Opus 5\.5.{0,1500}?63\.3%",snorkel_plain,re.I), "OPUS55_63_3_ROW_NOT_FOUND"
assert re.search(r"70.{0,100}?tasks",snorkel_plain,re.I), "CURRENT_LEADERBOARD_70_TASKS_NOT_FOUND"

# 4. The official Terminal-Bench website hard-redirects its science leaderboard to
# Harbor Hub dataset revision 10, leaderboard v0-1-eval.
cfg=get("https://raw.githubusercontent.com/harbor-framework/terminal-bench-website/main/next.config.mjs")
assert "terminal-bench-science/terminal-bench-science/10?tab=leaderboard&leaderboard=v0-1-eval" in cfg

# 5. Harbor Hub revision 10 exposes aliases 0.1.0/latest/v0.1 and exactly 70 tasks.
hub=get("https://hub.harborframework.com/datasets/terminal-bench-science/terminal-bench-science/10?tab=tasks")
hub_plain=re.sub(r"\s+"," ",hub)
for needle in ("0.1.0","v0.1","70"):
    assert needle in hub_plain,("HUB_REV10_MISSING",needle)

out={
  "schema":"PROJECT_BRAIN_TB_SCIENCE_OPUS55_SNAPSHOT_IDENTITY_SOURCE_VERIFICATION_V1",
  "status":"PASS__CURRENT_63_3_ROW_BINDS_TO_TERMINAL_BENCH_SCIENCE_0_1_RELEASE_LINE__V0_1_ALIAS_BINDS_TO_V0_1_0__EXACT_SOURCE_COMMIT_MATCH",
  "source_release_count":len(releases),
  "release_tag":"v0.1.0",
  "release_commit":"f81afac4f11048e77a15dfc8fb1dbfb897fea0ce",
  "current_leaderboard_label":"Terminal-Bench-Science 0.1",
  "current_opus55_percent":63.3,
  "task_count":70,
  "official_run_alias":"v0.1",
  "official_leaderboard_hub_revision":10,
  "hub_revision_aliases":["0.1.0","latest","v0.1"],
  "terminal_benchmark_trials_executed":0,
  "incremental_spend_usd":0,
}
print(json.dumps(out,sort_keys=True))
