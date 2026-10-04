#!/usr/bin/env python3
import hashlib,io,json,re,urllib.request
from pathlib import Path
from pypdf import PdfReader
R=Path(__file__).resolve().parent
cand=json.loads((R/"candidate.json").read_text())
manifest=json.loads((R/"osworld-v2.1.json").read_text())
def blob(path):
 b=path.read_bytes(); return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
assert blob(R/"candidate.json")=="f4bc47440829387db14e37c900a269d11f77fdc1"
assert blob(R/"osworld-v2.1.json")=="6d37c6f4c6c4f6daa5077d4e4c828f68360b7e36"
p=cand["anthopic_primary"]
req=urllib.request.Request(p["system_card_pdf_url"],headers={"User-Agent":"ProjectBrainVerifier/1.0"})
pdf=urllib.request.urlopen(req,timeout=60).read()
assert hashlib.sha256(pdf).hexdigest()==p["expected_system_card_pdf_sha256"]
text="\n".join((page.extract_text() or "") for page in PdfReader(io.BytesIO(pdf)).pages)
norm=" ".join(text.split())
need=[
 "OSWorld 2.0","108 long-horizon computer use tasks","weighted checkpoints",
 "partial score","strict pass rate","five independent runs","1080p resolution",
 "maximum of 500 action steps per task","maximum reasoning effort","Claude Opus 4.8",
 "September 10, 2026","retains every screenshot","100k tokens"
]
for x in need: assert x.lower() in norm.lower(),x
assert "81.8" in norm and "48.7" in norm
launch=urllib.request.urlopen(urllib.request.Request(p["launch_url"],headers={"User-Agent":"ProjectBrainVerifier/1.0"}),timeout=30).read().decode("utf-8","replace")
clean=" ".join(re.sub(r"<[^>]+>"," ",launch).split())
assert "OSWorld 2.1" in clean and "81.8" in clean and "partial" in clean.lower()
assert manifest["release"]=="osworld-v2.1"
assert manifest["task_hash_manifest"]["task_count"]==108
assert manifest["tasks"]["commit"]==cand["upstream_release_binding"]["task_revision"]
assert manifest["assets"]["commit"]==cand["upstream_release_binding"]["asset_revision"]
assert manifest["website_code"]["commit"]==cand["upstream_release_binding"]["website_revision"]
assert "NO_CLAIM_SYSTEM_CARD_LABEL_OSWORLD_2_0_EQUALS_RELEASE_TAG_OSWORLD_V2_1" in cand["hard_nonclaims"]
assert cand["acceptance_credit_delta"] if "acceptance_credit_delta" in cand else cand["accounting"]["acceptance_credit_delta"]==0
assert cand["fresh_reality_authority"] is False
print(json.dumps({
 "pass":True,
 "status":"PASS__EXACT_ANTHROPIC_PDF_SHA__OSWORLD_METHOD_108_TASKS_5_RUNS_1080P_500_STEPS_GRADER_CONTEXT__LAUNCH_81_8_PARTIAL__V21_MANIFEST_BOUND__RELEASE_IDENTITY_RELATION_STILL_OPEN__ZERO_CREDIT"
},sort_keys=True))
