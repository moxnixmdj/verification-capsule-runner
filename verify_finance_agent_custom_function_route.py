import hashlib
import html
import json
import pathlib
import re
import subprocess
import urllib.request
from html.parser import HTMLParser

BASE = "subject/finance_agent_custom_route_20261004_sol"
FILES = {
    "route": f"{BASE}/ROUTE.json",
    "intent": f"{BASE}/INTENT.json",
    "registry": f"{BASE}/REGISTRY.json",
    "guard": f"{BASE}/ZERO_SPEND_GUARD.json",
    "v6": f"{BASE}/ROOT2_V6.json",
}
EXPECTED = {
    "route": "79a60cb1c407fdabe68643ca91fcc2836ea000b1",
    "intent": "cd212b6474c90ff7191e677cd3e4a23c11ff66c5",
    "registry": "562536d9ba3f245a6bd24490a1eb3b30f27e0c3a",
    "guard": "278a3317564138088fd8af83a8734a84fe09b158",
    "v6": "fcbdb818b63b4986b026db29c400a47373a26fdb",
}
VALS_REPO_COMMIT = "502aab6fdaa3fb9294905c7453f89882baa8d39b"
VALS_README_BLOB = "6e18ea1e7149ba696e59c80e52890878aca8f096"

def committed_blob_sha(path):
    return subprocess.check_output(["git", "rev-parse", f"HEAD:{path}"], text=True).strip()

for key, path in FILES.items():
    got = committed_blob_sha(path)
    assert got == EXPECTED[key], (key, got, EXPECTED[key])

route = json.loads(pathlib.Path(FILES["route"]).read_text())
intent = json.loads(pathlib.Path(FILES["intent"]).read_text())
registry = json.loads(pathlib.Path(FILES["registry"]).read_text())
guard = json.loads(pathlib.Path(FILES["guard"]).read_text())
v6 = json.loads(pathlib.Path(FILES["v6"]).read_text())

# Frozen acceptance semantics.
pred = next(p for p in registry["predicates"] if p["id"] == "FINANCE_AGENT_V2_GE_58_59")
assert pred["kind"] == "PUBLIC_FIXED_BAR"
assert pred["acceptance"] == "Finance Agent v2 >= 58.59% on comparable Vals setup."
assert route["frozen_acceptance"] == pred["acceptance"]

# Exact subject bindings and zero-credit posture.
assert route["source_bindings"]["brain_root2_v6"]["git_blob_sha"] == EXPECTED["v6"]
assert route["source_bindings"]["zero_spend_guard"]["git_blob_sha"] == EXPECTED["guard"]
assert route["source_bindings"]["vals_finance_agent_repo"]["readme_git_blob_sha"] == VALS_README_BLOB
assert route["target_predicate"] == "FINANCE_AGENT_V2_GE_58_59"
assert "COMPARABILITY_OPEN" in route["status"]
assert "PLATFORM_ZERO_SPEND_OPEN" in route["status"]
for obj in (route, intent):
    assert obj["execution_authority"] is False
    assert obj["promotion_authority"] is False
    assert obj["fresh_reality_authority"] is False
    acct = obj["accounting"]
    for key in (
        "incremental_spend_usd", "new_reality_units_consumed", "terminal_cases_consumed",
        "acceptance_credit_delta", "family_credit_delta", "capability_credit_delta",
        "ownership_credit_delta",
    ):
        assert acct[key] == 0, (obj["schema"], key, acct[key])

# The existing default route remains valid and open. This candidate may not delete it.
default_route = route["route_graph"]["default_harness_route"]
custom_route = route["route_graph"]["custom_function_route"]
assert default_route["state"] == "OPEN"
assert custom_route["state"] == "CONDITIONALLY_OPEN"
assert "CUSTOM_FUNCTION_OR_CUSTOM_HARNESS_COMPARABILITY_TO_PUBLISHED_SHARED_DEFAULT_HARNESS_VERIFIED" in custom_route["requires"]
assert "VALS_PLATFORM_AND_EVALUATOR_JURY_ZERO_INCREMENTAL_SPEND_RECEIPT_OR_OWNER_NO_COST_ROUTE" in custom_route["requires"]
assert set(custom_route["potentially_deletes_if_comparability_verified"]) == {
    "DEFAULT_TAVILY_QUOTA_SUFFICIENCY_AS_MANDATORY_ROUTE",
    "DEFAULT_SEC_API_QUOTA_SUFFICIENCY_AS_MANDATORY_ROUTE",
    "DEFAULT_TIINGO_QUOTA_SUFFICIENCY_AS_MANDATORY_ROUTE",
}
for claim in (
    "NO_CLAIM_CUSTOM_FUNCTION_SCORE_IS_CURRENTLY_COMPARABLE",
    "NO_CLAIM_VALS_PLATFORM_EXECUTION_IS_FREE",
    "NO_CLAIM_DEFAULT_TOOL_PROVIDER_QUOTAS_ARE_DELETED_YET",
    "NO_BENCHMARK_CASE_EXECUTION",
    "NO_SCORE_OR_ACCEPTANCE_CREDIT",
    "NO_FRESH_REALITY_AUTHORITY",
):
    assert claim in route["hard_nonclaims"]

