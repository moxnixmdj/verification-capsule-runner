#!/usr/bin/env python3
from __future__ import annotations
import html, json, re, urllib.request

AA_URL="https://artificialanalysis.ai/methodology/intelligence-benchmarking"
HF_REV="69763877ec58e1958758b32153475185c5be469e"
HF_README=f"https://huggingface.co/datasets/openai/gdpval/raw/{HF_REV}/README.md"
STIRRUP_COMMIT="247f24d56b2108235880ed2a2baea5d35b5a67ee"
STIRRUP_RAW=f"https://raw.githubusercontent.com/ArtificialAnalysis/Stirrup/{STIRRUP_COMMIT}/pyproject.toml"

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
hf=get(HF_README)
st=get(STIRRUP_RAW)

facts={
  "aa_names_gdpval_v21":"GDPval-AA v2.1" in aa,
  "aa_220_tasks":bool(re.search(r"GDPval-AA v2\.1.{0,500}?220\s+tasks",aa,re.I)),
  "aa_one_repeat":bool(re.search(r"GDPval-AA v2\.1.{0,800}?220\s+tasks.{0,300}?\b1\b",aa,re.I)),
  "aa_pairwise_elo":"Pairwise comparison (Elo)" in aa,
  "aa_public_gold_openai_dataset":bool(re.search(r"public\s+gold\s+OpenAI\s+GDPval\s+dataset",aa,re.I)),
  "hf_gdpval_identity":bool(re.search(r"GDPval:\s*Evaluating\s+AI\s+Model\s+Performance",hf,re.I)),
  "hf_220_tasks":bool(re.search(r"220\s+real-world\s+knowledge\s+tasks",hf,re.I)),
  "hf_44_occupations":bool(re.search(r"44\s+occupations",hf,re.I)),
  "hf_num_examples_220":bool(re.search(r"num_examples:\s*220",hf,re.I)),
  "stirrup_public_source_identity":'name = "stirrup"' in st.lower() or "stirrup" in st.lower(),
}
missing=[k for k,v in facts.items() if not v]
out={
 "schema":"PROJECT_BRAIN_GDPVAL_AA_V21_PUBLIC_ROUTE_BOUNDARY_V1",
 "status":"PASS__AA_V21_BINDS_PUBLIC_OPENAI_GOLD_220_TASK_POPULATION_AND_PUBLIC_STIRRUP_SUBSTRATE__PAIRWISE_ELO_REPRODUCTION_REMAINS_OPEN__ZERO_CREDIT" if not missing else "FAIL_CLOSED__SOURCE_FACT_MISSING",
 "pass":not missing,
 "facts":facts,
 "missing":missing,
 "sources":{
   "artificial_analysis_methodology":AA_URL,
   "openai_gdpval_huggingface_repository":"openai/gdpval",
   "openai_gdpval_huggingface_readme_revision":HF_REV,
   "stirrup_commit":STIRRUP_COMMIT,
 },
 "derived":{
   "official_gdpval_aa_v21_task_count":220 if not missing else None,
   "public_openai_gold_task_count":220 if not missing else None,
   "population_identity_candidate":"AA_EXPLICITLY_BASES_EVALUATION_ON_PUBLIC_GOLD_OPENAI_GDPVAL_DATASET__PINNED_OPENAI_DATASET_CARD_HAS_220_TASKS_44_OCCUPATIONS" if not missing else None,
   "stirrup_framework_public":bool(facts["stirrup_public_source_identity"]),
   "pairwise_elo_still_requires_aa_judge_panel_comparison_graph_crowd_bt_fit_and_frozen_anchor":True,
 },
 "hard_nonclaims":[
   "NO_TASK_PROMPTS_REFERENCE_FILES_RUBRICS_HUMAN_DELIVERABLES_OR_MODEL_DELIVERABLES_READ",
   "NO_BRAIN_GDPVAL_SCORE",
   "NO_PAIRWISE_ELO_REPRODUCTION_CLAIM",
   "NO_CLAIM_THAT_PUBLIC_TASK_POPULATION_ALONE_REPRODUCES_ARTIFICIAL_ANALYSIS_ELO",
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
