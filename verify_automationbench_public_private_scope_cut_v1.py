from __future__ import annotations
import hashlib, json, re, urllib.request

COMMIT="4a8e1061254004d9dac807054eed33fad7d1ff14"
URL=f"https://raw.githubusercontent.com/zapier/AutomationBench/{COMMIT}/README.md"
EXPECTED_GIT_BLOB_SHA="680d7006e1a05e94c6ce208e91b13dd821d1554f"

req=urllib.request.Request(URL,headers={"User-Agent":"project-brain-automationbench-scope-verifier/1"})
with urllib.request.urlopen(req,timeout=60) as r:
    data=r.read()
git_blob_sha=hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
assert git_blob_sha==EXPECTED_GIT_BLOB_SHA, (git_blob_sha,EXPECTED_GIT_BLOB_SHA)
text=data.decode("utf-8")
low=re.sub(r"\s+"," ",text).lower()

checks={
    "ships_public_task_set":"this repository ships the **public** task set" in low,
    "official_uses_separate_private":"official** automationbench leaderboard" in low and "separate, held-out private task set" in low,
    "private_purposely_harder":"private set" in low and "purposely harder" in low,
    "local_not_one_to_one":"may not match the official leaderboard 1:1" in low,
    "public_600":"600-task **public** benchmark" in low,
    "opus5_public_50_3":"claude opus 5" in low and "50.3%" in low,
    "opus48_public_41":"claude opus 4.8" in low and "41.00%" in low,
}
assert all(checks.values()), {k:v for k,v in checks.items() if not v}

verdict={
  "schema":"PROJECT_BRAIN_AUTOMATIONBENCH_PUBLIC_PRIVATE_SCOPE_CUT_V1",
  "source_repository":"zapier/AutomationBench",
  "source_commit":COMMIT,
  "source_readme_git_blob_sha":git_blob_sha,
  "checks":checks,
  "deduction":{
    "public_600_is_official_leaderboard_population":False,
    "public_600_score_is_guaranteed_equal_to_private_leaderboard_score":False,
    "public_600_score_can_directly_discharge_private_bar_without_scope_equivalence_proof":False,
    "reason":"PRIMARY_SOURCE_STATES_OFFICIAL_LEADERBOARD_USES_SEPARATE_HELD_OUT_PRIVATE_TASK_SET__PRIVATE_IS_PURPOSELY_HARDER__LOCAL_PUBLIC_SCORES_MAY_NOT_MATCH_1_TO_1"
  },
  "terminal_results_observed":0,
  "incremental_spend_usd":0,
  "capability_credit_delta":0,
  "family_credit_delta":0
}
open("AUTOMATIONBENCH_PUBLIC_PRIVATE_SCOPE_CUT_V1.json","w",encoding="utf-8").write(json.dumps(verdict,indent=2,sort_keys=True)+"\n")
print(json.dumps(verdict,sort_keys=True))
