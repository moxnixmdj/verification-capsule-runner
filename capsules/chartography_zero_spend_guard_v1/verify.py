#!/usr/bin/env python3
import hashlib, json, sys, urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from canonical.runtime import chartography_zero_spend_guard_v1 as g

def blob(p):
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

m=json.loads((ROOT/"EXPECTED.json").read_text())
for rel,expected in m["exact_brain_blobs"].items():
    assert blob(ROOT/rel)==expected,(rel,blob(ROOT/rel),expected)

u=m["official_chartography"]
url=f"https://raw.githubusercontent.com/{u['repository']}/{u['commit']}/{u['path']}"
with urllib.request.urlopen(url,timeout=30) as r:
    raw=r.read()
assert hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()==u["git_blob_sha"]
assert f'DEFAULT_JUDGE_MODEL = "{u["expected_judge_model"]}"' in raw.decode()

gov=json.loads((ROOT/"canonical/governance/CHARTOGRAPHY_ZERO_SPEND_GUARD_V1.json").read_text())
assert gov["frozen_protocol"]["minimum_judge_calls"]==1000
assert gov["frozen_protocol"]["judge_model"]=="google/gemini-3.5-flash"
assert gov["incremental_spend_usd"]==0
assert gov["fresh_reality_authority"] is False
assert gov["acceptance_credit_delta"]==0

base={
 "receipt_verified":True,
 "model_id":"google/gemini-3.5-flash",
 "model_access":True,
 "free_tier_active":True,
 "paid_fallback_enabled":False,
 "overage_enabled":False,
 "incremental_spend_usd":0,
 "project_hash":"0123456789abcdef0123456789abcdef",
 "verified_free_call_capacity":1100
}
assert g.authorize_plan(base,required_calls=1000,retry_reserve=100)["status"].startswith("PASS__")
for mutation in [
 {"receipt_verified":False},
 {"model_id":"wrong"},
 {"paid_fallback_enabled":True},
 {"overage_enabled":True},
 {"incremental_spend_usd":"0.01"},
 {"verified_free_call_capacity":999},
]:
    s=dict(base); s.update(mutation)
    try:
        g.authorize_plan(s,required_calls=1000)
    except g.ZeroSpendBlocked:
        pass
    else:
        raise AssertionError(mutation)

try:
    g.authorize_next_call(dict(base,verified_free_call_capacity=1000),successful_calls=500,attempted_calls=520,retry_reserve_remaining=1)
except g.ZeroSpendBlocked:
    pass
else:
    raise AssertionError("eroded capacity must fail")

print(json.dumps({
 "schema":"PROJECT_BRAIN_CHARTOGRAPHY_ZERO_SPEND_GUARD_PUBLIC_RUNNER_RESULT_V1",
 "pass":True,
 "status":"PASS__EXACT_BLOBS__EXACT_JUDGE_MODEL__1000_CALL_FLOOR__FAIL_CLOSED_ZERO_SPEND__ZERO_CREDIT"
},sort_keys=True))
