#!/usr/bin/env python3
from __future__ import annotations
import html, json, re, urllib.request

FRONTIER_11="https://cognition.com/blog/frontier-code-1.1"
FRONTIER_INTRO="https://cognition.com/blog/frontier-code"
CURSOR_BENCH="https://cursor.com/cursorbench"
CURSOR_BLOG="https://cursor.com/blog/cursorbench"

def get(url:str)->str:
    req=urllib.request.Request(url,headers={
        "User-Agent":"Mozilla/5.0 Project-Brain-Zero-Reality-Verifier/1.0",
        "Accept":"text/html,text/plain,*/*",
    })
    with urllib.request.urlopen(req,timeout=30) as r:
        return r.read().decode("utf-8","replace")

def textify(s:str)->str:
    s=re.sub(r"<script\b[^>]*>.*?</script>"," ",s,flags=re.I|re.S)
    s=re.sub(r"<style\b[^>]*>.*?</style>"," ",s,flags=re.I|re.S)
    s=re.sub(r"<[^>]+>"," ",s)
    s=html.unescape(s).replace("’","'").replace("“",'"').replace("”",'"')
    return re.sub(r"\s+"," ",s).strip()

f11=textify(get(FRONTIER_11))
fi=textify(get(FRONTIER_INTRO))
cb=textify(get(CURSOR_BENCH))
cblog=textify(get(CURSOR_BLOG))

facts={
  "frontiercode_11_identity":"FrontierCode 1.1" in f11,
  "frontiercode_main_100":bool(re.search(r"Main\s+(?:comprises|consists of).*?100",f11+" "+fi,re.I)),
  "frontiercode_tasks_not_planned_public":bool(re.search(r"don't currently plan to release the tasks publicly",fi,re.I)),
  "frontiercode_owner_eval_open_to_model_creators":bool(re.search(r"opening up our evaluation to all model creators",fi,re.I)),
  "cursorbench_40_identity":"CursorBench 4.0" in cb,
  "cursorbench_internal_suite":bool(re.search(r"internal eval suite based on real Cursor sessions",cblog,re.I)),
  "cursorbench_internal_or_controlled_sources":bool(re.search(r"many tasks come from our internal codebase and controlled sources",cblog,re.I)),
  "cursorbench_real_sessions":bool(re.search(r"real Cursor sessions",cb+" "+cblog,re.I)),
}
missing=[k for k,v in facts.items() if not v]
out={
 "schema":"PROJECT_BRAIN_FRONTIERCODE_CURSORBENCH_OWNER_ROUTE_BOUNDARY_V1",
 "status":"PASS__FIRST_PARTY_OWNER_ROUTE_BOUNDARIES_PROVED__PUBLIC_EXACT_SELF_RUN_NOT_ESTABLISHED__ZERO_CREDIT" if not missing else "FAIL_CLOSED__SOURCE_FACT_MISSING",
 "pass":not missing,
 "facts":facts,
 "missing":missing,
 "sources":{
   "frontiercode_11":FRONTIER_11,
   "frontiercode_intro":FRONTIER_INTRO,
   "cursorbench_40":CURSOR_BENCH,
   "cursorbench_methodology":CURSOR_BLOG,
 },
 "derived":{
   "frontiercode_public_exact_self_run_route":"NOT_ESTABLISHED__FIRST_PARTY_STATES_TASKS_NOT_PLANNED_FOR_PUBLIC_RELEASE",
   "frontiercode_remaining_exact_route":"COGNITION_OWNER_EVALUATION_ACCESS_OR_SEPARATELY_ADMISSIBLE_STRONGER_PROOF",
   "cursorbench_public_exact_self_run_route":"NOT_ESTABLISHED__FIRST_PARTY_IDENTIFIES_INTERNAL_EVAL_SUITE_AND_INTERNAL_CONTROLLED_TASK_SOURCES",
   "cursorbench_remaining_exact_route":"CURSOR_OWNER_EVALUATION_ACCESS_OR_SEPARATELY_ADMISSIBLE_STRONGER_PROOF",
 },
 "hard_nonclaims":[
   "NO_CLAIM_THAT_OWNER_ACCESS_CAN_NEVER_BE_GRANTED",
   "NO_CLAIM_THAT_NO_SCOPE_EQUIVALENT_STRONGER_PROOF_CAN_EXIST",
   "NO_BENCHMARK_TASK_CONTENT_READ",
   "NO_BRAIN_SCORE",
   "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
 ],
 "terminal_cases_consumed":0,
 "new_reality_units_consumed":0,
 "incremental_spend_usd":0,
 "acceptance_credit_delta":0,
 "family_credit_delta":0,
 "capability_credit_delta":0,
 "ownership_credit_delta":0,
 "execution_authority":False,
 "promotion_authority":False,
 "fresh_reality_authority":False,
}
print(json.dumps(out,indent=2,sort_keys=True))
raise SystemExit(0 if out["pass"] else 1)
