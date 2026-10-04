#!/usr/bin/env python3
import hashlib, html, json, re, urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parent
FILES={
  "candidate":ROOT/"candidate.json",
  "envelope":ROOT/"envelope.json",
  "registry":ROOT/"predicate_registry.json",
  "adapter_governance":ROOT/"brain_adapter_governance.json",
  "adapter_verification":ROOT/"brain_adapter_verification.json",
}
EXPECTED={
  "candidate":"ef67dc84dc02f2216f9e1d0123dbf5d40b6ed173",
  "envelope":"661a57f839101fbf54c7e4edc76166c65ce9327d",
  "registry":"562536d9ba3f245a6bd24490a1eb3b30f27e0c3a",
  "adapter_governance":"f0352c187eb921d6e736608825005df887449488",
  "adapter_verification":"841fc40bd2f54b451e01d32afd9a79a32aaafa0b",
}
URLS={
  "launch":"https://www.anthropic.com/claude-opus-5-5",
  "system_card":"https://www.anthropic.com/claude-opus-5-5-system-card",
  "surge_readme":"https://raw.githubusercontent.com/surge-ai/chartography/3f1bf837232d3918c2cc35c6e2418c9e70d2a57b/README.md",
}

def blob(path):
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def fetch(url,max_bytes=25_000_000):
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 ProjectBrainVerifier/1.0"})
    with urllib.request.urlopen(req,timeout=45) as r:
        raw=r.read(max_bytes)
        if len(raw)>=max_bytes:
            raise AssertionError("SOURCE_TOO_LARGE_OR_TRUNCATED:"+url)
    text=raw.decode("utf-8","replace")
    if "<html" in text[:5000].lower() or "<body" in text[:5000].lower():
        text=re.sub(r"<script[\s\S]*?</script>"," ",text,flags=re.I)
        text=re.sub(r"<style[\s\S]*?</style>"," ",text,flags=re.I)
        text=re.sub(r"<[^>]+>"," ",text)
        text=html.unescape(text)
    return " ".join(text.split())

actual={k:blob(v) for k,v in FILES.items()}
assert actual==EXPECTED,(actual,EXPECTED)

cand=json.loads(FILES["candidate"].read_text())
env=json.loads(FILES["envelope"].read_text())
reg=json.loads(FILES["registry"].read_text())
ag=json.loads(FILES["adapter_governance"].read_text())
av=json.loads(FILES["adapter_verification"].read_text())

assert cand["target_predicate"]=="CHARTOGRAPHY_TOOLS_GE_89"
assert cand["frozen_target"]["condition"]=="WITH_TOOLS"
assert cand["frozen_target"]["opus55_score_percent"]==89.0
assert cand["existing_brain_adapter"]["frozen_with_tools_discharge"] is False
assert cand["root_effect"]["root1"].startswith("UNCHANGED_INACTIVE")
assert cand["root_effect"]["root2"].startswith("OPEN__WITH_TOOLS_HARNESS_BINDING")
assert cand["terminal_cases_consumed"]==0
assert cand["acceptance_credit_delta"]==0

vision=next(x for x in env["families"] if x["id"]=="VISION_AND_DENSE_DOCUMENT_UNDERSTANDING")
bar=next(x for x in vision["public_bars"] if x["benchmark"]=="Chartography with tools")
assert bar["opus_5_5"]==89
pred=next(x for x in reg["predicates"] if x["id"]=="CHARTOGRAPHY_TOOLS_GE_89")
assert pred["acceptance"]=="Chartography with tools >= 89.0%"
assert pred["surface"]=="Chartography with tools"

assert "TOOLS_NOT_ALLOWED_IN_CHARTOGRAPHY_MODEL_CALL" in FILES["adapter_governance"].read_text() or "REJECTS_TOOLS" in json.dumps(ag)
assert av["verified"]["tests_passed"]==11
assert av["verified"]["tests_failed"]==0
assert av["verified"]["tools_forbidden"] is True

launch=fetch(URLS["launch"])
card=fetch(URLS["system_card"])
surge=fetch(URLS["surge_readme"],2_000_000)

assert "Chartography" in launch and "89.0%" in launch and "with tools" in launch.lower()
for phrase in [
  "Chartography",
  "adaptive thinking",
  "max effort",
  "evaluated with and without tools",
  "provided with a container",
  "image file and standard libraries installed",
  "image cropping tool",
  "Gemini 3.5 Flash",
  "64.4% without tools",
  "89.0% with tools",
]:
    assert phrase.lower() in card.lower(), phrase
assert "five runs" in card.lower()
assert "chart attached inline, no tools" in surge.lower()
assert "gemini 3.5 flash" in surge.lower()

known=set(cand["primary_source_protocol"]["with_tools_environment"])
assert known=={
  "CONTAINER",
  "IMAGE_FILE_PRESENT_IN_CONTAINER",
  "STANDARD_LIBRARIES_INSTALLED",
  "IMAGE_CROPPING_TOOL",
}
assert cand["corrected_root2_residual"]["no_tools_score_route"]=="NON_SUBSTITUTABLE_FOR_FROZEN_WITH_TOOLS_PREDICATE"

print(json.dumps({
  "schema":"PROJECT_BRAIN_CHARTOGRAPHY_OPUS55_WITH_TOOLS_PROTOCOL_PUBLIC_RUNNER_RESULT_V1",
  "pass":True,
  "status":"PASS__FIRST_PARTY_89_WITH_TOOLS__CONTAINER_IMAGE_STANDARD_LIBRARIES_CROP_TOOL__PUBLIC_NATIVE_NO_TOOLS_NON_SUBSTITUTABLE__BRAIN_NO_TOOLS_ADAPTER_SUBCOMPONENT_ONLY__ZERO_CASES__ZERO_CREDIT",
  "known_tool_envelope":["CONTAINER","IMAGE_FILE","STANDARD_LIBRARIES","IMAGE_CROPPING_TOOL"],
  "frozen_target_percent":89.0
},sort_keys=True))
