#!/usr/bin/env python3
from __future__ import annotations
import html, json, re, urllib.request

AA_URL="https://artificialanalysis.ai/methodology/intelligence-benchmarking"
OPENAI_URL="https://openai.com/index/gdpval/"
STIRRUP_RAW="https://raw.githubusercontent.com/ArtificialAnalysis/Stirrup/247f24d56b2108235880ed2a2baea5d35b5a67ee/pyproject.toml"

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
    s=html.unescape(s)
    return re.sub(r"\s+"," ",s).strip()

aa=textify(get(AA_URL))
op=textify(get(OPENAI_URL))
st=get(STIRRUP_RAW)

facts={
  "aa_names_gdpval_v21":"GDPval-AA v2.1" in aa,
  "aa_220_tasks":bool(re.search(r"GDPval-AA v2\.1.{0,500}?220\s+tasks",aa,re.I)),
  "aa_one_repeat":bool(re.search(r"GDPval-AA v2\.1.{0,800}?220\s+tasks.{0,300}?\b1\b",aa,re.I)),
  "aa_pairwise_elo":"Pairwise comparison (Elo)" in aa,
  "openai_full_1320":("1,320" in op or "1320" in op),
  "openai_gold_220":bool(re.search(r"220.{0,80}(gold|open)",op,re.I) or re.search(r"(gold|open).{0,80}220",op,re.I)),
  "openai_44_occupations":"44 occupations" in op,
  "stirrup_public_source_identity":'name = "stirrup"' in st.lower() or "stirrup" in st.lower(),
}
missing=[k for k,v in facts.items() if not v]
out={
 "schema":"PROJECT_BRAIN_GDPVAL_AA_V21_PUBLIC_ROUTE_BOUNDARY_V1",
 "status":"PASS__EXACT_PUBLIC_220_TASK_POPULATION_AND_PUBLIC_STIRRUP_SUBSTRATE_BOUND__OFFICIAL_PAIRWISE_ELO_REPRODUCTION_REMAINS_OPEN__ZERO_CREDIT" if not missing else "FAIL_CLOSED__SOURCE_FACT_MISSING",
 "pass":not missing,
 "facts":facts,
 "missing":missing,
 "sources":{
   "artificial_analysis_methodology":AA_URL,
   "openai_gdpval":OPENAI_URL,
   "stirrup_commit":"247f24d56b2108235880ed2a2baea5d35b5a67ee",
 },
 "derived":{
   "official_gdpval_aa_v21_task_count":220 if not missing else None,
   "public_openai_gold_task_count":220 if not missing else None,
   "population_identity_candidate":"EXACT_SAME_220_TASK_COUNT_AND_UPSTREAM_GOLD_POPULATION__AA_METHOD_NAMES_220_TASKS__OPENAI_NAMES_220_OPEN_GOLD" if not missing else None,
   "stirrup_framework_public":bool(facts["stirrup_public_source_identity"]),
   "pairwise_elo_still_requires_aa_judge_panel_and_frozen_scaling":True,
 },
 "hard_nonclaims":[
   "NO_TASK_PROMPTS_REFERENCE_FILES_HUMAN_DELIVERABLES_OR_MODEL_DELIVERABLES_READ",
   "NO_BRAIN_GDPVAL_SCORE",
   "NO_PAIRWISE_ELO_REPRODUCTION_CLAIM",
   "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
 ],
 "new_reality_units_consumed":0,
 "terminal_cases_consumed":0,
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