# Root2 V6 remains zero-credit and continues to carry the default-harness route.
assert v6["exact_state"]["accepted_families"] == 5
assert v6["exact_state"]["proved_atomic"] == 12
assert v6["exact_state"]["unresolved_atomic"] == 26
assert v6["execution_authority"] is False
assert v6["promotion_authority"] is False
assert v6["fresh_reality_authority"] is False
assert "FINANCE_AGENT_V2_1350_EXECUTION_TAVILY_SEC_API_TIINGO_FREE_USAGE_FEASIBILITY" in v6["waiting_external_facts"]

# Existing runtime guard is explicitly default-provider based and does not itself prove custom-route comparability.
assert guard["target_predicate"] == "FINANCE_AGENT_V2_GE_58_59"
assert set(guard["current_evidence"]["required_providers"]) == {"tavily", "sec_api", "tiingo"}
assert "NO_CLAIM_FREE_QUOTAS_ARE_SUFFICIENT_BEFORE_EXECUTION" in guard["hard_nonclaims"]

class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
    def handle_data(self, data):
        s = html.unescape(data).strip()
        if s:
            self.parts.append(s)
    def text(self):
        return re.sub(r"\s+", " ", " ".join(self.parts))

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "project-brain-independent-verifier/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()

def page_text(url):
    parser = TextExtractor()
    parser.feed(fetch(url).decode("utf-8", errors="replace"))
    return parser.text()

# Pin the public Finance Agent README and verify the exact harness/platform statements.
readme_url = f"https://raw.githubusercontent.com/vals-ai/finance-agent-v2/{VALS_REPO_COMMIT}/README.md"
readme = fetch(readme_url)
blob_sha = hashlib.sha1(b"blob " + str(len(readme)).encode() + b"\0" + readme).hexdigest()
assert blob_sha == VALS_README_BLOB, (blob_sha, VALS_README_BLOB)
readme_text = readme.decode("utf-8", errors="replace")
assert "Access to the Vals platform is gated and requires approval." in readme_text
assert 'add the "Test Suite IDs" to suites.json' in readme_text
assert "To run your own harness or model" in readme_text

# Live Vals SDK must still support arbitrary custom functions, not merely stock models.
sdk = page_text("https://docs.vals.ai/sdk/running_suites")
assert "Running with Custom Function" in sdk
assert "custom function" in sdk.lower()
assert "RAG pipelines" in sdk
assert "prompt chains" in sdk
assert "agentic behavior" in sdk
assert "Provide Outputs Directly" in sdk

# Live benchmark page must still identify the published bar as shared-default-harness evidence.
method = page_text("https://www.vals.ai/benchmarks/fabv2")
assert "shared default harness" in method.lower()
assert "six tools" in method.lower()
assert "two-hour time limit" in method.lower()
assert "Every model is run three times" in method
assert "Test (450 samples)" in method or ("Test" in method and "450 samples" in method)
assert "58.59%" in method
assert "Claude Opus 5.5" in method
assert "three-judge LLM jury" in method

# Core logic: existence != comparability. Candidate must retain both proof obligations.
assert "TAVILY_SEC_API_TIINGO_ARE_NOT_GENERIC_VALS_SDK_PLATFORM_REQUIREMENTS_FOR_ARBITRARY_SUITE_EXECUTION" in route["deductions"]
assert "THEREFORE_CUSTOM_FUNCTION_EXISTENCE_ALONE_DOES_NOT_PROVE_COMPARABILITY_TO_THE_FROZEN_58_59_BAR" in route["deductions"]
assert route["owner_clarification"]["state"] == "SENT__AWAITING_REPLY"

print("PASS: Vals SDK independently confirms arbitrary custom-function suite execution")
print("PASS: Finance Agent v2 independently remains a shared-default-harness 58.59% comparator")
print("PASS: alternative route exists, but comparability and Vals-platform zero-spend remain open")
print("PASS: no provider-quota deletion, no cases, no score, no acceptance credit, no fresh reality")
