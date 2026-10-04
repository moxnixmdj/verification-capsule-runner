#!/usr/bin/env python3
import hashlib, html, json, re, urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parent
CAND=ROOT/"canonical/governance/GDPVAL_OPUS55_FIXED_BAR_PROVENANCE_RECONCILIATION_20261004_V1.json"
EXP=json.loads((ROOT/"EXPECTED.json").read_text())

def blob(path):
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def fetch(url):
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 ProjectBrainVerifier/1.0"})
    with urllib.request.urlopen(req,timeout=30) as r:
        raw=r.read().decode("utf-8","replace")
    text=re.sub(r"<script[\\s\\S]*?</script>"," ",raw,flags=re.I)
    text=re.sub(r"<style[\\s\\S]*?</style>"," ",text,flags=re.I)
    text=re.sub(r"<[^>]+>"," ",text)
    text=html.unescape(text)
    return " ".join(text.split())

assert blob(CAND)==EXP["candidate_blob_sha"], (blob(CAND),EXP["candidate_blob_sha"])
c=json.loads(CAND.read_text())
assert c["canonical_freeze"]["frozen_opus55_bar_elo"]==1846
assert c["reconciliation"]["frozen_bar_for_current_protocol"]==1846
assert c["reconciliation"]["frozen_target_mutation_authorized"] is False
assert c["acceptance_credit_delta"]==0
assert c["fresh_reality_authority"] is False

anth=fetch(EXP["urls"]["anthropic"])
assert "GDPval-AA v2.1" in anth and "1846" in anth and "Opus 5.5" in anth

live=fetch(EXP["urls"]["aa_live"])
assert "Claude Opus 5.5" in live and "GDPval-AA v2.1" in live and "1867" in live

meth=fetch(EXP["urls"]["aa_methodology"])
for needle in ["GDPval-AA v2.1","Crowd-BT","1600","Elo scores shift","rank ordering is largely preserved"]:
    assert needle in meth, needle
assert ("update the reference parameters" in meth) or ("reference parameters" in meth)

print(json.dumps({
  "schema":"PROJECT_BRAIN_GDPVAL_OPUS55_FIXED_BAR_PROVENANCE_PUBLIC_RUNNER_RESULT_V1",
  "pass":True,
  "status":"PASS__ANTHROPIC_1846_RELEASE_BAR__AA_LIVE_1867__CROWD_BT_ELO_DRIFT_SEMANTICS__ZERO_CREDIT"
},sort_keys=True))
