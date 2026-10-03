#!/usr/bin/env python3
import json, subprocess, urllib.request

CUT="fixtures/current_zero_reality_cut_v12.json"
DELTA="fixtures/root2_public_account_boundary_delta_v1.json"

def load(p):
    with open(p,encoding="utf-8") as f:
        return json.load(f)

def blob(p):
    return subprocess.check_output(["git","hash-object",p],text=True).strip()

def fetch(url):
    req=urllib.request.Request(url,headers={"User-Agent":"Project-Brain-V12-Public-Boundary-Verifier"})
    with urllib.request.urlopen(req,timeout=45) as r:
        return r.read().decode("utf-8","replace")

cut=load(CUT)
delta=load(DELTA)
assert blob(CUT)=="37631739d83ae0098a3c63a16bd23a1686d3bf12"
assert blob(DELTA)=="e5e49002a1a3635062cdb580d5a85f5f4e0734a4"
assert cut["schema"]=="PROJECT_BRAIN_CURRENT_ZERO_REALITY_MINIMUM_CUT_V12"
assert delta["schema"]=="PROJECT_BRAIN_ROOT2_PUBLIC_ACCOUNT_BOUNDARY_DELTA_20261003_V1"

s=cut["exact_state"]
assert (s["accepted_families"],s["open_families"],s["proved_atomic"],s["unresolved_atomic"])==(5,14,12,26)
assert s["terminal"] is False
assert s["root1_positive_gap_count"]==0

for doc in (cut,delta):
    for k in ["new_reality_units_consumed","terminal_cases_consumed","incremental_spend_usd","acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta"]:
        assert doc[k]==0
    assert doc["execution_authority"] is False
    assert doc["promotion_authority"] is False
    assert doc["fresh_reality_authority"] is False

c=delta["chartography"]["proved_public_facts"]
assert c["full_task_count"]==100
assert c["leaderboard_epochs"]==10
assert c["judge_calls_per_sample"]==1
assert c["exact_leaderboard_judge_call_mass"]==1000
assert c["exact_leaderboard_judge_call_mass"]==c["full_task_count"]*c["leaderboard_epochs"]*c["judge_calls_per_sample"]
assert c["standard_free_tier_input_price_usd"]==0
assert c["standard_free_tier_output_price_usd"]==0

chart=fetch("https://raw.githubusercontent.com/surge-ai/chartography/3f1bf837232d3918c2cc35c6e2418c9e70d2a57b/README.md")
assert "all 100 tasks" in chart
assert "--epochs 10" in chart
assert "judge_model=google/gemini-3.5-flash" in chart
assert "one model-graded call per sample" in chart

pricing=fetch("https://ai.google.dev/gemini-api/docs/pricing?hl=en")
assert "Gemini 3.5 Flash" in pricing
assert "Free of charge" in pricing

limits=fetch("https://ai.google.dev/gemini-api/docs/rate-limits?hl=en")
ll=limits.lower()
assert "per project" in ll
assert "ai studio" in ll
assert "not guaranteed" in ll

o=delta["osworld_2_1"]["proved_public_facts"]
assert o["task_access_request_auto_approved_after_acceptance"] is True
assert o["gated_asset_access_requires_acceptance"] is True
assert o["gated_asset_auto_approval_not_claimed"] is True
assert o["exact_release_component_matching_required"] is True
assert o["public_assets_are_not_complete_task_asset_source"] is True

osw=fetch("https://raw.githubusercontent.com/xlang-ai/OSWorld-V2/acdd3493808e716825975b0f0208194bb2faf3c3/README.md")
assert "osworld-v2.1" in osw
assert "your request will automatically be approved" in osw
assert "xlangai/osworld_v2_assets_gated@osworld-v2.1" in osw
assert "Task-Web/OSWorld-web@osworld-v2.1" in osw
ol=osw.lower()\nassert "complete asset snapshots are distributed only through the gated" in ol\nassert "xlangai/osworld_v2_assets@osworld-v2.1" in osw

weights=delta["finance_index"]["public_methodology_reconfirmed"]["component_weights"]
assert abs(sum(weights.values())-1.0)<1e-12
assert weights=={
    "BUSINESS_KNOWLEDGE":0.30,
    "AGENTIC_KNOWLEDGE_WORK":0.30,
    "REASONING":0.20,
    "AGENTIC_TOOL_USE":0.10,
    "LONG_CONTEXT":0.05,
    "NON_HALLUCINATION":0.05,
}

hle=fetch("https://raw.githubusercontent.com/centerforaisafety/hle/main/README.md")
assert "run_model_predictions.py" in hle
assert "run_judge_results.py" in hle

assert "ACCOUNT_BOUND_ACTIVE_RPM_RPD_SUFFICIENCY_FOR_1000_JUDGE_CALLS_WITH_RETRY_POLICY" in delta["chartography"]["remaining"]
assert "ACCOUNT_STATE_CHECK_FOR_TASK_AND_GATED_ASSET_ACCEPTANCE" in delta["osworld_2_1"]["remaining"]
assert delta["acceptance_credit_delta"]==0

print("CURRENT_ZERO_REALITY_MINIMUM_CUT_V12_PUBLIC_BOUNDARIES_VERIFIED")
