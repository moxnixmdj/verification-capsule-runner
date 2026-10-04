import json, pathlib, re, subprocess, urllib.request

FILES = {
    "carrier": "subject/TB4_CIRCLECI_GEN2_FREE_PLAN_CARRIER_CANDIDATE_20261004_V1.json",
    "frontier": "subject/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V3.json",
}
EXPECTED = {
    "carrier": "b855ce5c4d8f192cb806be468a8d5c1e7c2f2a93",
    "frontier": "681123ef6cff3506d66af6b31b61c8bc14a8a913",
}

def committed_blob_sha(path):
    return subprocess.check_output(["git", "rev-parse", f"HEAD:{path}"], text=True).strip()

for key, path in FILES.items():
    got = committed_blob_sha(path)
    assert got == EXPECTED[key], (key, got, EXPECTED[key])

carrier = json.loads(pathlib.Path(FILES["carrier"]).read_text())
frontier = json.loads(pathlib.Path(FILES["frontier"]).read_text())

env = carrier["frozen_minimum_envelope"]
assert env == {
    "cpus_at_least": 8,
    "usable_memory_mb_at_least": 16384,
    "free_storage_mb_at_least": 51200,
    "docker_required": True,
    "docker_compose_required": True,
    "additional_creditable_tasks_needed": 8,
}

nc = carrier["narrow_conclusion"]
for key in [
    "nominal_free_disk_requirement_proved",
    "xlarge_gen2_free_plan_account_access_proved",
    "docker_runtime_semantics_for_tb4_proved",
    "docker_compose_runtime_semantics_for_tb4_proved",
    "allowance_sufficient_for_minimum_recovery_transaction_proved",
    "tb4_carrier_admissibility_proved",
]:
    assert nc[key] is False, key

assert nc["named_information_positive_route_exists"] is True
assert nc["free_plan_gen2_policy_proved_by_primary_source"] is True
assert nc["nominal_cpu_requirement_met"] is True
assert nc["nominal_memory_requirement_met"] is True

assert carrier["execution_authority"] is False
assert carrier["promotion_authority"] is False
assert carrier["fresh_reality_authority"] is False
assert carrier["incremental_spend_usd"] == 0
assert carrier["terminal_cases_consumed"] == 0
assert carrier["acceptance_credit_delta"] == 0

assert frontier["execution_authority"] is False
assert frontier["promotion_authority"] is False
assert frontier["fresh_reality_authority"] is False
assert frontier["accounting"]["incremental_spend_usd"] == 0
assert frontier["accounting"]["terminal_cases_consumed"] == 0
assert frontier["source_bindings"]["tb4_buildkite_documentary_reduction"]["git_blob_sha"] == "2997d7f95227d024a55aa201b3fced53f85a01e8"

portfolio = frontier["tb4_carrier_portfolio"]
providers = {item["provider"] for item in portfolio["candidates"]}
assert providers == {"Buildkite", "CircleCI"}
assert "DO_NOT_SUM_CORRELATED_OR_UNCALIBRATED_PROBABILITIES" in portfolio["policy"]
buildkite = next(item for item in portfolio["candidates"] if item["provider"] == "Buildkite")
assert "DOCUMENTARY_REQUIREMENTS_REDUCED" in buildkite["state"]
assert "NO_TB4_CIRCLECI_PROMOTION_FROM_FREE_PLAN_DOCUMENTATION_ALONE" in frontier["hard_rules"]
assert "TB4_CIRCLECI_FREE_PLAN_ACCOUNT_AND_ZERO_CASE_PREFLIGHT_WHEN_ACCOUNT_ACCESS_IS_AVAILABLE" in frontier["runnable_zero_reality"]
assert "CIRCLECI_FREE_PLAN_XLARGE_GEN2_DISK_RUNTIME_AND_ALLOWANCE" in frontier["waiting_external_facts"]

def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 Project-Brain-Independent-Verifier"})
    with urllib.request.urlopen(request, timeout=45) as response:
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
assert "gen 2" in price
assert "48 credits/min" in price

print("ROOT2_FRONTIER_V3_CIRCLECI_V2_INDEPENDENT_PASS__SECOND_ORTHOGONAL_TB4_WAKE_ONLY__ZERO_CREDIT")
