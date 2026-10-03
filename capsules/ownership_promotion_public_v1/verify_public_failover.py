from __future__ import annotations
import hashlib, json, pathlib, subprocess, sys
ROOT=pathlib.Path(__file__).resolve().parent
EXPECTED={"SELF_VERIFICATION_DEBUGGING_AND_RECOVERY","SUBAGENT_DELEGATION_AND_COORDINATION","TOOL_DISCOVERY_SELECTION_AND_LEARNING"}

def run(cmd):
    p=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
    if p.returncode:
        print(p.stdout); print(p.stderr,file=sys.stderr); raise SystemExit(p.returncode)
    return p.stdout

m=json.loads((ROOT/"EXPECTED_BRAIN_BLOBS.json").read_text())
for rel,expected in m["exact_brain_blobs"].items():
    b=(ROOT/rel).read_bytes()
    got=hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
    assert got==expected,(rel,got,expected)

out1=json.loads(run([sys.executable,"canonical/runtime/ownership_promotion_compiler_v1.py"]))
assert out1["status"]=="PASS",out1
assert set(out1["promotion_eligible_families"])==EXPECTED,out1
assert out1["counts"]=={"eligible":3,"blocked":0},out1
assert out1["new_reality_units_consumed"]==0 and out1["incremental_spend_usd"]==0
for row in out1["families"]:
    assert row["status"]=="PROMOTION_ELIGIBLE_ZERO_REALITY",row
    assert row["provider_audit"]=="SELF_CONTAINED_STDLIB_ONLY",row
    assert row["errors"]==[],row

out2=json.loads(run([sys.executable,"canonical/runtime/ownership_promotion_independent_verifier_v1.py"]))
assert out2["status"]=="PASS",out2
assert out2["verified_family_count"]==3,out2
passed={x["family"] for x in out2["families"] if x["pass"]}
assert passed==EXPECTED,out2
assert out2["candidate_owned_count_before"]==2 and out2["candidate_owned_count_after"]==5
assert out2["new_reality_units_consumed"]==0 and out2["incremental_spend_usd"]==0
assert out2["promotion_authority"] is False
assert set(out1["promotion_eligible_families"])==passed
print(json.dumps({"status":"INDEPENDENT_PUBLIC_DUAL_IMPLEMENTATION_PASS","families":sorted(EXPECTED),"verified_owned_before":2,"verified_owned_after_if_promoted":5,"new_reality_units_consumed":0,"incremental_spend_usd":0,"promotion_authority":False},indent=2,sort_keys=True))
