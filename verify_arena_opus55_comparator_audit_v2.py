import json, pathlib, re, subprocess, urllib.request

PATH="subject/EXACT_OPUS_5_5_ZERO_COST_COMPARATOR_ACCESS_AUDIT_V2.json"
EXPECTED="bf0408a470596c4f137bddfeda65c9709be56140"
got=subprocess.check_output(["git","rev-parse",f"HEAD:{PATH}"],text=True).strip()
assert got==EXPECTED,(got,EXPECTED)
j=json.loads(pathlib.Path(PATH).read_text())

assert j["status"]=="CANDIDATE__ZERO_COST_EXACT_MACHINE_COMPARATOR_STILL_UNBOUND__ACCOUNT_ROUTES_RECONCILED__ZERO_CREDIT"
imp=j["implications"]
assert imp["matched_superportfolio_unblocked"] is False
assert imp["exact_identity_required"] is True
assert imp["auto_model_selection_admissible"] is False
assert imp["proxy_substitution_admissible"] is False
assert imp["arena_machine_channel_exists"] is True
assert imp["arena_machine_channel_publicly_verified"] is True
assert imp["arena_machine_route_currently_admissible"] is False
assert imp["arena_api_remaining_account_facts"]==[
 "ARENA_ACCOUNT_AND_VIRTUAL_API_KEY",
 "ACCOUNT_V1_MODELS_INCLUDES_EXACT_REQUIRED_OPUS55_VARIANT",
 "ACCOUNT_CREDIT_OR_PLAN_PROVES_ZERO_INCREMENTAL_SPEND_FOR_FUTURE_MATCHED_WAVE",
 "HARNESS_AND_EFFORT_RELATION_TO_FROZEN_COMPARATOR",
]
assert j["execution_authority"] is False
assert j["promotion_authority"] is False
assert j["fresh_reality_authority"] is False
for k in ("incremental_spend_usd","terminal_cases_consumed","acceptance_credit_delta",
          "family_credit_delta","capability_credit_delta","ownership_credit_delta"):
    assert j["accounting"][k]==0,(k,j["accounting"][k])

def fetch(url):
    req=urllib.request.Request(url,headers={"User-Agent":"project-brain-independent-verifier/1.0"})
    with urllib.request.urlopen(req,timeout=30) as r:
        return r.read().decode("utf-8","replace")

api=fetch("https://portal.api.preview.arena.ai/docs/api-reference")
routing=fetch("https://portal.api.preview.arena.ai/docs/routing")
selector=fetch("https://help.arena.ai/articles/1858200927-lmarena-experiments-new-model-selector")

for needle in ("OpenAI-compatible","/v1/models","/v1/chat/completions","Anthropic"):
    assert needle in api, needle
for needle in ("X-Arena-Resolved-Model","fallbacks","model"):
    assert needle in routing, needle
for needle in ("Direct","Select a model"):
    assert needle in selector, needle

# Critical anti-overclaim: public docs prove a machine channel, not this account's exact Opus 5.5 entitlement or free balance.
nonclaims="\n".join(j["hard_nonclaims"])
assert "NO_CLAIM_PUBLIC_ARENA_API_DOCS_PROVE_CLAUDE_OPUS_5_5_IS_IN_THIS_ACCOUNT_V1_MODELS" in nonclaims
assert "NO_CLAIM_ARENA_API_REQUESTS_ARE_ZERO_COST_WITHOUT_ACCOUNT_CREDIT_OR_PLAN_RECEIPT" in nonclaims

print("PASS: Arena machine API channel independently verified from first-party docs")
print("PASS: exact Opus 5.5 account availability/credit/harness remain unbound")
print("PASS: zero spend, zero cases, zero acceptance credit, no fresh-reality authority")
