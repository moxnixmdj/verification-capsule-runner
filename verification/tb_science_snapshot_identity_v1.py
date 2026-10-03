import json, math, urllib.request

EXPECTED_COMMIT="f81afac4f11048e77a15dfc8fb1dbfb897fea0ce"
AICHARTS="https://aicharts.io/data/benchmark-atlas/terminal-bench-science"
TAG_API="https://api.github.com/repos/harbor-framework/terminal-bench-science/git/ref/tags/v0.1.0"
RELEASE_API="https://api.github.com/repos/harbor-framework/terminal-bench-science/releases/tags/v0.1.0"
ROW_PREFIX="https://hub.harborframework.com/datasets/terminal-bench-science/terminal-bench-science/0.1.0/leaderboards/v0-1-eval/rows/"

def get(url):
    req=urllib.request.Request(url,headers={"User-Agent":"project-brain-independent-verifier/1"})
    with urllib.request.urlopen(req,timeout=30) as r:
        return json.loads(r.read().decode())

atlas=get(AICHARTS)
bench=atlas["benchmark"]
ds=atlas["dataset"]
assert bench["version"]=="0.1.0"
assert ds["version"]=="0.1.0"
assert ds["source"]["revision"]==EXPECTED_COMMIT
assert "/0.1.0" in ds["source"]["url"]
assert ds["observedAt"].startswith("2026-09-23")

rows=[p for p in ds["points"]
      if p.get("model")=="Opus 5.5"
      and p.get("harness")=="Claude Code"
      and p.get("effort")=="max"]
assert len(rows)==1, rows
row=rows[0]
assert row["id"]=="cb24f3a2-82ab-4f97-be88-92a28118bf1c"
assert row["sourceUrl"]==ROW_PREFIX+row["id"]
assert abs(float(row["score"])-(133/210*100)) < 1e-12
assert math.ceil(float(row["score"])*210/100)==133

tag=get(TAG_API)
assert tag["ref"]=="refs/tags/v0.1.0"
assert tag["object"]["type"]=="commit"
assert tag["object"]["sha"]==EXPECTED_COMMIT

release=get(RELEASE_API)
assert release["tag_name"]=="v0.1.0"
assert release["target_commitish"]==EXPECTED_COMMIT
assert "Initial release containing 70 expert-curated research workflow tasks" in release["body"]

out={
  "schema":"PROJECT_BRAIN_TB_SCIENCE_OPUS55_SNAPSHOT_IDENTITY_INDEPENDENT_CHECK_V1",
  "status":"PASS",
  "benchmark_version":"0.1.0",
  "source_revision":EXPECTED_COMMIT,
  "upstream_tag_commit":tag["object"]["sha"],
  "release_target_commitish":release["target_commitish"],
  "opus55_row_id":row["id"],
  "opus55_model":row["model"],
  "opus55_harness":row["harness"],
  "opus55_effort":row["effort"],
  "opus55_score_percent":row["score"],
  "owner_row_url":row["sourceUrl"],
  "slots":210,
  "required_successes":133,
  "fail_lock_failures":78,
  "finalized_failures_already_consumed":3,
  "remaining_failures_before_fail_lock":75,
  "execution_authority":False,
  "promotion_authority":False,
  "capability_credit_delta":0,
  "family_credit_delta":0,
}
print(json.dumps(out,sort_keys=True))
