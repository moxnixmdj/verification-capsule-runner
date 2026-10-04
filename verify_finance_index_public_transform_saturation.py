import json, pathlib, re, subprocess, urllib.request

FILES = {
  "cut": "subject/FINANCE_INDEX_PUBLIC_TRANSFORM_ROUTE_SATURATION_20261004_V1.json",
  "floor": "subject/FINANCE_INDEX_COMPONENT_FLOOR_BOUNDARY_20261004_V1.json",
  "fanout": "subject/ROOT2_OWNER_CHANNEL_FANOUT_V2.json",
}
EXPECTED = {
  "cut": "2a831b8632b18fe9e10ed423f131b6ae93d99b77",
  "floor": "277feb222baaa87526a17ac846d16413b31df44a",
  "fanout": "9b59f951f5b7135bb167f2aaebc35e9960172fa4",
}

def blob(path):
    return subprocess.check_output(["git","rev-parse",f"HEAD:{path}"], text=True).strip()

for k,p in FILES.items():
    got=blob(p)
    assert got==EXPECTED[k], (k,got,EXPECTED[k])

cut=json.loads(pathlib.Path(FILES["cut"]).read_text())
floor=json.loads(pathlib.Path(FILES["floor"]).read_text())
fan=json.loads(pathlib.Path(FILES["fanout"]).read_text())

assert cut["target_predicate"]=="FINANCE_ACCOUNTING_INDEX_GE_61"
assert cut["prior_boundary"]["git_blob_sha"]==EXPECTED["floor"]
assert cut["existing_owner_channel_binding"]["git_blob_sha"]==EXPECTED["fanout"]
assert cut["exact_deduction"]["public_free_api_can_return_final_finance_index"] is True
assert cut["exact_deduction"]["public_free_api_can_return_six_headline_capability_indexes"] is True
assert cut["exact_deduction"]["public_free_api_per_benchmark_scores"] is False
assert cut["exact_deduction"]["public_free_api_documented_finance_capability_subscores"] is False
assert cut["exact_deduction"]["public_free_api_documented_inner_capability_transform"] is False
assert cut["exact_deduction"]["finance_subscore_zero_floor_proved"] is False
assert cut["exact_deduction"]["direct_threshold_predicate_closed"] is False
assert cut["accounting"]["incremental_spend_usd"]==0
assert cut["accounting"]["terminal_cases_consumed"]==0
assert cut["accounting"]["acceptance_credit_delta"]==0
assert cut["fresh_reality_authority"] is False
assert cut["execution_authority"] is False
assert cut["promotion_authority"] is False
assert floor["exact_missing_theorem"]["statement"]
assert floor["scheduling_effect_if_verified"]["zero_floor_substitution_authorized"] is False

aa = next(x for x in fan["owner_exclusive_channels"] if x["owner"]=="Artificial Analysis")
assert aa["state"]=="OUTREACH_SENT"
assert "Finance & Accounting Index/components" in aa["surfaces"]
assert "NO_DUPLICATE_OWNER_OUTREACH_WITHOUT_MATERIAL_WAKE" in fan["hard_rules"]

def fetch(url):
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 Project-Brain-Independent-Verifier"})
    with urllib.request.urlopen(req,timeout=45) as r:
        return r.read().decode("utf-8","ignore").lower()

def textify(html):
    return re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",html))

finance=textify(fetch("https://artificialanalysis.ai/models/capabilities/finance-and-accounting"))
docs=textify(fetch("https://artificialanalysis.ai/data-api/docs"))

assert "weighted average of its capability sub-scores" in finance
for token in ["business knowledge", "agentic knowledge work", "reasoning", "agentic tool use", "long-context", "non-hallucination"]:
    assert token in finance
assert "get language models (free tier)" in docs
assert "/api/v2/language/models/free" in docs
assert "six capability indexes" in docs
assert "pro tier adds per-benchmark scores" in docs
assert "free tier requests return a" in docs and "403" in docs and "subscription error" in docs
assert "aa_omniscience_breakdown" in docs and "pro tier only" in docs

print("FINANCE_INDEX_PUBLIC_TRANSFORM_ROUTE_SATURATION_PASS__PUBLIC_FREE_ROUTE_DELETED__ZERO_FLOOR_NOT_PROVED__ZERO_CREDIT")
