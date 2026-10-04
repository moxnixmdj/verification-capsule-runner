import hashlib, json, pathlib, re, urllib.request
p=pathlib.Path("capsules/tb4_buildkite_documentary_reduction/subject.json")
b=p.read_bytes()
assert hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()=="2997d7f95227d024a55aa201b3fced53f85a01e8"
j=json.loads(p.read_text())
assert j["derived_bounds"]["single_large_agent_wall_minutes_equivalent"]==500
def fetch(u):
    req=urllib.request.Request(u,headers={"User-Agent":"Project-Brain-Independent-Verifier"})
    with urllib.request.urlopen(req,timeout=30) as r:
        return re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",r.read().decode("utf-8","ignore")))
q=fetch("https://buildkite.com/docs/agent/queues/managing")
l=fetch("https://buildkite.com/docs/agent/buildkite-hosted/linux")
m=fetch("https://buildkite.com/docs/platform/limits")
p0=fetch("https://buildkite.com/pricing/")
for token in ["linux-large","Large","LINUX_AMD64_8X32"]:
    assert token.lower() in q.lower() or token.lower() in l.lower(), token
for token in ["8","32 GB","158 GB"]:
    assert token.lower() in l.lower(), token
for token in ["All Access Trial","24 vCPU","4,000 included"]:
    assert token.lower() in m.lower(), token
for token in ["No credit card","Hosted Agents"]:
    assert token.lower() in p0.lower(), token
assert j["accounting"]["incremental_spend_usd"]==0
assert "NO_CARRIER_ADMISSIBILITY_CLAIM" in j["hard_nonclaims"]
print("TB4_BUILDKITE_DOCUMENTARY_REDUCTION_PUBLIC_RUNNER_PASS__ZERO_CREDIT")
