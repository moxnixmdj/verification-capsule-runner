import hashlib, json, pathlib, re, urllib.request

FILES = {
  "carrier": "subject/TB4_BUILDKITE_ALL_ACCESS_TRIAL_CARRIER_CANDIDATE_20261004_V1.json",
  "frontier": "subject/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V2.json",
}
EXPECTED = {
  "carrier": "2725cf6820fb7ce6025213d474b9acf2937282ee",
  "frontier": "36013ab1768260cca9dca4dbe1aa11a68dab56cf",
}

def git_blob_sha(path):
    b=pathlib.Path(path).read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

for k,p in FILES.items():
    got=git_blob_sha(p)
    assert got==EXPECTED[k], (k,got,EXPECTED[k])

carrier=json.loads(pathlib.Path(FILES["carrier"]).read_text())
frontier=json.loads(pathlib.Path(FILES["frontier"]).read_text())

env=carrier["frozen_minimum_envelope"]
assert env["cpus_at_least"]==8
assert env["usable_memory_mb_at_least"]==16384
assert env["free_storage_mb_at_least"]==51200
assert env["docker_required"] is True and env["docker_compose_required"] is True
assert carrier["narrow_conclusion"]["tb4_carrier_admissibility_proved"] is False
assert carrier["execution_authority"] is False
assert carrier["promotion_authority"] is False
assert carrier["fresh_reality_authority"] is False
assert carrier["incremental_spend_usd"]==0
assert "NO_TB4_CARRIER_PROMOTION_FROM_PROVIDER_DOCUMENTATION_ALONE" in frontier["hard_rules"]

s=[x for x in frontier["verified_or_primary_source_deltas"] if x["target"]=="SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR"]
assert len(s)==1
assert s[0]["remaining"]==["metric:matched_quality","matched_quality_noninferiority"]
assert s[0]["delete"]=="required_claim_coverage_noninferiority"
t=[x for x in frontier["verified_or_primary_source_deltas"] if x["target"]=="CODING_TB4_GE_66_4"]
assert len(t)==1 and "BUILDKITE" in t[0]["replace_with"]
assert frontier["fresh_reality_authority"] is False
assert frontier["accounting"]["incremental_spend_usd"]==0

def fetch(url):
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 Project-Brain-Independent-Verifier"})
    with urllib.request.urlopen(req,timeout=30) as r:
        return r.read().decode("utf-8","ignore")

linux=fetch("https://buildkite.com/docs/agent/buildkite-hosted/linux")
pricing=fetch("https://www.buildkite.com/pricing/")
linux_text=re.sub(r"<[^>]+>"," ",linux)
pricing_text=re.sub(r"<[^>]+>"," ",pricing)
linux_text=re.sub(r"\s+"," ",linux_text)
pricing_text=re.sub(r"\s+"," ",pricing_text)

for token in ["LINUX_AMD64_8X32","8","32 GB","158 GB","docker","docker-compose"]:
    assert token.lower() in linux_text.lower(), token
for token in ["30 days","all-access trial","No credit card"]:
    assert token.lower() in pricing_text.lower(), token

print("ROOT2_FRONTIER_V2_BUILDKITE_INDEPENDENT_PASS__NAMED_CARRIER_WAKE_ONLY__SYNTHESIS_TWO_RESIDUALS__ZERO_CREDIT")
