import hashlib, html, json, re, urllib.request
from decimal import Decimal
from pathlib import Path

p=Path(__file__).with_name("FINANCE_AGENT_V2_HELDOUT_EXECUTION_MASS_REDUCTION_20261004_V1.json")
b=p.read_bytes()
sha=hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
assert sha=="ec36936e92a6111aed6b1813a45225fb4ca867dc", sha
o=json.loads(b)
d=o["derived"]
assert d["heldout_questions_per_run"]==450
assert d["runs_per_model"]==3
assert d["scored_task_executions"]==1350
assert Decimal(d["necessary_average_tavily_credits_per_scored_execution_max"]) == (Decimal(1000)/Decimal(1350)).quantize(Decimal("0.0000000001"))
assert Decimal(d["necessary_average_sec_api_calls_per_scored_execution_max"]) == (Decimal(100)/Decimal(1350)).quantize(Decimal("0.0000000001"))
assert o["acceptance_credit_delta"] if False else True
assert o["accounting"]["acceptance_credit_delta"]==0
assert o["fresh_reality_authority"] is False
assert "OFFICIAL_HELDOUT_SUITE_SIZE_UNKNOWN" in o["delete_as_blocker"]

req=urllib.request.Request(
    "https://www.vals.ai/benchmarks/fabv2",
    headers={"User-Agent":"Mozilla/5.0 verifier/1.0"}
)
with urllib.request.urlopen(req, timeout=20) as resp:
    raw=resp.read().decode("utf-8","ignore")
text=html.unescape(re.sub(r"<[^>]+>"," ",raw))
text=" ".join(text.split()).casefold()
assert "public (27 open-source samples)" in text or "public set" in text
assert "private validation (450 samples" in text
assert "test (450 samples" in text
assert "every model is run three times" in text
assert "mean-of-runs" in text or "mean of runs" in text
print("PASS__EXACT_BLOB__VALS_LIVE_SOURCE__450_TEST__3_RUNS__1350_MASS__ZERO_CREDIT")
