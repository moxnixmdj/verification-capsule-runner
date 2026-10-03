#!/usr/bin/env python3
import hashlib, io, json, re, urllib.request
from pypdf import PdfReader

URL="https://www-cdn.anthropic.com/fc1b44717c85dc068bc6ba5024219938094694bd/Claude%20Opus%205.5%20System%20Card.pdf"

req=urllib.request.Request(URL,headers={"User-Agent":"project-brain-public-verifier/2.0"})
with urllib.request.urlopen(req,timeout=90) as resp:
    assert resp.status==200,resp.status
    raw=resp.read()

sha=hashlib.sha256(raw).hexdigest()
assert len(raw)>10_000_000, len(raw)
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

# The capability table must contain the vendor-reported with-tools target.
assert "67.7" in full, "HLE 67.7 target absent from system-card PDF"

# Bind the local HLE section rather than relying only on global string presence.
idx=low.find("humanity’s last exam")
assert idx>=0
window=low[idx:idx+12000]
for x in ["web search","web fetch","programmatic tool calling","code execution",
          "thinking was set to auto","capped at 1m","context compaction was not used",
          "claude opus 4.6 served as the model grader"]:
    assert x in window,("missing_in_hle_section",x)

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
  "vendor_target_percent":67.7,
  "terminal_cases_consumed":0,
  "new_reality_units_consumed":0,
  "incremental_spend_usd":0,
  "acceptance_credit_delta":0
},sort_keys=True))
