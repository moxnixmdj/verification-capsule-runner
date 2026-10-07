#!/usr/bin/env python3
from __future__ import annotations
import hashlib, html, json, re, urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SUBJECT=ROOT/"SUBJECT.json"
EXPECTED_BRAIN_BLOB="7434040c58142a0f4f537b2ad8ec23223acd38e3"

URLS={
 "credit":"https://help.arena.ai/articles/5476762589-credit-sytem",
 "selector":"https://help.arena.ai/articles/1858200927-lmarena-experiments-new-model-selector",
 "agent":"https://arena.ai/leaderboard/agent/code",
 "changelog":"https://arena.ai/company/leaderboard-changelog",
}

def git_blob_sha(raw:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\\0"+raw).hexdigest()

def fetch(url:str)->str:
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 Project-Brain-independent-verifier/1.0"})
    with urllib.request.urlopen(req,timeout=30) as r:
        raw=r.read().decode("utf-8","replace")
    text=html.unescape(re.sub(r"<[^>]+>"," ",raw))
    return re.sub(r"\\s+"," ",text).strip().lower()

def main()->int:
    raw=SUBJECT.read_bytes()
    doc=json.loads(raw)
    errors=[]
    if git_blob_sha(raw)!=EXPECTED_BRAIN_BLOB:
        errors.append("SUBJECT_GIT_BLOB_MISMATCH")
    pages={}
    for key,url in URLS.items():
        try: pages[key]=fetch(url)
        except Exception as exc: errors.append("FETCH_FAILED:"+key+":"+type(exc).__name__)
    if "credit" in pages:
        if "daily balance of usage credits" not in pages["credit"] or "used for free" not in pages["credit"]:
            errors.append("FREE_DAILY_CREDIT_SEMANTICS_NOT_REPRODUCED")
    if "selector" in pages:
        if "direct and side by side" not in pages["selector"] or "select a model" not in pages["selector"]:
            errors.append("SPECIFIC_MODEL_SELECTOR_SEMANTICS_NOT_REPRODUCED")
    if "agent" in pages and "claude opus 5.5 (high)" not in pages["agent"]:
        errors.append("OPUS55_HIGH_AGENT_PRESENCE_NOT_REPRODUCED")
    if "changelog" in pages:
        if "claude-opus-5.5-high" not in pages["changelog"] or "claude opus 5.5 (high)" not in pages["changelog"]:
            errors.append("OPUS55_CHANGELOG_PRESENCE_NOT_REPRODUCED")

    nonclaims=set(doc.get("hard_nonclaims") or [])
    required_nonclaims={
      "NO_CLAIM_CLAUDE_OPUS_5_5_IS_CURRENTLY_SELECTABLE_IN_THE_USER_ACCOUNT",
      "NO_CLAIM_FREE_DAILY_CREDITS_ARE_SUFFICIENT_FOR_ANY_MATCHED_TERMINAL_WAVE",
      "NO_CLAIM_ARENA_API_IS_ZERO_COST",
      "NO_COMPARATOR_EXECUTION",
      "NO_FRESH_REALITY_AUTHORITY",
      "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
      "NO_TERMINAL_FINALITY",
    }
    if not required_nonclaims <= nonclaims:
        errors.append("HARD_NONCLAIMS_INCOMPLETE")
    acct=doc.get("accounting") or {}
    for k in ("incremental_spend_usd","new_reality_units_consumed","terminal_cases_consumed","acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta"):
        if acct.get(k)!=0: errors.append("NONZERO_ACCOUNTING:"+k)
    if doc.get("execution_authority") is not False: errors.append("EXECUTION_AUTHORITY")
    if doc.get("promotion_authority") is not False: errors.append("PROMOTION_AUTHORITY")
    if doc.get("fresh_reality_authority") is not False: errors.append("FRESH_REALITY_AUTHORITY")
    if doc.get("scheduling_authority") is not False: errors.append("PREMATURE_SCHEDULING_AUTHORITY")
    out={
      "schema":"PROJECT_BRAIN_ARENA_ZERO_COST_DIRECT_COMPARATOR_TRUTH_REPAIR_PUBLIC_VERDICT_V1",
      "status":"PASS" if not errors else "FAIL_CLOSED",
      "pass":not errors,
      "errors":errors,
      "subject_git_blob_sha":git_blob_sha(raw),
      "verified_public_facts":[
        "ARENA_DAILY_FREE_USAGE_CREDIT_BALANCE",
        "ARENA_DIRECT_SPECIFIC_MODEL_SELECTOR",
        "ARENA_CURRENT_CLAUDE_OPUS55_PLATFORM_PRESENCE",
      ] if not errors else [],
      "still_open":[
        "ACCOUNT_SPECIFIC_EXACT_OPUS55_DIRECT_SELECTABILITY",
        "SUFFICIENT_FREE_CREDIT_FOR_REQUIRED_WORKLOAD",
        "HARNESS_AND_EFFORT_IDENTITY",
        "CASE_LEVEL_PROVENANCE_AND_NO_SUBSTITUTION",
      ],
      "incremental_spend_usd":0,
      "new_reality_units_consumed":0,
      "terminal_cases_consumed":0,
      "acceptance_credit_delta":0,
      "family_credit_delta":0,
      "capability_credit_delta":0,
      "ownership_credit_delta":0,
      "execution_authority":False,
      "promotion_authority":False,
      "fresh_reality_authority":False,
    }
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if not errors else 1

if __name__=="__main__":
    raise SystemExit(main())
