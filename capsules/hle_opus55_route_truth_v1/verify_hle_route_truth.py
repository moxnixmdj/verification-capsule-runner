#!/usr/bin/env python3
import json, re, urllib.request

HF_META="https://huggingface.co/api/datasets/cais/hle-diamond"
ANTHROPIC="https://www.anthropic.com/claude-opus-5-5-system-card"

def get(url):
    req=urllib.request.Request(url,headers={"User-Agent":"project-brain-public-verifier/1.0"})
    with urllib.request.urlopen(req,timeout=45) as resp:
        assert resp.status==200,(url,resp.status)
        return resp.read()

meta=json.loads(get(HF_META))
assert meta.get("id")=="cais/hle-diamond",meta.get("id")
assert meta.get("gated")=="auto",meta.get("gated")

html=get(ANTHROPIC).decode("utf-8","replace")
text=re.sub(r"<[^>]+>"," ",html)
text=re.sub(r"\s+"," ",text)

needles=[
  "Claude Opus 4.6 served as the model grader",
  "web search",
  "web fetch",
  "programmatic tool calling",
  "code execution",
  "capped at 1M",
  "Context compaction was not used"
]
missing=[x for x in needles if x.lower() not in text.lower()]
assert not missing,("missing_primary_source_facts",missing)

print(json.dumps({
  "schema":"PROJECT_BRAIN_HLE_OPUS55_ROUTE_TRUTH_PUBLIC_RUNNER_RESULT_V1",
  "status":"PASS__HF_AUTO_GATE_CONFIRMED__OPUS55_GRADER_CLAUDE_OPUS_4_6__TOOLS_AND_1M_CAP_BOUND__ZERO_CASES",
  "huggingface_gated":meta.get("gated"),
  "grader":"Claude Opus 4.6",
  "terminal_cases_consumed":0,
  "new_reality_units_consumed":0,
  "incremental_spend_usd":0,
  "acceptance_credit_delta":0
},sort_keys=True))
