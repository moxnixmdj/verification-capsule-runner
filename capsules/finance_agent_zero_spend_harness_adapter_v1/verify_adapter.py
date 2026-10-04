#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))

from canonical.runtime import finance_agent_v2_zero_spend_harness_adapter_v1 as adapter

def blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

manifest=json.loads((ROOT/"EXPECTED_BRAIN_BLOBS.json").read_text())
for group in ("candidate_blobs","dependency_blobs"):
    for rel,expected in manifest[group].items():
        raw=(ROOT/rel).read_bytes()
        got=blob_sha(raw)
        assert got==expected,(group,rel,got,expected)

gov=json.loads((ROOT/"canonical/governance/FINANCE_AGENT_V2_ZERO_SPEND_HARNESS_ADAPTER_V1.json").read_text())
guardv=json.loads((ROOT/"canonical/verification/FINANCE_AGENT_V2_ZERO_SPEND_RUNTIME_GUARD_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json").read_text())
v6=json.loads((ROOT/"canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V6.json").read_text())

assert gov["adapter"]["runtime_git_blob_sha"]==manifest["candidate_blobs"]["canonical/runtime/finance_agent_v2_zero_spend_harness_adapter_v1.py"]
assert gov["adapter"]["tests_git_blob_sha"]==manifest["candidate_blobs"]["canonical/tests/test_finance_agent_v2_zero_spend_harness_adapter_v1.py"]
assert gov["verified_guard_dependency"]["verification_git_blob_sha"]==manifest["dependency_blobs"]["canonical/verification/FINANCE_AGENT_V2_ZERO_SPEND_RUNTIME_GUARD_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json"]
assert gov["current_root2"]["frontier_git_blob_sha"]==manifest["dependency_blobs"]["canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V6.json"]
assert guardv["independent_runner"]["conclusion"]=="success"
assert "FINANCE_AGENT_V2_1350_EXECUTION_TAVILY_SEC_API_TIINGO_FREE_USAGE_FEASIBILITY" in v6["waiting_external_facts"]

src=manifest["vals_source"]
base=f"https://raw.githubusercontent.com/{src['repository']}/{src['ref']}/"
downloaded={}
for key,path_key,sha_key in [
    ("tools","tools_path","tools_git_blob_sha"),
    ("get_agent","get_agent_path","get_agent_git_blob_sha"),
    ("run_agent","run_agent_path","run_agent_git_blob_sha"),
]:
    url=base+src[path_key]
    raw=urllib.request.urlopen(url,timeout=60).read()
    got=blob_sha(raw)
    assert got==src[sha_key],(key,got,src[sha_key])
    downloaded[key]=raw.decode("utf-8")

tools=downloaded["tools"]
get_agent=downloaded["get_agent"]
run_agent=downloaded["run_agent"]

assert adapter.PINNED_TOOLS_GIT_BLOB_SHA==src["tools_git_blob_sha"]
assert adapter.PINNED_GET_AGENT_GIT_BLOB_SHA==src["get_agent_git_blob_sha"]

# Exact provider topology in pinned source.
tav=tools[tools.index("class TavilyWebSearch"):tools.index("class EDGARSearch")]
edgar=tools[tools.index("class EDGARSearch"):tools.index("class ParseHtmlPage")]
price=tools[tools.index("class PriceHistory"):tools.index("class RetrieveInformation")]

assert tav.count("await self.client.search(")==1
assert "@retry_http_errors(429, 503, max_tries=8)" in tav

assert 'self.sec_api_url: str = "https://api.sec-api.io/full-text-search"' in edgar
assert edgar.count("session.post(")==1
assert "@retry_with_policy({429: 20, 503: 20})" in edgar

for host in (
    "https://api.tiingo.com/tiingo/daily/{ticker}/prices",
    "https://api.tiingo.com/tiingo/crypto/prices",
    "https://api.tiingo.com/tiingo/fx/{pair}/prices",
):
    assert host in price
assert price.count("session.get(")==1
assert "@retry_with_policy({429: 4, 503: 4})" in price

for binding in (
    '"web_search": TavilyWebSearch',
    '"edgar_search": EDGARSearch',
    '"price_history": PriceHistory',
):
    assert binding in get_agent
assert "selected_tools.append(tool_cls()" in get_agent
assert "MAX_TIME_SECONDS = 2 * 60 * 60" in get_agent
assert "max_turns: int | None = None" in get_agent

# The pinned runner uses get_agent for both single and parallel paths.
assert run_agent.count("get_agent(parameters") >= 2

# Adapter exact-host classifier rejects spoofed paths/domains.
assert adapter._provider_for_url("https://api.sec-api.io/full-text-search")=="sec_api"
assert adapter._provider_for_url("https://api.tiingo.com/tiingo/daily/AAPL/prices")=="tiingo"
assert adapter._provider_for_url("https://example.com/path/api.tiingo.com/prices") is None
assert adapter._provider_for_url("https://api.tiingo.com.evil/prices") is None

assert gov["accounting"]["incremental_spend_usd"]==0
assert gov["accounting"]["terminal_cases_consumed"]==0
assert gov["accounting"]["acceptance_credit_delta"]==0
assert gov["execution_authority"] is False
assert gov["promotion_authority"] is False
assert gov["fresh_reality_authority"] is False
assert "NO_CLAIM_LAUNCHER_BINDING_IS_ALREADY_INSTALLED" in gov["hard_nonclaims"]

print(json.dumps({
  "schema":"PROJECT_BRAIN_FINANCE_AGENT_ZERO_SPEND_HARNESS_ADAPTER_PUBLIC_RUNNER_RESULT_V1",
  "status":"PASS__EXACT_BLOBS__PINNED_VALS_SOURCE_TOPOLOGY__THREE_PROVIDER_NETWORK_PATHS_BOUND__RETRY_LAYER_GUARDED__ZERO_CREDIT",
  "pass":True,
  "verified":{
    "exact_candidate_and_dependency_blobs":True,
    "pinned_vals_tools_source":True,
    "pinned_vals_get_agent_source":True,
    "pinned_vals_run_agent_source":True,
    "tavily_actual_client_search_interception_point":True,
    "sec_api_actual_post_interception_point":True,
    "tiingo_actual_get_interception_point":True,
    "retry_decorators_reenter_intercepted_network_paths":True,
    "get_agent_instantiates_pinned_provider_tool_classes":True,
    "exact_hostname_spoof_resistance":True,
    "verified_guard_dependency":True,
    "launcher_binding_still_open":True,
    "zero_terminal_credit":True
  }
},indent=2,sort_keys=True))
