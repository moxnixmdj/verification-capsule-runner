import json, pathlib, subprocess, urllib.request, urllib.error

PATH="subject/EXACT_OPUS_5_5_ZERO_COST_COMPARATOR_ACCESS_AUDIT_V2.json"
EXPECTED="1e8ba20f18671537f1d6f52d9ab7362ac5a761f2"

def blob(path):
    return subprocess.check_output(["git","rev-parse",f"HEAD:{path}"],text=True).strip()

assert blob(PATH)==EXPECTED,(blob(PATH),EXPECTED)
j=json.loads(pathlib.Path(PATH).read_text())
imp=j["implications"]

assert j["status"]=="CANDIDATE__ZERO_COST_EXACT_MACHINE_COMPARATOR_STILL_UNBOUND__ACCOUNT_ROUTES_RECONCILED__ZERO_CREDIT"
assert imp["matched_superportfolio_unblocked"] is False
assert imp["exact_identity_required"] is True
assert imp["auto_model_selection_admissible"] is False
assert imp["proxy_substitution_admissible"] is False
assert imp["arena_machine_channel_exists"] is False
assert imp["arena_machine_channel_candidate_detected"] is True
assert imp["arena_authenticated_api_portal_independently_verifiable"] is True
assert imp["arena_machine_channel_publicly_verified"] is False
assert imp["arena_machine_route_currently_admissible"] is False
assert imp["arena_api_remaining_account_facts"]==[
 "ARENA_ACCOUNT_AND_VIRTUAL_API_KEY",
 "ACCOUNT_V1_MODELS_INCLUDES_EXACT_REQUIRED_OPUS55_VARIANT",
 "ACCOUNT_CREDIT_OR_PLAN_PROVES_ZERO_INCREMENTAL_SPEND_FOR_FUTURE_MATCHED_WAVE",
 "HARNESS_AND_EFFORT_RELATION_TO_FROZEN_COMPARATOR",
]

for k in ("incremental_spend_usd","terminal_cases_consumed","acceptance_credit_delta",
          "family_credit_delta","capability_credit_delta","ownership_credit_delta"):
    assert j["accounting"][k]==0,(k,j["accounting"][k])
assert j["execution_authority"] is False
assert j["promotion_authority"] is False
assert j["fresh_reality_authority"] is False

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

opener=urllib.request.build_opener(NoRedirect())
req=urllib.request.Request(
    "https://portal.api.preview.arena.ai/docs/api-reference",
    headers={"User-Agent":"project-brain-independent-verifier/1.0"}
)
try:
    r=opener.open(req,timeout=30)
    status=r.status
    location=r.headers.get("Location","")
except urllib.error.HTTPError as e:
    status=e.code
    location=e.headers.get("Location","")
assert 300 <= status < 400,(status,location)
assert ("workos.com" in location or "/auth/" in location or "authorize" in location.lower()),location

# Public Direct selector evidence remains independently readable and only proves human exact-selection capability.
url="https://help.arena.ai/articles/1858200927-lmarena-experiments-new-model-selector"
with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"project-brain-independent-verifier/1.0"}),timeout=30) as r:
    selector=r.read().decode("utf-8","replace")
assert "Direct" in selector
assert ("Select a model" in selector or "select a model" in selector)

nonclaims="\n".join(j["hard_nonclaims"])
assert "NO_CLAIM_PUBLIC_ARENA_API_DOCS_PROVE_CLAUDE_OPUS_5_5_IS_IN_THIS_ACCOUNT_V1_MODELS" in nonclaims
assert "NO_CLAIM_ARENA_API_REQUESTS_ARE_ZERO_COST_WITHOUT_ACCOUNT_CREDIT_OR_PLAN_RECEIPT" in nonclaims
assert "NO_CLAIM_LOGIN_GATED_ARENA_ROUTING_DOC_CONTENT_IS_INDEPENDENTLY_PUBLIC_RUNNER_REPRODUCED" in nonclaims

print("PASS: Arena authenticated API portal independently verified")
print("PASS: human Direct exact-selection surface independently verified")
print("PASS: machine comparator channel remains candidate-only and inadmissible")
print("PASS: exact account model/credit/harness facts remain unbound; zero spend/cases/credit")
