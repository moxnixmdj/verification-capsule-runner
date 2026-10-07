#!/usr/bin/env python3
import hashlib, html, json, pathlib, re, urllib.request

ROOT=pathlib.Path(__file__).resolve().parent

def blob_sha(path):
    raw=path.read_bytes()
    return hashlib.sha1(f"blob {len(raw)}\0".encode()+raw).hexdigest()

def fetch(url):
    req=urllib.request.Request(url,headers={"User-Agent":"project-brain-public-verifier/1.0"})
    with urllib.request.urlopen(req,timeout=90) as r:
        assert r.status==200,(url,r.status)
        return r.read().decode("utf-8","replace")

def norm(s):
    s=html.unescape(s).replace("’","'").replace("–","-").replace("—","-")
    s=re.sub(r"<[^>]+>"," ",s)
    return re.sub(r"\s+"," ",s).lower()

expected=json.load(open(ROOT/"EXPECTED_BRAIN_BLOBS.json",encoding="utf-8"))
for rel,exp in expected["exact_brain_blobs"].items():
    got=blob_sha(ROOT/rel)
    assert got==exp,(rel,got,exp)

subject=json.load(open(ROOT/"canonical/governance/OPUS55_CURRENT_AUTHORIZED_PROFILE_SET_TRUTH_REPAIR_20261005_V1.json",encoding="utf-8"))
launch=norm(fetch("https://www.anthropic.com/claude-opus-5-5"))
help_page=norm(fetch("https://support.claude.com/en/articles/16049681-why-claude-switched-models-in-your-conversation-with-opus-5-or-opus-5-5"))
docs=norm(fetch("https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5"))

# First-party current-state facts.
assert "life sciences verification program" in launch
assert "use opus 5.5 for biology research" in launch
assert "cyber verification program" in launch
assert "in the coming weeks" in launch
assert "most cybersecurity tasks will be re-routed to opus 4.8" in launch or "most cybersecurity tasks will be rerouted to opus 4.8" in launch

# The Help Center is the load-bearing current availability source.
assert "opus 5.5 isn't currently available in the cyber verification program" in help_page
assert "life sciences verification program" in help_page

# Current platform docs independently confirm live safeguard classes and the LSVP route.
assert "claude opus 5.5 runs safety classifiers" in docs
for token in ("biology","cybersecurity","reasoning extraction","life sciences verification program"):
    assert token in docs,token

inc={x["profile_id"]:x for x in subject["current_profile_membership"]["include"]}
exc={x["profile_id"]:x for x in subject["current_profile_membership"]["exclude_until_activation_event"]}
assert "OPUS55_GENERAL_PRODUCTION_SAFEGUARDED" in inc
assert "OPUS55_LIFE_SCIENCES_VERIFIED" in inc
assert exc["OPUS55_CYBER_VERIFIED"]["current_membership"]=="FALSE_AS_OF_2026_10_05_FIRST_PARTY_HELP_CENTER"
assert subject["accounting"]["acceptance_credit_delta"]==0
assert subject["promotion_authority"] is False

print(json.dumps({
  "schema":"PROJECT_BRAIN_OPUS55_CURRENT_PROFILE_PUBLIC_RUNNER_RESULT_V1",
  "status":"PASS__CURRENT_FIRST_PARTY_SOURCES_CONFIRM_LSVP_CURRENT_AND_CYBER_VERIFICATION_OPUS55_NOT_CURRENTLY_AVAILABLE__ZERO_CREDIT",
  "subject_git_blob_sha":expected["exact_brain_blobs"]["canonical/governance/OPUS55_CURRENT_AUTHORIZED_PROFILE_SET_TRUTH_REPAIR_20261005_V1.json"],
  "life_sciences_verified_current":True,
  "cyber_verified_opus55_current":False,
  "future_cyber_wake_condition_preserved":True,
  "terminal_cases_consumed":0,
  "incremental_spend_usd":0,
  "acceptance_credit_delta":0
},sort_keys=True))
