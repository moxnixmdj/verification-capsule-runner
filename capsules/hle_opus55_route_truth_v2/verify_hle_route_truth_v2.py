#!/usr/bin/env python3
import hashlib, io, json, re, urllib.request
from pypdf import PdfReader

URL="https://www-cdn.anthropic.com/fc1b44717c85dc068bc6ba5024219938094694bd/Claude%20Opus%205.5%20System%20Card.pdf"

req=urllib.request.Request(URL,headers={"User-Agent":"project-brain-public-verifier/2.0"})
with urllib.request.urlopen(req,timeout=90) as resp:
    assert resp.status==200,resp.status
    raw=resp.read()

sha=hashlib.sha256(raw).hexdigest()
assert sha=="7311c9c6bbb16d012f1c12c7418b05949fcf7ae3e30d2c40f22050074b2a7378",sha
assert len(raw)==17795106,len(raw)
reader=PdfReader(io.BytesIO(raw))
texts=[]
for page in reader.pages:
    try:
        texts.append(page.extract_text() or "")
    except Exception:
        texts.append("")
full=" ".join(" ".join(texts).split())
low=full.lower()

facts=[
    "humanity’s last exam",
    "web search",
    "web fetch",
    "programmatic tool calling",
    "code execution",
    "thinking was set to auto",
    "total tokens used across contexts was capped at 1m",
    "context compaction was not used",
    "claude opus 4.6 served as the model grader",
    "blocklist sources known to discuss hle",
]
missing=[x for x in facts if x.lower() not in low]
assert not missing,("missing_primary_source_facts",missing)

# Bind population identity and vendor-reported with-tools target.
# Anthropic's frozen HLE description is the full 2,500-question benchmark, not
# the separate 1,000-question HLE-Diamond subset.
assert re.search(r"2[, ]500\s+questions",full,re.I), "HLE 2500-question population absent"
assert "67.7" in full, "HLE 67.7 target absent from system-card PDF"

pop_hits=[m.start() for m in re.finditer(r"2[, ]500\s+questions",full,re.I)]
hle_hits=[m.start() for m in re.finditer(r"humanity.s last exam",full,re.I)]
assert pop_hits and hle_hits
assert min(abs(a-b) for a in pop_hits for b in hle_hits) < 12000, "2500 population not locally bound to HLE"

# Bind the local HLE evaluation paragraph around its distinctive grader sentence.
# The PDF contains earlier HLE mentions (e.g. table/overview), so anchoring to the
# first HLE occurrence is not a valid locality test.
anchor="claude opus 4.6 served as the model grader"
aidx=low.find(anchor)
assert aidx>=0
window=low[max(0,aidx-20000):aidx+12000]
for x in ["humanity’s last exam","web search","web fetch","programmatic tool calling",
          "code execution","thinking was set to auto","capped at 1m",
          "context compaction was not used",anchor]:
    assert x in window,("missing_near_hle_grader_paragraph",x)

print(json.dumps({
  "schema":"PROJECT_BRAIN_HLE_OPUS55_ROUTE_TRUTH_PUBLIC_RUNNER_RESULT_V2",
  "status":"PASS__PRIMARY_ANTHROPIC_PDF__OPUS55_HLE_PROTOCOL_BOUND__ZERO_CASES",
  "source_url":URL,
  "source_sha256":sha,
  "source_bytes":len(raw),
  "page_count":len(reader.pages),
  "grader":"Claude Opus 4.6",
  "tools":["web_search","web_fetch","programmatic_tool_calling","code_execution"],
  "thinking":"auto",
  "total_context_token_cap":1000000,
  "context_compaction":False,
  "population_question_count":2500,
  "population_identity":"FULL_HLE_NOT_HLE_DIAMOND",
  "vendor_target_percent":67.7,
  "terminal_cases_consumed":0,
  "new_reality_units_consumed":0,
  "incremental_spend_usd":0,
  "acceptance_credit_delta":0
},sort_keys=True))
