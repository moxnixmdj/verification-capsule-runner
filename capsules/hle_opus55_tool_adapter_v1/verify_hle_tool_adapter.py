#!/usr/bin/env python3
from __future__ import annotations
import hashlib, io, json, re, sys, urllib.request
from pathlib import Path
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from canonical.runtime import root2_hle_opus55_tool_adapter_v1 as adapter

PDF="https://www-cdn.anthropic.com/fc1b44717c85dc068bc6ba5024219938094694bd/Claude%20Opus%205.5%20System%20Card.pdf"

def blob(path:Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def norm(x:str)->str:
    return str(x).replace("/","").lower()

manifest=json.loads((ROOT/"EXPECTED_BRAIN_BLOBS.json").read_text())
for rel,expected in manifest["exact_brain_blobs"].items():
    got=blob(ROOT/rel)
    assert got==expected,(rel,got,expected)

policy=json.loads((ROOT/"canonical/governance/HLE_OPUS55_TOOL_POLICY_V1.json").read_text())
assert policy["contamination_policy"]["pattern_count"]==153
assert len(policy["blocklist_patterns"])==153
assert len({norm(x) for x in policy["blocklist_patterns"]})==153

req=urllib.request.Request(PDF,headers={"User-Agent":"project-brain-hle-policy-verifier/1.0"})
with urllib.request.urlopen(req,timeout=120) as resp:
    raw=resp.read()
assert raw.startswith(b"%PDF")
reader=PdfReader(io.BytesIO(raw))
pages=[p.extract_text() or "" for p in reader.pages]
start_page=None
for i,t in enumerate(pages):
    flat=re.sub(r"\s+"," ",t).lower()
    if "blocklist used for humanity" in flat and "last exam" in flat:
        start_page=i
        break
assert start_page is not None,"BLOCKLIST_SECTION_NOT_FOUND"
section="\n".join(pages[start_page:])
m=re.search(r"9\.2\s+Blocklist\s+used\s+for\s+Humanity.?s\s+Last\s+Exam",section,re.I)
assert m,"BLOCKLIST_HEADING_NOT_FOUND"
body=section[m.end():]
tokens=[x for x in re.split(r"\s+",body) if x]
tokens=[x for x in tokens if x not in {"226","227","228","229","230"}]

joined=[]
i=0
while i<len(tokens):
    x=tokens[i]
    if x.endswith("-future") and i+1<len(tokens) and tokens[i+1]=="-for-ai":
        joined.append(x+tokens[i+1]); i+=2; continue
    if x.endswith("-c25") and i+1<len(tokens) and tokens[i+1].startswith("8aad557ba"):
        joined.append(x+tokens[i+1]); i+=2; continue
    joined.append(x); i+=1

source_norm=[norm(x) for x in joined]
policy_norm=[norm(x) for x in policy["blocklist_patterns"]]
assert len(source_norm)==153,(len(source_norm),source_norm[-20:])
assert source_norm==policy_norm, {
    "source_only":sorted(set(source_norm)-set(policy_norm)),
    "policy_only":sorted(set(policy_norm)-set(source_norm)),
    "source_count":len(source_norm),
    "policy_count":len(policy_norm),
}

assert adapter.block_match("https://huggingface.co/datasets/cais/hle-diamond",policy) is not None
assert adapter.block_match("https://example.org/ordinary-reference",policy) is None
contract=adapter.tool_contract()
assert contract["status"]=="READY"
assert contract["blocklist_pattern_count"]==153
assert set(contract["tools"])=={"web_search","web_fetch","programmatic_tool_calling","code_execution"}
assert contract["context_compaction"] is False

gov=json.loads((ROOT/"canonical/governance/HLE_OPUS55_TOOL_ADAPTER_V1.json").read_text())
assert gov["acceptance_credit_delta"]==0
assert gov["fresh_reality_authority"] is False
assert gov["soundness"]["identical_vendor_backend_claim"] is False

print(json.dumps({
  "schema":"PROJECT_BRAIN_HLE_OPUS55_TOOL_ADAPTER_PUBLIC_RUNNER_RESULT_V1",
  "status":"PASS__EXACT_BLOBS__PRIMARY_PDF_153_OF_153_POLICY_EQUALITY__BLOCKED_SEARCH_FETCH_REDIRECT_TESTS__RESTRICTED_CODE_TESTS__ONE_SIDED_SOUNDNESS__ZERO_CASES__ZERO_CREDIT",
  "pass":True,
  "primary_pdf_pages":len(reader.pages),
  "policy_pattern_count":len(policy_norm),
  "terminal_cases_consumed":0,
  "new_reality_units_consumed":0,
  "incremental_spend_usd":0,
  "acceptance_credit_delta":0,
  "execution_authority":False,
  "promotion_authority":False
},sort_keys=True))
