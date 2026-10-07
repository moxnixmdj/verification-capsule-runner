import json, re, subprocess, urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parent
def load(n):
    return json.load(open(ROOT/n,encoding="utf-8"))
def blob(n):
    return subprocess.check_output(["git","hash-object",str(ROOT/n)],text=True).strip()
def fetch(url):
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0"})
    with urllib.request.urlopen(req,timeout=30) as r:
        return r.read().decode("utf-8","ignore").lower()

m=load("manifest.json")
for n,sha in m["exact_blobs"].items():
    assert blob(n)==sha,(n,sha,blob(n))

s=load("subject.json"); e=load("envelope.json"); g=load("guard.json"); f=load("fixed_interface.json")
assert e["target_family_count"]==19==len(e["families"])
assert e["acceptance_rule"]=="BRAIN_CONFIGURED_CAPABILITY_MUST_EQUAL_OR_EXCEED_OPUS_5_5_ON_RELEVANT_USEFUL_CONDITIONS"
assert "MULTILINGUAL" in g["mandatory_conditions"]
assert "LONG_CONTEXT" in g["mandatory_conditions"]
assert any("19_CANONICAL_FAMILIES_COVER_EVERY_B0_THROUGH_B9_ROLE" in p for p in f["trace_normal_form"]["theorem"]["premises"])

# Exact frozen-envelope absence audit. Do not infer semantics from family labels.
records=[{"useful_behavior":x.get("useful_behavior",""),"public_bars":x.get("public_bars",[])} for x in e["families"]]
raw=json.dumps(records,sort_keys=True).lower()
assert "multilingual" not in raw
assert re.search(r"\\blanguage\\b",raw) is None
assert "1m" not in raw
assert "1,000,000" not in raw
assert "1000000" not in raw
assert "context window" not in raw

# Independent live first-party source checks.
overview=fetch("https://platform.claude.com/docs/en/models/overview")
opus=fetch("https://platform.claude.com/docs/en/models/opus-5-5/overview")
multi=fetch("https://platform.claude.com/docs/en/build-with-claude/multilingual-support")
assert "multilingual" in overview
assert "claude opus 5.5" in overview
assert "1m" in opus and "claude opus 5.5" in opus
assert "multilingual" in multi and ("most world languages" in multi or "many languages" in multi)
assert "claude-opus-5-5" in multi

assert s["exact_frozen_envelope_audit"]["multilingual"]["explicit_language_or_multilingual_binding_count"]==0
assert s["exact_frozen_envelope_audit"]["one_million_context"]["explicit_1m_or_context_window_parity_binding_count"]==0
assert s["minimum_repair"]["representation"]=="CONDITION_OVERLAY_NOT_NEW_FAMILY"
assert [x["id"] for x in s["minimum_repair"]["overlays"]]==["C_MULTILINGUAL","C_LONG_CONTEXT_1M"]
assert "NO_CLAIM_A_20TH_FAMILY_IS_REQUIRED" in s["hard_nonclaims"]
for k,v in s["accounting"].items(): assert v==0,(k,v)
assert s["scheduling_authority"] is False
assert s["execution_authority"] is False
assert s["promotion_authority"] is False
assert s["fresh_reality_authority"] is False
assert s["independent_verification_required"] is True
print("P3_CONDITION_OVERLAY_MINIMUM_CUT_VERIFIED")
