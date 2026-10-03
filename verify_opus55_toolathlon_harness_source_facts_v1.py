from __future__ import annotations
import hashlib, io, json, re, urllib.request
from pypdf import PdfReader

URL="https://www-cdn.anthropic.com/fc1b44717c85dc068bc6ba5024219938094694bd/Claude%20Opus%205.5%20System%20Card.pdf"
EXPECTED_SHA="7311c9c6bbb16d012f1c12c7418b05949fcf7ae3e30d2c40f22050074b2a7378"

def norm(s:str)->str:
    return re.sub(r"\s+"," ",s).strip()

req=urllib.request.Request(URL,headers={"User-Agent":"project-brain-toolathlon-harness-verifier/1"})
with urllib.request.urlopen(req,timeout=120) as r:
    data=r.read()
assert data.startswith(b"%PDF")
assert hashlib.sha256(data).hexdigest()==EXPECTED_SHA
reader=PdfReader(io.BytesIO(data))
pages=[]
for i,p in enumerate(reader.pages,1):
    t=norm(p.extract_text() or "")
    if "Toolathlon" in t:
        pages.append((i,t))
assert pages
section=" ".join(t for _,t in pages)
low=section.lower()
checks={
    "toolathlon_section":"toolathlon" in low,
    "opus_score":"77.8" in low,
    "task_count":"108 tasks" in low,
    "three_trials":"three trials" in low,
    "internal_harness":"internal harness" in low,
    "setup_patches":"setup patches" in low,
    "financial_feeds":("financial" in low and "data feed" in low),
    "container_images":"container image" in low,
    "null_attempts":"null attempt" in low,
    "reference_scores":("71.6" in low and "76.2" in low),
}
assert all(checks.values()), {k:v for k,v in checks.items() if not v}

mirrors = ("mirror" in low and "task definitions" in low and "prompts" in low and "checker" in low)
patches = checks["setup_patches"]
internal = checks["internal_harness"]
nulls = checks["null_attempts"]
exact_equality_claim = (
    "same exact harness" in section.lower()
    or "identical harness" in section.lower()
)

verdict={
  "schema":"PROJECT_BRAIN_OPUS55_TOOLATHLON_HARNESS_SOURCE_FACTS_V1",
  "source_url":URL,
  "source_sha256":EXPECTED_SHA,
  "toolathlon_pages":[i for i,_ in pages],
  "facts":{
    "opus55_pass_at_1_percent":77.8,
    "task_count":108,
    "trials":3,
    "source_calls_results_internal_harness":internal,
    "source_says_harness_mirrors_task_prompts_checkers":mirrors,
    "source_discloses_environment_specific_setup_patches":patches,
    "source_discloses_pinned_financial_feeds_and_container_images":checks["financial_feeds"] and checks["container_images"],
    "source_discloses_public_vs_internal_score_shift_for_reference_models":(("three points higher" in low or "3 points higher" in low) and nulls),
    "source_claims_exact_harness_identity":exact_equality_claim,
    "normalized_source_checks":checks
  },
  "deduction_boundary":{
    "first_party_source_proves_exact_internal_vs_public_harness_byte_identity":False,
    "first_party_source_supports_treating_77_8_as_same_harness_public_service_score_without_additional_proof":False,
    "reason":"SOURCE_EXPLICITLY_LABELS_RESULTS_INTERNAL_HARNESS_AND_DISCLOSES_ENVIRONMENT_SPECIFIC_SETUP_PATCHES_AND_OBSERVED_PUBLIC_INTERNAL_SCORE_SHIFT"
  },
  "terminal_results_observed":0,
  "capability_credit_delta":0,
  "family_credit_delta":0,
  "incremental_spend_usd":0
}
open("OPUS55_TOOLATHLON_HARNESS_SOURCE_FACTS_V1.json","w",encoding="utf-8").write(json.dumps(verdict,indent=2,sort_keys=True)+"\n")
print(json.dumps(verdict,sort_keys=True))
