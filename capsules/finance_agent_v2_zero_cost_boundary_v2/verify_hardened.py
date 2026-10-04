import base64, json, pathlib, re, subprocess, urllib.request, shutil, tempfile, time

SUBJECT="capsules/finance_agent_v2_zero_cost_boundary_v2/subject.json"
EXPECTED="2e9406243e3ef8b0b1d4c00889c1f93ccf1b7e2a"

def blob(path):
    return subprocess.check_output(["git","rev-parse",f"HEAD:{path}"],text=True).strip()
assert blob(SUBJECT)==EXPECTED
s=json.loads(pathlib.Path(SUBJECT).read_text())

def fetch(url):
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 Project-Brain-Independent-Verifier"})
    with urllib.request.urlopen(req,timeout=45) as r:
        return r.read().decode("utf-8","ignore")

def gh_blob(sha):
    d=json.loads(fetch("https://api.github.com/repos/vals-ai/finance-agent-v2/git/blobs/"+sha))
    assert d["sha"]==sha
    return base64.b64decode(d["content"]).decode("utf-8")

q=s["first_party_runner"]["public_question_file"]
assert len([x for x in gh_blob(q["git_blob_sha"]).splitlines() if x.strip()])==27
a=s["first_party_runner"]["agent_runtime"]
agent=gh_blob(a["git_blob_sha"])
assert "MAX_TIME_SECONDS = 2 * 60 * 60" in agent
assert "max_turns: int | None = None" in agent

def txt(html):
    return re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",html)).lower()

vals=txt(fetch("https://www.vals.ai/benchmarks/fabv2"))
assert "927 expert-reviewed questions" in vals
assert "public (27 open-source samples)" in vals
assert "private validation (450 samples" in vals
assert "test (450 samples)" in vals
assert "all results reported on this page are based solely on the test set" in vals
assert "two-hour time limit" in vals
assert "weighted checks" in vals and "dealbreakers" in vals

tavily=txt(fetch("https://www.tavily.com/pricing"))
assert "1,000 api credits" in tavily and "no credit card required" in tavily and "requests will stop" in tavily

# sec-api and Tiingo pricing are client-rendered for GitHub-hosted raw HTTP.
# Verify the exact first-party rendered pages rather than weakening either quota.
chrome=shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser")
assert chrome, "CHROMIUM_NOT_AVAILABLE"
def rendered(url):
    cmd=[chrome,"--headless=new","--no-sandbox","--disable-gpu","--disable-dev-shm-usage",
         "--virtual-time-budget=8000","--dump-dom",url]
    proc=subprocess.run(cmd,text=True,capture_output=True,timeout=45)
    assert proc.returncode==0,proc.stderr[-1000:]
    return txt(proc.stdout)

sec=rendered("https://sec-api.io/pricing")
assert re.search(r"(first\s+)?100\s+api\s+calls",sec) and "free" in sec
assert "free trial api key" in sec and re.search(r"100\s+calls\s+total",sec)

tiingo=rendered("https://www.tiingo.com/pricing")
assert "starter" in tiingo and re.search(r"\$0\s*/?\s*month",tiingo)
assert "unique symbols per month" in tiingo and "500" in tiingo
assert "max requests per hour" in tiingo and "50" in tiingo
assert "max requests per day" in tiingo and "1000" in tiingo
assert "max bandwidth per month" in tiingo and "1 gb" in tiingo

assert s["first_party_methodology"]["dataset_total_questions"]==927
assert s["first_party_methodology"]["splits"]=={"public":27,"private_validation":450,"test":450}
assert s["first_party_methodology"]["scored_population"]=="TEST"
assert s["first_party_methodology"]["reported_results_based_solely_on_test"] is True
assert "UNKNOWN_OFFICIAL_FINANCE_AGENT_V2_TEST_POPULATION_SIZE" in s["delete_as_blockers"]
assert "NO_CLAIM_FREE_QUOTAS_ARE_SUFFICIENT_FOR_OFFICIAL_TEST_450" in s["hard_nonclaims"]
assert s["accounting"]["incremental_spend_usd"]==0 and s["accounting"]["terminal_cases_consumed"]==0 and s["accounting"]["acceptance_credit_delta"]==0
assert s["execution_authority"] is False and s["promotion_authority"] is False and s["fresh_reality_authority"] is False
print("FINANCE_AGENT_V2_ZERO_COST_BOUNDARY_V2_PASS__TEST_450_CLOSED__PROVIDER_DEMAND_BOUNDS_OPEN__ZERO_CREDIT")
