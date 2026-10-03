#!/usr/bin/env python3
import io, json, re, urllib.request
from pypdf import PdfReader

HF_META="https://huggingface.co/api/datasets/cais/hle-diamond"
PDF="https://www-cdn.anthropic.com/fc1b44717c85dc068bc6ba5024219938094694bd/Claude%20Opus%205.5%20System%20Card.pdf"

def get(url,timeout=90):
    req=urllib.request.Request(url,headers={"User-Agent":"project-brain-public-verifier/1.0"})
    with urllib.request.urlopen(req,timeout=timeout) as resp:
        assert resp.status==200,(url,resp.status)
        return resp.read()

meta=json.loads(get(HF_META))
assert meta.get("id")=="cais/hle-diamond",meta.get("id")
assert meta.get("gated")=="auto",meta.get("gated")

pdf=get(PDF,120)
assert pdf.startswith(b"%PDF"),"PRIMARY_SOURCE_NOT_PDF"
reader=PdfReader(io.BytesIO(pdf))
assert len(reader.pages)>=220,len(reader.pages)
text="\n".join((p.extract_text() or "") for p in reader.pages)
text=re.sub(r"\s+"," ",text).lower()

needles=[
  "claude opus 4.6 served as the model grader",
  "web search",
  "web fetch",
  "programmatic tool calling",
  "code execution",
  "capped at 1m",
  "context compaction was not used"
]
missing=[x for x in needles if x not in text]
assert not missing,("missing_primary_pdf_facts",missing)

low_raw=raw_text.lower()\nstart=low_raw.find("blocklist used for humanity")\nassert start>=0,"HLE_BLOCKLIST_SECTION_MISSING"\nblocklist_excerpt=raw_text[start:start+9000]\nprint("HLE_BLOCKLIST_EXCERPT_BEGIN")\nprint(blocklist_excerpt)\nprint("HLE_BLOCKLIST_EXCERPT_END")\n\nprint(json.dumps({
  "schema":"PROJECT_BRAIN_HLE_OPUS55_ROUTE_TRUTH_PUBLIC_RUNNER_RESULT_V1",
  "status":"PASS__PRIMARY_ANTHROPIC_PDF__HF_AUTO_GATE_CONFIRMED__OPUS55_GRADER_CLAUDE_OPUS_4_6__TOOLS_AND_1M_CAP_BOUND__ZERO_CASES",
  "anthropic_pdf_pages":len(reader.pages),
  "huggingface_gated":meta.get("gated"),
  "grader":"Claude Opus 4.6",
  "terminal_cases_consumed":0,
  "new_reality_units_consumed":0,
  "incremental_spend_usd":0,
  "acceptance_credit_delta":0
},sort_keys=True))
