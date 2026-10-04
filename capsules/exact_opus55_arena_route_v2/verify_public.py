from __future__ import annotations
import hashlib, json, pathlib, urllib.request

ROOT=pathlib.Path(__file__).resolve().parent
AUDIT=ROOT/"EXACT_OPUS_5_5_ZERO_COST_COMPARATOR_ACCESS_AUDIT_V2.json"
raw=AUDIT.read_bytes()
got=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
assert got=="bf0408a470596c4f137bddfeda65c9709be56140", got
a=json.loads(raw)

url="https://portal.api.preview.arena.ai/docs/api-reference"
req=urllib.request.Request(url,headers={"User-Agent":"project-brain-public-verifier/1.0"})
with urllib.request.urlopen(req,timeout=60) as r:
    page=r.read().decode("utf-8","replace")

# Public machine-channel facts only.
for needle in [
    "api.preview.arena.ai",
    "/v1/models",
    "/v1/chat/completions",
    "/v1/messages",
    "allow_fallbacks",
    "Authorization",
]:
    assert needle in page, needle

arena=[x for x in a["observations"] if x[0]=="ARENA_API"]
assert len(arena)==1
assert a["implications"]["arena_machine_channel_exists"] is True
assert a["implications"]["arena_machine_route_currently_admissible"] is False
assert a["implications"]["matched_superportfolio_unblocked"] is False
assert a["implications"]["exact_identity_required"] is True
assert a["implications"]["proxy_substitution_admissible"] is False
assert "ACCOUNT_V1_MODELS_INCLUDES_EXACT_REQUIRED_OPUS55_VARIANT" in a["implications"]["arena_api_remaining_account_facts"]
assert "ACCOUNT_CREDIT_OR_PLAN_PROVES_ZERO_INCREMENTAL_SPEND_FOR_FUTURE_MATCHED_WAVE" in a["implications"]["arena_api_remaining_account_facts"]

# Public docs do not prove the two decisive account facts.
assert "NO_CLAIM_PUBLIC_ARENA_API_DOCS_PROVE_CLAUDE_OPUS_5_5_IS_IN_THIS_ACCOUNT_V1_MODELS" in a["hard_nonclaims"]
assert "NO_CLAIM_ARENA_API_REQUESTS_ARE_ZERO_COST_WITHOUT_ACCOUNT_CREDIT_OR_PLAN_RECEIPT" in a["hard_nonclaims"]

assert a["accounting"]["incremental_spend_usd"]==0
assert a["accounting"]["terminal_cases_consumed"]==0
assert a["accounting"]["acceptance_credit_delta"]==0
assert a["execution_authority"] is False
assert a["promotion_authority"] is False
assert a["fresh_reality_authority"] is False

print("EXACT_OPUS55_ARENA_API_PUBLIC_ROUTE_V2_PASS")
