import json
from pathlib import Path
R=Path(__file__).resolve().parent
def load(n): return json.loads((R/n).read_text())
act=load("CHARTOGRAPHY_ZERO_SPEND_GUARD_ACTIVATION_V1.json")
vr=load("CHARTOGRAPHY_ZERO_SPEND_GUARD_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json")
inv=load("ROOT2_FIXED_BAR_ROUTE_INVENTORY_V1.json")
gov=load("CHARTOGRAPHY_ZERO_SPEND_GUARD_V1.json")
assert act["control"]["verification_git_blob_sha"]=="d97fd0e5bae8fb103a539187b2cadf9b25457e5d"
assert vr["independent_runner"]["workflow_run_id"]==37163725050
assert vr["independent_runner"]["workflow_job_id"]==111322279817
assert vr["independent_runner"]["conclusion"]=="success"
assert vr["verified"]["minimum_judge_calls"]==1000
assert vr["verified"]["zero_credit_preserved"] is True
row=next(x for x in inv["routes"] if x["surface"]=="Chartography with tools")
assert "HARD_ZERO_SPEND_GUARD_INDEPENDENT_PASS" in row["state"]
assert row["zero_spend_guard"]["conclusion"]=="success"
assert row["zero_spend_guard"]["removed"]=="HARD_ZERO_SPEND_GUARD_IMPLEMENTATION_AND_VERIFICATION"
assert row["zero_spend_guard"]["remaining"]==[
 "PROJECT_SPECIFIC_GEMINI_3_5_FLASH_ACCESS_AND_CAPACITY_RECEIPT",
 "BRAIN_EVALUATION_ADAPTER",
 "BRAIN_SCORE_GE_89"]
assert "BIND_HARD_ZERO" not in row["next"]
assert gov["fresh_reality_authority"] is False
for o in (act,vr,gov,inv):
    assert o["incremental_spend_usd"]==0
    assert o["acceptance_credit_delta"]==0
    assert o["family_credit_delta"]==0
    assert o["capability_credit_delta"]==0
    assert o["ownership_credit_delta"]==0
print(json.dumps({"status":"PASS__CHARTOGRAPHY_ZERO_SPEND_GUARD_ACTIVATED__PROJECT_ACCOUNT_CAPACITY_ADAPTER_SCORE_REMAIN__ZERO_CREDIT","pass":True},sort_keys=True))
