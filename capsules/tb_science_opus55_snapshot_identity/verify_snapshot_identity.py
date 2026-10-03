from __future__ import annotations
import html
import json
import math
import re
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parent
PREQ=json.loads((ROOT/"prequalification.json").read_text())
FRESH=json.loads((ROOT/"freshness.json").read_text())

TAG_COMMIT="f81afac4f11048e77a15dfc8fb1dbfb897fea0ce"
DATASET_HASH="sha256:91531bf50016a7c64f6cc60794a17c64c6b2c14858a8ae0de39ca16f2abd611a"
SCORE=63.3
TASKS=70
TRIALS=3
SLOTS=TASKS*TRIALS

def get(url: str) -> bytes:
    req=urllib.request.Request(url,headers={"User-Agent":"ProjectBrain-TBScience-SnapshotVerifier/1.0"})
    with urllib.request.urlopen(req,timeout=30) as r:
        return r.read(8_000_000)

def text(url: str) -> str:
    raw=get(url).decode("utf-8","replace")
    raw=re.sub(r"<script\b[^>]*>.*?</script>"," ",raw,flags=re.S|re.I)
    raw=re.sub(r"<style\b[^>]*>.*?</style>"," ",raw,flags=re.S|re.I)
    raw=re.sub(r"<[^>]+>"," ",raw)
    return re.sub(r"\s+"," ",html.unescape(raw)).strip()

assert PREQ["brain_basis"]["dataset_content_hash"]==DATASET_HASH
assert "EXACT_PUBLIC_TB_SCIENCE_0_1_0_DATASET_CONTENT_HASH_BOUND" in PREQ["proved"]
assert FRESH["fresh_public_observation"]["resolution_rate_percent"]==SCORE
assert FRESH["fresh_public_observation"]["task_count"]==TASKS
assert FRESH["fresh_public_observation"]["trials_per_task"]==TRIALS

snorkel=text("https://snorkel.ai/leaderboard/terminal-bench-science/")
assert "70 tasks in the v0.1 release" in snorkel
assert "Terminal-Bench-Science 0.1" in snorkel
assert re.search(r"Opus 5\.5\s+Claude Code\s+max\s+63\.3%\s*±3\.3",snorkel), snorkel[:4000]

announcement=text("https://www.terminal-bench-science.ai/announcement")
for token in ["Terminal-Bench-Science 0.1","70","three independent trials"]:
    assert token.lower() in announcement.lower(), token

releasing=get("https://raw.githubusercontent.com/harbor-framework/terminal-bench-science/main/RELEASING.md").decode()
assert "releases are immutable benchmark snapshots" in releasing
assert "Release tags must point to commits on" in releasing
assert "must never be moved after publication" in releasing

releases=json.loads(get("https://api.github.com/repos/harbor-framework/terminal-bench-science/releases?per_page=100"))
v01=[x for x in releases if str(x.get("tag_name","")).startswith("v0.1.")]
assert len(v01)==1, [x.get("tag_name") for x in v01]
release=v01[0]
assert release["tag_name"]=="v0.1.0"
assert release["target_commitish"]==TAG_COMMIT
assert "70 expert-curated" in release.get("body","")

tag=json.loads(get("https://api.github.com/repos/harbor-framework/terminal-bench-science/git/ref/tags/v0.1.0"))
assert tag["object"]["type"]=="commit"
assert tag["object"]["sha"]==TAG_COMMIT

commit=json.loads(get(f"https://api.github.com/repos/harbor-framework/terminal-bench-science/commits/{TAG_COMMIT}"))
assert commit["sha"]==TAG_COMMIT
assert "Freeze the first 70-task snapshot" in commit["commit"]["message"]

required=math.ceil(SLOTS*SCORE/100.0)
fail_lock=SLOTS-required+1
consumed=3
remaining_failures=fail_lock-consumed
p=required/SLOTS
se=math.sqrt(p*(1-p)/SLOTS)*100.0
assert required==133
assert fail_lock==78
assert remaining_failures==75
assert abs(se-3.3)<0.15, se

receipt={
  "schema":"PROJECT_BRAIN_TB_SCIENCE_OPUS55_SNAPSHOT_IDENTITY_VERIFICATION_V1",
  "status":"PASS__CURRENT_PUBLIC_OPUS55_63_3_BOUND_TO_IMMUTABLE_V0_1_0_RELEASE__EFFECTIVE_THRESHOLD_133_OF_210",
  "proof_chain":{
    "leaderboard_label":"Terminal-Bench-Science 0.1",
    "leaderboard_task_count":70,
    "leaderboard_trials_per_task":3,
    "leaderboard_opus55_percent":63.3,
    "leaderboard_reported_standard_error_points":3.3,
    "release_tag":"v0.1.0",
    "release_tag_commit":TAG_COMMIT,
    "v0_1_release_count":1,
    "release_policy_immutable_snapshots":True,
    "release_tags_never_move":True,
    "brain_exact_public_v0_1_0_dataset_hash_bound":True,
    "brain_dataset_hash":DATASET_HASH,
  },
  "arithmetic":{
    "tasks":TASKS,
    "trials_per_task":TRIALS,
    "slots":SLOTS,
    "required_successes":required,
    "fail_lock_failures":fail_lock,
    "already_consumed_failures":consumed,
    "remaining_failures_before_fail_lock":remaining_failures,
    "required_overall_fraction":required/SLOTS,
    "binomial_se_points_at_133_of_210":se,
  },
  "hard_nonclaims":[
    "NO_CLAIM_CLAUDE_CODE_AGENT_EQUALS_BRAIN_AGENT",
    "NO_CLAIM_63_3_IS_ANTHROPIC_SELF_REPORTED_SCORE",
    "NO_TERMINAL_TASK_CONTENT_READ",
    "NO_TERMINAL_TRIAL_EXECUTED"
  ],
  "terminal_task_content_read":0,
  "terminal_trials_executed":0,
  "incremental_spend_usd":0,
  "execution_authority":False,
  "promotion_authority":False,
  "capability_credit_delta":0,
  "family_credit_delta":0,
}
print(json.dumps(receipt,sort_keys=True))
