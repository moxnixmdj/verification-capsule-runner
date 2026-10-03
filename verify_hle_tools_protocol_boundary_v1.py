#!/usr/bin/env python3
"""Independent zero-reality HLE-with-tools protocol boundary verifier.

Reads only public source/configuration files from the exact official HLE commit.
No benchmark question, image, answer row, model response, or judge call is consumed.
"""
from __future__ import annotations
import hashlib, json, urllib.request

REPO="centerforaisafety/hle"
COMMIT="22ed3074b1e7b134bcbc09028d0ba320839b0655"
FILES={
 "docs/evaluation-with-tools.md":"78ad17375fe3ec2239615cf05f577d6196af2992",
 "docs/requirements-tools.txt":"d700cda6162e2d4f5d86dbf4865487721d979050",
 "docs/blocklist.json":"8ca485255e99736e2615d73a25736b30055c5c5b",
 "hle_eval/run_judge_results.py":"4caca7c5e6eaa9c64ec33e5f1bcc93312e6c5b31",
 "README.md":"a948c9512541fff702aaf5e0c8bc371fded3689c",
}

def get(path:str)->bytes:
    url=f"https://raw.githubusercontent.com/{REPO}/{COMMIT}/{path}"
    req=urllib.request.Request(url,headers={"User-Agent":"project-brain-hle-protocol-verifier-v1"})
    with urllib.request.urlopen(req,timeout=30) as r:
        return r.read()

def blob_sha(b:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def main()->int:
    raw={}
    for p,h in FILES.items():
        b=get(p)
        got=blob_sha(b)
        if got!=h:
            raise AssertionError((p,h,got))
        raw[p]=b.decode("utf-8")

    tools=raw["docs/evaluation-with-tools.md"]
    judge=raw["hle_eval/run_judge_results.py"]
    readme=raw["README.md"]

    facts={
      "official_tools_document_names_hle_diamond": "# Evaluating HLE-Diamond with tools" in tools,
      "opus55_harness_exact": "| Claude Opus 5.5 | Claude Code | 2.1.280 |" in tools,
      "python_version_exact": "Python 3.11.16" in tools,
      "no_direct_internet": "No direct internet access" in tools,
      "only_web_search_and_web_fetch": "Expose only these two web tools:" in tools and "web_search(query)" in tools and "web_fetch(url)" in tools,
      "web_search_cap_20": "at most 20 results per call" in tools,
      "web_fetch_cap_60000": "capped at 60,000 characters" in tools,
      "blocklist_required": "docs/blocklist.json" in tools,
      "official_judge_gold_field_bound": 'correct_answer = question["answer"]' in judge,
      "official_judge_exact_match_semantics_present": "matches the [correct_answer] given above" in judge,
      "official_judge_default_o3_mini": 'default="o3-mini-2025-01-31"' in judge,
      "public_base_dataset_named": 'load_dataset("cais/hle", split="test")' in readme,
    }
    missing=[k for k,v in facts.items() if not v]
    if missing:
        out={"status":"FAIL_CLOSED__OFFICIAL_PROTOCOL_FACT_MISSING","missing":missing,"facts":facts}
        print(json.dumps(out,indent=2,sort_keys=True))
        return 1

    out={
      "schema":"PROJECT_BRAIN_HLE_TOOLS_PROTOCOL_BOUNDARY_V1",
      "status":"PASS__OFFICIAL_HLE_TOOLS_PROTOCOL_AND_OPUS55_HARNESS_BOUND__JUDGE_AND_EXACT_DIAMOND_POPULATION_REMAIN_OPEN__ZERO_CREDIT",
      "official_repository":REPO,
      "official_commit":COMMIT,
      "exact_file_blobs":FILES,
      "verified":{
        "hle_diamond_tools_protocol_named":True,
        "opus55_provider_harness":"Claude Code 2.1.280",
        "python_version":"3.11.16",
        "allowed_external_tools":["web_search","web_fetch"],
        "web_search_max_results":20,
        "web_fetch_max_chars":60000,
        "blocklist_required":True,
        "judge_gold_source":"question.answer",
        "judge_default_model":"o3-mini-2025-01-31",
        "judge_contract_accepts_matching_extracted_final_answer":True,
        "base_public_dataset_reference":"cais/hle",
      },
      "remaining_exact_residuals":[
        "BIND_EXACT_HLE_DIAMOND_POPULATION_TO_FROZEN_67_7_TARGET",
        "PROVE_OR_OBTAIN_HARD_ZERO_COST_COMPARABLE_JUDGE_ROUTE__OR_SCOPE_COMPLETE_STRONGER_SCORER_RELATION",
        "BIND_BRAIN_TOOL_ADAPTER_TO_THE_FROZEN_SEARCH_FETCH_SANDBOX_AND_BLOCKLIST_SEMANTICS"
      ],
      "hard_nonclaims":[
        "NO_HLE_BENCHMARK_CASE_READ",
        "NO_HLE_DIAMOND_POPULATION_EQUIVALENCE_CLAIM",
        "NO_DETERMINISTIC_EXACT_MATCH_SCORER_EQUIVALENCE_CLAIM",
        "NO_BRAIN_SCORE_CLAIM",
        "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT"
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
      "fresh_reality_authority":False
    }
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
