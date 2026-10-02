from __future__ import annotations
import hashlib, json, pathlib, subprocess, sys

ROOT=pathlib.Path(__file__).resolve().parent
m=json.loads((ROOT/"EXPECTED_BRAIN_BLOBS.json").read_text(encoding="utf-8"))

def blob(path:pathlib.Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

for rel,expected in m["exact_brain_blobs"].items():
    actual=blob(ROOT/rel)
    assert actual==expected,(rel,actual,expected)

sys.path.insert(0,str(ROOT))
subprocess.run([
    sys.executable,"-m","unittest",
    "canonical.tests.test_p1_v6_derived_only_counterexample_v1","-v"
],cwd=ROOT,check=True)

from canonical.runtime.p1_v6_derived_only_counterexample_v1 import evaluate
out=evaluate()
assert out["status"]=="PASS__V6_DERIVED_ONLY_SCOPE_COUNTEREXAMPLE_CONFIRMED",out
assert out["derived_only_visible_failure"] is True,out
assert out["candidate_output"]["status"]=="IDENTIFIED",out
assert out["candidate_output"]["cause_action_id"]=="A1",out
assert out["candidate_output"]["repair_targets"]==["restore:A1:SCOPE"],out
assert out["forward_intervention"]["terminal_rescued"] is False,out
assert out["v6_scope_transport_falsified"] is True,out
assert out["terminal_results_replayed"]==0,out
assert out["new_reality_units_consumed"]==0,out
assert out["execution_authority"] is False,out
assert out["promotion_authority"] is False,out
print(json.dumps(out,indent=2,sort_keys=True))
