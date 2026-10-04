#!/usr/bin/env python3
import hashlib, json
from pathlib import Path

R=Path(__file__).resolve().parent
def blob(p):
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

m=json.loads((R/"EXPECTED.json").read_text())
for name,expected in m["exact_blobs"].items():
    got=blob(R/name)
    assert got==expected,(name,got,expected)

cut=json.loads((R/"CURRENT_ZERO_REALITY_MINIMUM_CUT_V9.json").read_text())
inv=json.loads((R/"ROOT2_FIXED_BAR_ROUTE_INVENTORY_V1.json").read_text())
front=json.loads((R/"ROOT2_ROOT3_MINIMUM_EXECUTION_FRONTIER_V1.json").read_text())
r3=json.loads((R/"ROOT3_RESIDUAL_COMPRESSION_V1.json").read_text())

s=cut["exact_state"]
assert (s["root2_only_count"],s["root3_only_count"],s["root2_and_root3_count"])==(16,7,3)
assert s["unresolved_atomic"]==26 and s["root2_unique_benchmark_surfaces"]==14
fs=front["exact_state"]
assert (fs["root2_only_count"],fs["root3_only_count"],fs["root2_and_root3_count"])==(16,7,3)
assert "SYNTHESIS_SCOPE_RECLASSIFIED_TO_ROOT2_ONLY" in r3["status"]

assert cut["authority"]["root2_routes"]["git_blob_sha"]==m["exact_blobs"]["ROOT2_FIXED_BAR_ROUTE_INVENTORY_V1.json"]
assert cut["authority"]["minimum_frontier"]["git_blob_sha"]==m["exact_blobs"]["ROOT2_ROOT3_MINIMUM_EXECUTION_FRONTIER_V1.json"]
assert cut["authority"]["root3_compression"]["git_blob_sha"]==m["exact_blobs"]["ROOT3_RESIDUAL_COMPRESSION_V1.json"]

active=cut["active_zero_reality_work"]
assert len(active)==6
joined="\n".join(x["work"] for x in active)
assert "GITLAB_EXACT_REVISION" not in joined
assert "BIND_HARD_ZERO_SPEND_GUARD" not in joined
assert any(x["surface"]=="Communication and Synthesis" and "ROOT2_ONLY" in x["work"] for x in active)
assert any(x["surface"]=="Chartography with tools" and "SEMANTIC_EVALUATION_ADAPTER" in x["work"] for x in active)

events={x["event_class"] for x in cut["external_event_dependencies"]}
assert events=={
 "OWNER_REPLY_OR_OWNER_EVALUATION_ACCESS",
 "CHARTOGRAPHY_PROJECT_ACCOUNT_CAPACITY",
 "HUGGINGFACE_GATED_ACCOUNT_ACCESS",
 "TB4_CARRIER_STATE_CHANGE",
 "CURSOR_POLICY_CHANGE"
}
assert set(cut["preserved_for_minimum_reality_execution"])=={
 "LIVEBENCH_IF_GE_65_7__ROUTE_COMPLETE_TO_BRAIN_SCORE_ONLY",
 "TB_SCIENCE_GE_58_7__ROUTE_COMPLETE_TO_BRAIN_SCORE_ONLY"
}

assert cut["new_reality_units_consumed"]==0
assert cut["terminal_cases_consumed"]==0
assert cut["incremental_spend_usd"]==0
assert cut["acceptance_credit_delta"]==0
assert cut["family_credit_delta"]==0
assert cut["capability_credit_delta"]==0
assert cut["ownership_credit_delta"]==0
assert cut["execution_authority"] is False
assert cut["promotion_authority"] is False
assert cut["fresh_reality_authority"] is False

assert "CHARTOGRAPHY_ZERO_SPEND_GUARD_DISCHARGED" in inv["status"]
assert "OSWORLD_GITLAB_REVISION_DELETED" in inv["status"]

print(json.dumps({
 "schema":"PROJECT_BRAIN_ROOT2_MINCUT_V9_CURRENT_PUBLIC_RUNNER_RESULT_V1",
 "pass":True,
 "status":"PASS__EXACT_CURRENT_BLOBS__16_7_3_PARTITION__SIX_ACTIVE_ZERO_REALITY_STREAMS__EXTERNAL_EVENTS_SEPARATED__SCORE_ONLY_ROUTES_PRESERVED__ZERO_CREDIT"
},sort_keys=True))
