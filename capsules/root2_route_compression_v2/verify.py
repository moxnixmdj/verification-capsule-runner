#!/usr/bin/env python3
from __future__ import annotations
import hashlib, html, json, re, urllib.request
from html.parser import HTMLParser
from pathlib import Path

ROOT=Path(__file__).resolve().parent
EXPECTED_CANDIDATE="dc826cd30a26ed76e8af487dbf722ef872098fbc"
EXPECTED_OS_RECEIPT="4290221e46c05af4c4cb4bc479c800564d9a41c2"

def blob_sha(raw:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def get(url:str)->bytes:
    req=urllib.request.Request(url,headers={"User-Agent":"project-brain-root2-verifier/1.0"})
    with urllib.request.urlopen(req,timeout=35) as r:
        return r.read()

class Text(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts=[]
    def handle_data(self,d):
        self.parts.append(d)
def plain(raw:bytes)->str:
    p=Text(); p.feed(raw.decode("utf-8","replace"))
    return " ".join(" ".join(p.parts).split())

cand_raw=(ROOT/"candidate.json").read_bytes()
osr_raw=(ROOT/"osworld_receipt.json").read_bytes()
assert blob_sha(cand_raw)==EXPECTED_CANDIDATE,(blob_sha(cand_raw),EXPECTED_CANDIDATE)
assert blob_sha(osr_raw)==EXPECTED_OS_RECEIPT,(blob_sha(osr_raw),EXPECTED_OS_RECEIPT)
cand=json.loads(cand_raw)
osr=json.loads(osr_raw)

# Exact public GitHub source bytes.
auto_raw=get("https://raw.githubusercontent.com/zapier/AutomationBench/4a8e1061254004d9dac807054eed33fad7d1ff14/README.md")
chart_raw=get("https://raw.githubusercontent.com/surge-ai/chartography/3f1bf837232d3918c2cc35c6e2418c9e70d2a57b/README.md")
assert blob_sha(auto_raw)=="680d7006e1a05e94c6ce208e91b13dd821d1554f"
assert blob_sha(chart_raw)=="dc534fbfff5fa7f94cd62a567dc73e9747666725"
auto=auto_raw.decode("utf-8")
chart=chart_raw.decode("utf-8")

# AutomationBench: owner explicitly says public != official private score surface.
for phrase in [
    "separate, held-out private task set per domain",
    "purposely harder",
    "may not match the official leaderboard 1:1",
    "likely (but not guaranteed)"
]:
    assert phrase in auto,phrase
a=cand["routes"]["automationbench"]
assert a["official_readme_git_blob_sha"]=="680d7006e1a05e94c6ce208e91b13dd821d1554f"
assert a["official_repository_commit"]=="4a8e1061254004d9dac807054eed33fad7d1ff14"
assert a["search_state"]=="SATURATED_CURRENT_BOUND_EVIDENCE"
assert "PUBLIC600_CANNOT_LOGICALLY_SUBSTITUTE" in a["consequence"]

# Chartography: exact public set, ten epochs, one judge call per sample, exact judge.
assert "all 100 tasks" in chart
assert "one model-graded call per sample" in chart
assert "--epochs 10" in chart
assert "judge_model=google/gemini-3.5-flash" in chart
c=cand["routes"]["chartography"]
m=c["exact_call_mass"]
assert (m["task_count"],m["epochs_per_task"],m["judge_calls_per_sample"])==(100,10,1)
assert m["minimum_judge_call_count"]==1000
assert m["minimum_judge_call_count"]==m["task_count"]*m["epochs_per_task"]*m["judge_calls_per_sample"]
assert c["official_readme_git_blob_sha"]=="dc534fbfff5fa7f94cd62a567dc73e9747666725"
assert c["official_repository_commit"]=="3f1bf837232d3918c2cc35c6e2418c9e70d2a57b"

# Google: zero price does not imply capacity; limits are project-specific.
rate=plain(get("https://ai.google.dev/gemini-api/docs/rate-limits?hl=en"))
assert "Rate limits are applied per project, not per API key." in rate
assert "Specified rate limits are not guaranteed and actual capacity may vary." in rate
assert "View your active rate limits in AI Studio" in rate

pricing=plain(get("https://ai.google.dev/gemini-api/docs/pricing?hl=en"))
start=pricing.find("Gemini 3.5 Flash")
end=pricing.find("Gemini 3.5 Flash-Lite",start+1)
assert start>=0 and end>start
sec=pricing[start:end]
assert re.search(r"Input price\s+Free of charge",sec),sec[:1500]
assert re.search(r"Output price.*?Free of charge",sec),sec[:1500]

# Reused OSWorld proof must be exact and actually independently passed.
o=cand["routes"]["osworld_v2_1"]["reused_verified_boundary"]
assert o["git_blob_sha"]=="f58c12d5c42e1e6b7cdda05d52f978469f3aa300"
assert o["verifier_pull_request"]==1476
assert o["workflow_run_id"]==37161634483
assert o["workflow_job_id"]==111316102614
assert o["conclusion"]=="success"
assert osr["subject"]["git_blob_sha"]=="f58c12d5c42e1e6b7cdda05d52f978469f3aa300"
assert osr["independent_runner"]["workflow_run_id"]==37161634483
assert osr["independent_runner"]["workflow_job_id"]==111316102614
assert osr["independent_runner"]["conclusion"]=="success"
assert osr["verified"]["gitlab_release_revision_absent"] is True

# Frozen targets and zero-credit boundary.
assert cand["invariant_frozen_targets"]=={
    "automationbench_target_percent":40.0,
    "chartography_target_percent":89.0,
    "osworld_v2_1_partial_target_percent":81.8
}
for k in ["acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta","new_reality_units_consumed","terminal_cases_consumed","incremental_spend_usd"]:
    assert cand[k]==0,(k,cand[k])
assert cand["execution_authority"] is False
assert cand["promotion_authority"] is False
assert cand["fresh_reality_authority"] is False

print(json.dumps({
  "schema":"PROJECT_BRAIN_ROOT2_ROUTE_COMPRESSION_V2_PUBLIC_RUNNER_RESULT",
  "status":"PASS__AUTOMATIONBENCH_PUBLIC_PRIVATE_NONSUBSTITUTION__CHARTOGRAPHY_1000_JUDGE_CALL_PROJECT_QUOTA_RESIDUAL__OSWORLD_VERIFIED_BOUNDARY_REUSED__ZERO_CREDIT",
  "pass":True,
  "verified":{
    "candidate_exact_blob":True,
    "automationbench_exact_source":True,
    "automationbench_public_private_nonsubstitution":True,
    "chartography_exact_source":True,
    "chartography_minimum_judge_calls":1000,
    "gemini_free_token_price":True,
    "gemini_limits_per_project":True,
    "gemini_actual_capacity_not_guaranteed":True,
    "osworld_independent_receipt_reused":True,
    "zero_credit":True
  }
},indent=2,sort_keys=True))
