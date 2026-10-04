import hashlib
import json
import pathlib
import re
import subprocess
import urllib.request
from html.parser import HTMLParser

FILES = {
    "frontier": "subject/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V4.json",
    "circleci": "subject/TB4_CIRCLECI_FREE_XLARGE_CONTRADICTION_RECONCILIATION_20261004_V1.json",
    "vals": "subject/FINANCE_AGENT_V2_PUBLIC_RUNNER_ROUTE_RECONCILIATION_20261004_V1.json",
    "intent": "subject/2026-10-04_ROOT2_FRONTIER_V4_TRUTH_REPAIR_V1.json",
}
EXPECTED = {
    "frontier": "2df366e1794fdd05fc64f1f52917f1c8725b1de0",
    "circleci": "0c5d16da02e7a71c5583f7c1a743adf389fc47b1",
    "vals": "126ff389982aab89f810388b1adbe402c25a7a59",
    "intent": "f093a5c9354186b2e3f53b329d61dbf3bbe4f96a",
}
VALS_COMMIT = "502aab6fdaa3fb9294905c7453f89882baa8d39b"
VALS_README_BLOB = "6e18ea1e7149ba696e59c80e52890878aca8f096"

def committed_blob_sha(path):
    return subprocess.check_output(["git", "rev-parse", f"HEAD:{path}"], text=True).strip()

for key, path in FILES.items():
    got = committed_blob_sha(path)
    assert got == EXPECTED[key], (key, got, EXPECTED[key])

frontier = json.loads(pathlib.Path(FILES["frontier"]).read_text())
circleci = json.loads(pathlib.Path(FILES["circleci"]).read_text())
vals = json.loads(pathlib.Path(FILES["vals"]).read_text())
intent = json.loads(pathlib.Path(FILES["intent"]).read_text())

# Frozen terminal accounting must not drift.
state = frontier["exact_state"]
assert state == {
    "accepted_families": 5,
    "open_families": 14,
    "proved_atomic": 12,
    "unresolved_atomic": 26,
    "root1_positive_gap_count": 0,
    "root2_only_count": 16,
    "root3_only_count": 7,
    "root2_and_root3_count": 3,
    "root2_touching_predicates": 19,
}
for obj in (frontier, circleci, vals, intent):
    assert obj["execution_authority"] is False
    assert obj["promotion_authority"] is False
    assert obj["fresh_reality_authority"] is False

# Exact causal bindings.
assert frontier["source_bindings"]["circleci_contradiction_reconciliation"]["git_blob_sha"] == EXPECTED["circleci"]
assert frontier["source_bindings"]["finance_agent_v2_public_runner"]["git_blob_sha"] == EXPECTED["vals"]
assert frontier["source_bindings"]["action_intent"]["git_blob_sha"] == EXPECTED["intent"]
providers = [x["provider"] for x in frontier["tb4_carrier_portfolio"]["candidates"]]
assert providers == ["Buildkite"], providers
deleted = {x["provider"]: x["reason"] for x in frontier["tb4_carrier_portfolio"]["deleted"]}
assert "CircleCI" in deleted
assert "8_VCPU" in deleted["CircleCI"]
assert circleci["conclusion"]["current_circleci_free_xlarge_route_killed"] is True
assert circleci["conclusion"]["circleci_xlarge_gen2_free"] is False
assert circleci["conclusion"]["documented_free_route_meets_tb4_8cpu_envelope"] is False

# Finance Agent v2 must be route compression only, never score credit.
assert "CUSTOM_MODEL_OR_HARNESS_CAN_BE_BOUND_VIA_GET_CUSTOM_MODEL" in vals["proved_by_first_party_readme"]
assert "USER_CURRENTLY_HAS_VALS_PLATFORM_APPROVAL" in vals["not_proved"]
assert "BRAIN_SCORE_GE_58_59" in vals["not_proved"]
assert vals["route_reduction"]["owner_run_receipt_remains_valid_alternative"] is True
assert any("FINANCE_AGENT_V2_VALS_PLATFORM_APPROVAL" in x for x in frontier["runnable_zero_reality"])
assert "VALS_MYSTERYMECHANISM_OWNER_OR_EXACT_ROUTE_RESULT" in frontier["waiting_external_facts"]

# All accounting remains zero.
for obj in (frontier, circleci, vals, intent):
    acct = obj["accounting"]
    for k in ("incremental_spend_usd", "new_reality_units_consumed", "terminal_cases_consumed",
              "acceptance_credit_delta", "family_credit_delta", "capability_credit_delta",
              "ownership_credit_delta"):
        assert acct[k] == 0, (obj["schema"], k, acct[k])

class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
    def handle_data(self, data):
        if data.strip():
            self.parts.append(data.strip())
    def text(self):
        return " ".join(self.parts)

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "project-brain-independent-verifier/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()

def html_text(data):
    p = TextExtractor()
    p.feed(data.decode("utf-8", errors="replace"))
    return re.sub(r"\s+", " ", p.text())

# Independent live CircleCI source check.
changelog = html_text(fetch("https://circleci.com/changelog/"))
assert "Gen2 x86 Docker resource classes now available on Free plans" in changelog
assert "Gen2 x86 Docker resource classes" in changelog and "available to Free plan users" in changelog

pricing = html_text(fetch("https://circleci.com/pricing/"))
start = pricing.find("(x86) Docker (Gen 2)")
end = pricing.find("(Arm) Docker", start)
assert start >= 0 and end > start, (start, end)
gen2 = pricing[start:end]
# Current table semantics: Free/Performance/Scale, Large is Yes/Yes/Yes, X-large is unavailable/Yes/Yes.
assert re.search(r"Large\s+Yes\s+Yes\s+Yes", gen2), gen2[:1200]
assert re.search(r"X-large\s+(?:—|-|–)\s+Yes\s+Yes", gen2), gen2[:1200]

# Independent pinned Vals first-party check.
vals_url = f"https://raw.githubusercontent.com/vals-ai/finance-agent-v2/{VALS_COMMIT}/README.md"
vals_readme = fetch(vals_url)
blob_sha = hashlib.sha1(b"blob " + str(len(vals_readme)).encode() + b"\0" + vals_readme).hexdigest()
assert blob_sha == VALS_README_BLOB, (blob_sha, VALS_README_BLOB)
vals_text = vals_readme.decode("utf-8")
assert "Access to the Vals platform is gated and requires approval." in vals_text
assert 'add the "Test Suite IDs" to suites.json' in vals_text
assert "To run your own harness or model, just modify the `get_custom_model` function as needed." in vals_text
assert "data/public.txt" in vals_text

print("PASS: Root2 frontier V4 truth repair independently verified")
print("PASS: CircleCI Free Gen2 general availability does not include X-large in current plan table")
print("PASS: Vals Finance Agent v2 public custom-harness route pinned; gated suite access remains open")
print("PASS: 5/19 accepted, 12/38 proved, 26 unresolved; zero credit and no fresh-reality authority")
