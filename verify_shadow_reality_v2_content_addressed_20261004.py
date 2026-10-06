#!/usr/bin/env python3
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
P=ROOT/"subject"/"shadow_reality_v2_content_addressed_20261004"/"PROOF_CARRYING_SHADOW_REALITY_V2_CONTENT_ADDRESSED_ACTIVATION_V1.json"
EXPECTED="64eaf3d2e7f469fd5fee34afd5bb0cbeb874b278"

def blob(path):
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

assert blob(P)==EXPECTED
x=json.loads(P.read_text())

b=x["load_bearing_bindings"]
assert b["terminal_root"]["git_blob_sha"]=="36ac53134b123cfed7e63c31a871a30f9b4579e4"
assert b["runtime"]["git_blob_sha"]=="fd5639e9d503f59913bfbd08e47799ef5132b1e7"
assert b["policy"]["git_blob_sha"]=="756a608f0a3acaa72e56abbaa078f1cf0f3df938"
assert b["generic_isolation_activation"]["git_blob_sha"]=="89b3d8cbbc3b9e0822870ee803fb99c37a82d209"

r=x["current_root_truth"]
assert r=={
 "accepted_families":5,
 "open_families":14,
 "proved_atomic":12,
 "unresolved_atomic":26,
 "terminal":False,
 "root1_positive_gap_count":0,
}

p=x["proposed_effect"]
assert p["scheduling"] is True
assert p["per_route_shadow_collection"] is True
for k in ("result_release","acceptance_credit","promotion","global_fresh_reality_promotion"):
    assert p[k] is False

assert "UNRELATED_MAIN_COMMITS_DO_NOT_INVALIDATE" in x["validity_rule"]
assert "ANY_LOAD_BEARING_BLOB_DRIFT_INVALIDATES_FAIL_CLOSED" in x["validity_rule"]
assert x["active"] is False

for k,v in x["accounting"].items():
    assert v==0

print("PASS: content-addressed shadow reality activation preserves root truth and ignores only non-load-bearing main drift")
