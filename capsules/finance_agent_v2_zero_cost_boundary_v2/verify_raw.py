import hashlib, json, pathlib, re, subprocess, urllib.request

SUBJECT="capsules/finance_agent_v2_zero_cost_boundary_v2/subject.json"
EXPECTED="b7ba653977771df8312fd140cf4b563bcc4e21e4"
VALS_COMMIT="502aab6fdaa3fb9294905c7453f89882baa8d39b"

def committed_blob(path):
    return subprocess.check_output(["git","rev-parse",f"HEAD:{path}"],text=True).strip()
assert committed_blob(SUBJECT)==EXPECTED
s=json.loads(pathlib.Path(SUBJECT).read_text())

def fetch_bytes(url):
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 Project-Brain-Independent-Verifier"})
    with urllib.request.urlopen(req,timeout=45) as r:
        return r.read()

def fetch(url):
    return fetch_bytes(url).decode("utf-8","ignore")

def git_blob_sha(data):
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

q=s["first_party_runner"]["public_question_file"]
qbytes=fetch_bytes(f"https://raw.githubusercontent.com/vals-ai/finance-agent-v2/{VALS_COMMIT}/data/public.txt")
assert git_blob_sha(qbytes)==q["git_blob_sha"]
assert len([x for x in qbytes.decode().splitlines() if x.strip()])==27

a=s["first_party_runner"]["agent_runtime"]
abytes=fetch_bytes(f"https://raw.githubusercontent.com/vals-ai/finance-agent-v2/{VALS_COMMIT}/finance_agent/get_agent.py")
assert git_blob_sha(abytes)==a["git_blob_sha"]
agent=abytes.decode()
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
sec=txt(fetch("https://sec-api.io/"))
tiingo=txt(fetch("https://www.tiingo.com/pricing"))
assert "1,000 api credits" in tavily and "no credit card required" in tavily and "requests will stop" in tavily
assert "no credit card is required" in sec and "free tier covers every endpoint" in sec
assert "starter" in tiingo and ("$0/month" in tiingo or "$0 / month" in tiingo)
assert "500" in tiingo and "50" in tiingo and "1000" in tiingo and "1 gb" in tiingo

assert s["first_party_methodology"]["dataset_total_questions"]==927
assert s["first_party_methodology"]["splits"]=={"public":27,"private_validation":450,"test":450}
assert s["first_party_methodology"]["scored_population"]=="TEST"
assert s["first_party_methodology"]["reported_results_based_solely_on_test"] is True
assert "UNKNOWN_OFFICIAL_FINANCE_AGENT_V2_TEST_POPULATION_SIZE" in s["delete_as_blockers"]
assert "NO_CLAIM_FREE_QUOTAS_ARE_SUFFICIENT_FOR_OFFICIAL_TEST_450" in s["hard_nonclaims"]
assert s["accounting"]["incremental_spend_usd"]==0 and s["accounting"]["terminal_cases_consumed"]==0 and s["accounting"]["acceptance_credit_delta"]==0
assert s["execution_authority"] is False and s["promotion_authority"] is False and s["fresh_reality_authority"] is False
print("FINANCE_AGENT_V2_ZERO_COST_BOUNDARY_V2_RAW_PASS__TEST_450_CLOSED__PROVIDER_DEMAND_BOUNDS_OPEN__ZERO_CREDIT")
