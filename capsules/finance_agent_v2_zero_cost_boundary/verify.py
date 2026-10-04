import base64, json, pathlib, re, subprocess, urllib.request

SUBJECT="capsules/finance_agent_v2_zero_cost_boundary/subject.json"
EXPECTED_SUBJECT="032caa374280983945321f0a5706c0c665c097a6"

def committed_blob(path):
    return subprocess.check_output(["git","rev-parse",f"HEAD:{path}"],text=True).strip()

assert committed_blob(SUBJECT)==EXPECTED_SUBJECT
s=json.loads(pathlib.Path(SUBJECT).read_text())
assert s["target_predicate"]=="FINANCE_AGENT_V2_GE_58_59"
assert s["first_party_runner"]["repo"]=="vals-ai/finance-agent-v2"

def fetch(url):
    req=urllib.request.Request(url,headers={"User-Agent":"Project-Brain-Independent-Verifier"})
    with urllib.request.urlopen(req,timeout=45) as r:
        return r.read().decode("utf-8","ignore")

def github_blob(sha):
    data=json.loads(fetch("https://api.github.com/repos/vals-ai/finance-agent-v2/git/blobs/"+sha))
    assert data["sha"]==sha
    return base64.b64decode(data["content"]).decode("utf-8")

q=s["first_party_runner"]["public_question_file"]
questions=github_blob(q["git_blob_sha"])
assert len([x for x in questions.splitlines() if x.strip()])==27
assert q["public_question_count"]==27

a=s["first_party_runner"]["agent_runtime"]
agent=github_blob(a["git_blob_sha"])
assert "MAX_TIME_SECONDS = 2 * 60 * 60" in agent
assert "max_turns: int | None = None" in agent
assert "TurnLimit(max_turns=parameters.max_turns) if parameters.max_turns else None" in agent
assert a["max_time_seconds"]==7200
assert a["default_max_turns"] is None

def textify(html):
    return re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",html)).lower()

tavily=textify(fetch("https://www.tavily.com/pricing"))
sec=textify(fetch("https://sec-api.io/pricing"))
tiingo=textify(fetch("https://www.tiingo.com/pricing"))

assert "1,000 api credits" in tavily
assert "no credit card required" in tavily
assert "requests will stop" in tavily
assert "first 100 api calls" in sec and "free" in sec
assert "starter" in tiingo
assert "$0/month" in tiingo or "$0 / month" in tiingo
assert "50" in tiingo and "1000" in tiingo and "1 gb" in tiingo

assert "UNKNOWN_WHETHER_TAVILY_HAS_ANY_ZERO_COST_API_ROUTE" in s["delete_as_blockers"]
assert "UNKNOWN_WHETHER_SEC_API_HAS_ANY_ZERO_COST_API_ROUTE" in s["delete_as_blockers"]
assert "UNKNOWN_WHETHER_TIINGO_HAS_ANY_ZERO_COST_API_ROUTE" in s["delete_as_blockers"]
assert "NO_CLAIM_FREE_QUOTAS_ARE_SUFFICIENT_FOR_OFFICIAL_RUN" in s["hard_nonclaims"]
assert s["accounting"]["incremental_spend_usd"]==0
assert s["accounting"]["terminal_cases_consumed"]==0
assert s["accounting"]["acceptance_credit_delta"]==0
assert s["execution_authority"] is False
assert s["promotion_authority"] is False
assert s["fresh_reality_authority"] is False

print("FINANCE_AGENT_V2_ZERO_COST_TOOL_BOUNDARY_PASS__PROVIDER_EXISTENCE_ONLY__QUOTA_SUFFICIENCY_OPEN__ZERO_CREDIT")
