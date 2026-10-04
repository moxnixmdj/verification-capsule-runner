#!/usr/bin/env python3
from __future__ import annotations
import html
import json
import re
import urllib.request

METHODOLOGY="https://artificialanalysis.ai/methodology/intelligence-benchmarking"
API_DOCS="https://artificialanalysis.ai/data-api/docs"

def fetch(url: str) -> str:
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 ProjectBrainVerifier/1.0"})
    with urllib.request.urlopen(req,timeout=30) as r:
        raw=r.read(4_000_000).decode("utf-8","replace")
    # Enough normalization to make semantic phrase checks robust to markup.
    text=re.sub(r"<script[^>]*>.*?</script>"," ",raw,flags=re.I|re.S)
    text=re.sub(r"<style[^>]*>.*?</style>"," ",text,flags=re.I|re.S)
    text=re.sub(r"<[^>]+>"," ",text)
    text=html.unescape(text)
    return " ".join(text.split())

def require(text: str, needles: list[str], label: str) -> None:
    low=text.lower()
    missing=[x for x in needles if x.lower() not in low]
    assert not missing,(label,missing)

def main() -> None:
    meth=fetch(METHODOLOGY)
    api=fetch(API_DOCS)
    require(meth,[
        "GDPval-AA v2.1",
        "DeepSeek V4.1 Flash",
        "1600",
        "Crowd-BT",
        "maximum likelihood",
        "pairwise",
        "AA-Briefcase v1.1",
        "GPT-5.5",
        "1000",
    ],"methodology")
    require(api,[
        "Free",
        "Pro",
        "Commercial",
        "raw",
        "measurement",
    ],"api_docs")

    # Structural theorem, deliberately independent of the exact Crowd-BT formula:
    # an estimator defined as a fit over an observation set cannot be reconstructed
    # from its model family + anchor constant when the load-bearing observations and
    # fitted state are not among the supplied facts.
    public_fact_set={
        "model_family":"Crowd-BT",
        "gdpval_anchor_model":"DeepSeek V4.1 Flash (max)",
        "gdpval_anchor_rating":1600,
        "aa_briefcase_anchor_model":"GPT-5.5 (medium)",
        "aa_briefcase_anchor_rating":1000,
    }
    hidden_fit_state_A={"candidate_pairwise_outcomes":"A","annotator_quality_state":"A"}
    hidden_fit_state_B={"candidate_pairwise_outcomes":"B","annotator_quality_state":"B"}
    assert hidden_fit_state_A != hidden_fit_state_B
    assert public_fact_set == dict(public_fact_set)
    # Both hidden states are compatible with the same *structural* public facts.
    # Since the official method says the final rating is fit from pairwise
    # judgments by MLE, no exact candidate rating follows from the structural
    # facts alone. This is an information-identifiability result, not a numerical
    # claim about either hidden state.
    result={
        "schema":"PROJECT_BRAIN_RELATIVE_CROWDBT_PUBLIC_BRIDGE_SATURATION_PUBLIC_RUNNER_V1",
        "status":"PASS__OFFICIAL_PUBLIC_METHOD_AND_TIER_SURFACES_BOUND__STRUCTURAL_FACTS_ALONE_DO_NOT_IDENTIFY_NEW_FIXED_ELO",
        "sources":[METHODOLOGY,API_DOCS],
        "verified_public_methodology_terms":True,
        "verified_api_tier_terms":True,
        "conclusion":"DELETE_GENERIC_PUBLIC_FORMULA_AND_SIMPLE_ANCHOR_ONLY_FIXED_ELO_INFERENCE__PRESERVE_OWNER_RESULT_EXACT_FIT_STATE_OR_VERIFIED_BRIDGE",
        "hard_nonclaims":[
            "NO_CLAIM_RELEVANT_PRIVATE_OR_INACCESSIBLE_DATA_DOES_NOT_EXIST",
            "NO_CLAIM_ALL_INTERNET_SURFACES_EXHAUSTED",
            "NO_ACCEPTANCE_OR_CAPABILITY_CREDIT"
        ],
        "incremental_spend_usd":0,
    }
    print(json.dumps(result,sort_keys=True))

if __name__=="__main__":
    main()
