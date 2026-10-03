from __future__ import annotations
import json, os, re
from pathlib import Path
import fitz

ROOT=Path(__file__).resolve().parent
PDF=Path(os.environ["OPUS55_PDF"])
PROJ=Path(os.environ["PROJECTION_DIR"])
cand=json.loads((ROOT/"candidate.json").read_text())

def req(x,msg):
    if not x: raise AssertionError(msg)

req(cand["status"].startswith("CANDIDATE__"),"candidate status")
req(cand["first_party_source"]["sha256"]=="7311c9c6bbb16d012f1c12c7418b05949fcf7ae3e30d2c40f22050074b2a7378","source hash drift")
req(cand["matched_reference"]["pass_at_1_percent"]==77.8,"bar drift")
req(cand["matched_reference"]["task_count"]==108,"task count drift")
req(cand["matched_reference"]["trials"]==3,"trial count drift")
req(cand["matched_reference"]["total_trials"]==324,"total trials drift")
req(cand["capability_credit_delta"]==0 and cand["family_credit_delta"]==0,"zero credit")
req(cand["execution_authority"] is False and cand["promotion_authority"] is False,"authority leak")

doc=fitz.open(PDF)
req(doc.page_count==230,f"page count {doc.page_count}")
text="\n".join(page.get_text("text") for page in doc)
norm=re.sub(r"\s+"," ",text)
for phrase in [
    "Claude Opus 5.5 achieved 77.8% Pass@1",
    "Of 324 trials",
    "all 108 tasks",
]:
    req(phrase in norm,f"first-party PDF missing: {phrase}")
req("three trials" in norm or "3 trials" in norm,"first-party PDF missing three-trial fact")

meta=(PROJ/"cards/anthropic/claude-opus-5-5/meta.yaml").read_text()
l2=json.loads((PROJ/"cards/anthropic/claude-opus-5-5/l2-links.json").read_text())
inv=json.loads((PROJ/"cards/anthropic/claude-opus-5-5/source-inventory.json").read_text())
sec=(PROJ/"cards/anthropic/claude-opus-5-5/sections/08b-capabilities-2.md").read_text()
req("release_date: 2026-09-22" in meta,"projection release drift")
req(l2["source_sha256"]==cand["first_party_source"]["sha256"],"l2 source hash mismatch")
req(inv["source_sha256"]==cand["first_party_source"]["sha256"],"inventory source hash mismatch")
for phrase in [
    "Claude Opus 5.5 achieved 77.8% Pass@1",
    "Of 324 trials",
    "all 108 tasks",
]:
    req(phrase in sec,f"projection section missing: {phrase}")

closes=set(cand["closes_if_independently_verified"])
req("BIND_OPUS_5_5_77_8_PASS_AT_1_SOURCE_DURABLY_AND_INDEPENDENTLY" in closes,"missing original precondition")
req("OPUS55_TOOLATHLON_77_8_DURABLE_FIRST_PARTY_BYTE_BINDING" in closes,"missing reduced-cut atom")
req("NO_BRAIN_TOOLATHLON_RESULT" in cand["hard_nonclaims"],"result nonclaim missing")
req("NO_TOOL_DISCOVERY_ACCEPTANCE_CREDIT" in cand["hard_nonclaims"],"acceptance nonclaim missing")

print(json.dumps({
  "pass":True,
  "first_party_pdf_sha256":cand["first_party_source"]["sha256"],
  "first_party_pdf_pages":doc.page_count,
  "opus55_toolathlon_pass_at_1_percent":77.8,
  "task_count":108,
  "trials":3,
  "total_trials":324,
  "durable_source_binding_verified":True,
  "acceptance_credit_delta":0
},sort_keys=True))
