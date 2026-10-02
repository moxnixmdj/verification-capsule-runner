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
    "canonical.tests.test_p1_zero_reality_exhaustion_gate_v1","-v"
],cwd=ROOT,check=True)

from canonical.runtime import p1_zero_reality_exhaustion_gate_v1 as gate
out=gate.evaluate()
assert str(out.get("status","")).startswith("PASS"),out
assert out["zero_reality_fixed_point_reached"] is True,out
assert out["can_clear_p1_scope_quarantine"] is False,out
assert set(out["residual_obligations"])==set(m["expected_residuals"]),out
assert out["new_reality_units_consumed"]==0,out
assert out["terminal_results_replayed"]==0,out
assert out["capability_credit_delta"]==0,out
assert out["family_credit_delta"]==0,out
assert out["execution_authority"] is False,out
assert out["promotion_authority"] is False,out
cut=out["next_proof_cut"]
assert cut["new_reality_authorized"] is False,cut
must=set(cut["must_jointly_verify"])
assert "EXPLICIT_SCOPE_FAILURE_IS_A_FIRST_CLASS_MECHANISM" in must
assert "HETEROGENEOUS_DELAYED_AND_INTERACTION_INTERVENTION_RESCUE" in must
assert "SCOPE_RELATION_TO_ALL_THREE_DECLARED_P1_DIRECT_SURFACES_IS_EXACT_OR_SUPERSET" in must
print(json.dumps({
    "status":"PASS",
    "residual_obligations":out["residual_obligations"],
    "zero_reality_fixed_point_reached":True,
    "can_clear_p1_scope_quarantine":False,
    "new_reality_authorized":False,
    "zero_credit":True
},indent=2,sort_keys=True))
