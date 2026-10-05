#!/usr/bin/env python3
import io, json, re, urllib.request
from pypdf import PdfReader

PDF="https://www-cdn.anthropic.com/fc1b44717c85dc068bc6ba5024219938094694bd/Claude%20Opus%205.5%20System%20Card.pdf"

def get(url, timeout=120):
    req=urllib.request.Request(url, headers={"User-Agent":"project-brain-public-verifier/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        assert resp.status == 200, (url, resp.status)
        return resp.read()

pdf=get(PDF)
assert pdf.startswith(b"%PDF"), "PRIMARY_SOURCE_NOT_PDF"
reader=PdfReader(io.BytesIO(pdf))
assert len(reader.pages) >= 220, len(reader.pages)
raw="\n".join((p.extract_text() or "") for p in reader.pages)
text=re.sub(r"\s+", " ", raw).lower()

start_candidates=[
    "8.11.1 humanity’s last exam",
    "8.11.1 humanity's last exam",
    "8.11.1 humanity s last exam",
]
start=-1
for needle in start_candidates:
    start=text.find(needle)
    if start >= 0:
        break
assert start >= 0, "HLE_SECTION_START_NOT_FOUND"
end=text.find("8.11.2", start)
assert end > start, "HLE_SECTION_END_NOT_FOUND"
section=text[start:end]

required=[
    "multimodal benchmark comprising 2,500 questions",
    "we tested claude opus 5.5 in two configurations",
    "reasoning-only without tools",
    "web search",
    "web fetch",
    "programmatic tool calling",
    "code execution",
    "claude opus 4.6 served as the model grader",
]
missing=[x for x in required if x not in section]
assert not missing, ("missing_hle_section_facts", missing)

# The HLE section names one benchmark object, defines it as multimodal/2500,
# then describes two tested configurations on that object. We do not infer
# per-question execution logs or image-asset success from this protocol fact.
print(json.dumps({
  "schema":"PROJECT_BRAIN_HLE_OPUS55_MULTIMODAL_CONFIGURATION_IDENTITY_PUBLIC_RUNNER_RESULT_V1",
  "status":"PASS__PRIMARY_ANTHROPIC_PDF_HLE_SECTION_DEFINES_MULTIMODAL_2500_BENCHMARK_AND_APPLIES_BOTH_TEST_CONFIGURATIONS_TO_HLE__ZERO_CASES",
  "anthropic_pdf_pages":len(reader.pages),
  "section_start_found":True,
  "section_end_found":True,
  "hle_defined_multimodal_2500":True,
  "opus55_two_configurations_on_hle":True,
  "with_tools_named":True,
  "grader":"Claude Opus 4.6",
  "terminal_cases_consumed":0,
  "new_reality_units_consumed":0,
  "incremental_spend_usd":0
}, sort_keys=True))

# verifier-trigger-v1

# pr-verifier-trigger-v1

# pr-synchronize-trigger-v2
