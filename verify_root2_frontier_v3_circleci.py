import hashlib, json, pathlib, re, urllib.request

FILES = {
    "carrier": "subject/TB4_CIRCLECI_GEN2_FREE_PLAN_CARRIER_CANDIDATE_20261004_V1.json",
    "frontier": "subject/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V3.json",
}
EXPECTED = {
    "carrier": "b855ce5c4d8f192cb806be468a8d5c1e7c2f2a93",
    "frontier": "681123ef6cff3506d66af6b31b61c8bc14a8a913",
}

def git_blob_sha(path):
    b = pathlib.Path(path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()

for k, p in FILES.items():
    got = git_blob_sha(p)
    assert got == EXPECTED[k], (k, got, EXPECTED[k])

carrier = json.loads(pathlib.Path(FILES["carrier"]).read_text())
frontier = json.loads(pathlib.Path(FILES["frontier"]).read_text())

env = carrier["frozen_minimum_envelope"]
assert env["cpus_at_least"] == 8
assert env["usable_memory_mb_at_least"] == 16384
assert env["free_storage_mb_at_least"] == 51200
assert env["docker_required"] is True
assert env["docker_compose_required"] is True

nc = carrier["narrow_conclusion"]
assert nc["named_information_positive_route_exists"] is True
assert nc["free_plan_gen2_policy_proved_by_primary_source"] is True
assert nc["nominal_cpu_requirement_met"] is True
assert nc["nominal_memory_requirement_met"] is True
assert nc["nominal_free_disk_requirement_proved"] is False
assert nc["xlarge_gen2_free_plan_account_access_proved"] is False
assert nc["docker_runtime_semantics_for_tb4_proved"] is False
assert nc["docker_compose_runtime_semantics_for_tb4_proved"] is False
assert nc["allowance_sufficient_for_minimum_recovery_transaction_proved"] is False
assert nc["tb4_carrier_admissibility_proved"] is False

for k in ["execution_authority", "promotion_authority", "fresh_reality_authority"]:
    assert carrier[k] is False
    assert frontier[k] is False

for k in [
    "incremental_spend_usd",
    "acceptance_credit_delta",
    "family_credit_delta",
    "capability_credit_delta",
    "ownership_credit_delta",
    "terminal_cases_consumed",
]:
    assert carrier[k] == 0

assert frontier["accounting"]["incremental_spend_usd"] == 0
assert frontier["accounting"]["terminal_cases_consumed"] == 0
assert frontier["source_bindings"]["tb4_buildkite_documentary_reduction"]["git_blob_sha"] == "2997d7f95227d024a55aa201b3fced53f85a01e8"

portfolio = frontier["tb4_carrier_portfolio"]
providers = {x["provider"] for x in portfolio["candidates"]}
assert providers == {"Buildkite", "CircleCI"}
assert "DO_NOT_SUM_CORRELATED_OR_UNCALIBRATED_PROBABILITIES" in portfolio["policy"]
buildkite_state = next(x["state"] for x in portfolio["candidates"] if x["provider"] == "Buildkite")
assert "DOCUMENTARY_REQUIREMENTS_REDUCED" in buildkite_state
assert "NO_TB4_CIRCLECI_PROMOTION_FROM_FREE_PLAN_DOCUMENTATION_ALONE" in frontier["hard_rules"]
assert "TB4_CIRCLECI_FREE_PLAN_ACCOUNT_AND_ZERO_CASE_PREFLIGHT_WHEN_ACCOUNT_ACCESS_IS_AVAILABLE" in frontier["runnable_zero_reality"]
assert "CIRCLECI_FREE_PLAN_XLARGE_GEN2_DISK_RUNTIME_AND_ALLOWANCE" in frontier["waiting_external_facts"]

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 Project-Brain-Independent-Verifier"})
    with urllib.request.urlopen(req, timeout=45) as response:
        return response.read().decode("utf-8", "ignore")

def textify(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).lower()

changelog = textify(fetch("https://circleci.com/changelog/"))
docker = textify(fetch("https://circleci.com/docs/guides/execution-managed/using-docker/"))
credits = textify(fetch("https://circleci.com/docs/guides/plans-pricing/credits/"))
price = textify(fetch("https://circleci.com/pricing/price-list/"))

assert "gen2 x86 docker resource classes now available on free plans" in changelog
assert "xlarge.gen2" in docker
assert "8" in docker and "16 gb" in docker
assert ("30,000" in credits or "30000" in credits)
assert ("400,000" in credits or "400000" in credits)
assert "blocked" in credits and "credits" in credits
assert "xlarge.gen2" in price
assert "48" in price

print("ROOT2_FRONTIER_V3_CIRCLECI_INDEPENDENT_PASS__SECOND_ORTHOGONAL_TB4_WAKE_ONLY__ZERO_CREDIT")
