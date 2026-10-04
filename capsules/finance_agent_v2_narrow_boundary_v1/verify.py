#!/usr/bin/env python3
import base64, html, json, pathlib, re, subprocess, time, urllib.request

SUBJECT="capsules/finance_agent_v2_narrow_boundary_v1/subject.json"
EXPECTED="2e9406243e3ef8b0b1d4c00889c1f93ccf1b7e2a"

def committed_blob(path):
    return subprocess.check_output(["git","rev-parse",f"HEAD:{path}"], text=True).strip()

assert committed_blob(SUBJECT)==EXPECTED
s=json.loads(pathlib.Path(SUBJECT).read_text())
assert s["target_predicate"]=="FINANCE_AGENT_V2_GE_58_59"

def fetch(url, attempts=3):
    err=None
    for i in range(attempts):
        try:
            req=urllib.request.Request(url,headers={
                "User-Agent":"Mozilla/5.0 Project-Brain-Independent-Verifier",
                "Accept":"text/html,application/json,text/plain;q=0.9,*/*;q=0.8"
            })
            with urllib.request.urlopen(req,timeout=45) as r:
                return r.read().decode("utf-8","ignore")
        except Exception as e:
            err=e
            time.sleep(1+i)
    raise err

def textify(raw):
    return re.sub(r"\s+"," ",html.unescape(re.sub(r"<[^>]+>"," ",raw))).lower()

def gh_blob(sha):
    d=json.loads(fetch("https://api.github.com/repos/vals-ai/finance-agent-v2/git/blobs/"+sha))
    assert d["sha"]==sha
    return base64.b64decode(d["content"]).decode("utf-8")

# Exact first-party public-runner bytes.
q=s["first_party_runner"]["public_question_file"]
questions=gh_blob(q["git_blob_sha"])
assert len([x for x in questions.splitlines() if x.strip()])==27
a=s["first_party_runner"]["agent_runtime"]
agent=gh_blob(a["git_blob_sha"])
assert "MAX_TIME_SECONDS = 2 * 60 * 60" in agent
assert "max_turns: int | None = None" in agent
assert a["max_time_seconds"]==7200 and a["default_max_turns"] is None

# Vals first-party benchmark methodology. Verify only load-bearing Root2 facts.
vals=textify(fetch("https://www.vals.ai/benchmarks/fabv2"))
for token in [
    "927 expert-reviewed questions",
    "public (27 open-source samples)",
    "private validation (450 samples",
    "test (450 samples)",
    "all results reported on this page are based solely on the test set",
    "two-hour time limit",
    "weighted checks",
    "dealbreakers",
]:
    assert token in vals, "VALS:"+token

# Tavily: official help page is more stable than the dynamic pricing DOM.
tav=textify(fetch("https://help.tavily.com/articles/9170796666-how-can-i-create-an-api-key"))
assert "1,000 free api credits per month" in tav
assert "no credit card required" in tav

# SEC-API: official pricing page.
sec=textify(fetch("https://sec-api.io/pricing"))
assert re.search(r"100\s*api\s*calls",sec)
assert ("free tier" in sec or " free " in sec)

# Tiingo: first-party static blog gives the Starter limits without relying on dynamic pricing DOM.
tii=textify(fetch("https://www.tiingo.com/blog/scaling-investment-processes-through-a-stock-api/"))
assert "starter" in tii
assert "$0" in tii
assert ("50 requests/hour" in tii or "50 requests / hour" in tii or "50/hour" in tii)
assert ("1,000 requests/day" in tii or "1,000 requests / day" in tii or "1,000/day" in tii)
assert ("1gb" in tii or "1 gb" in tii)

# The narrow verified consequence: route existence + exact test size only.
expected_delete={
    "UNKNOWN_WHETHER_TAVILY_HAS_ANY_ZERO_COST_API_ROUTE",
    "UNKNOWN_WHETHER_SEC_API_HAS_ANY_ZERO_COST_API_ROUTE",
    "UNKNOWN_WHETHER_TIINGO_HAS_ANY_ZERO_COST_API_ROUTE",
    "UNKNOWN_OFFICIAL_FINANCE_AGENT_V2_TEST_POPULATION_SIZE",
}
assert expected_delete.issubset(set(s["delete_as_blockers"]))
assert s["first_party_methodology"]["dataset_total_questions"]==927
assert s["first_party_methodology"]["splits"]=={"public":27,"private_validation":450,"test":450}
assert s["first_party_methodology"]["scored_population"]=="TEST"
assert s["first_party_methodology"]["reported_results_based_solely_on_test"] is True

# Preserve exactly what is not proved.
assert "NO_CLAIM_FREE_QUOTAS_ARE_SUFFICIENT_FOR_OFFICIAL_TEST_450" in s["hard_nonclaims"]
assert "WORST_CASE_TAVILY_CREDIT_DEMAND_ACROSS_450_TEST_TASKS_WITHIN_FREE_CREDITS" in s["preserve"]
assert "WORST_CASE_SEC_API_CALL_DEMAND_ACROSS_450_TEST_TASKS_WITHIN_100_FREE_CALLS" in s["preserve"]
assert "WORST_CASE_TIINGO_SYMBOL_RATE_REQUEST_AND_BANDWIDTH_DEMAND_ACROSS_450_TEST_TASKS_WITHIN_STARTER_LIMITS" in s["preserve"]
assert s["accounting"]["incremental_spend_usd"]==0
assert s["accounting"]["terminal_cases_consumed"]==0
assert s["accounting"]["acceptance_credit_delta"]==0
assert s["execution_authority"] is False
assert s["promotion_authority"] is False
assert s["fresh_reality_authority"] is False

print("FINANCE_AGENT_V2_NARROW_BOUNDARY_PASS__TEST_450_AND_ZERO_COST_ROUTE_EXISTENCE_ONLY__QUOTA_SUFFICIENCY_OPEN__ZERO_CREDIT")
