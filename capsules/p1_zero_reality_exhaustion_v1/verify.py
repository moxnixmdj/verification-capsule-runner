from __future__ import annotations
import hashlib,json,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parent
m=json.loads((ROOT/"EXPECTED_BRAIN_BLOBS.json").read_text())
def blob(p):
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
for rel,expected in m["exact_brain_blobs"].items():
    actual=blob(ROOT/rel)
    assert actual==expected,(rel,actual,expected)
sys.path.insert(0,str(ROOT))
subprocess.run([sys.executable,"-m","py_compile",str(ROOT/"canonical/runtime/p1_zero_reality_exhaustion_gate_v1.py")],check=True)
subprocess.run([sys.executable,"-m","unittest","canonical.tests.test_p1_zero_reality_exhaustion_gate_v1","-v"],cwd=ROOT,check=True)
from canonical.runtime import p1_zero_reality_exhaustion_gate_v1 as gate
out=gate.evaluate()
assert out["status"]=="PASS__P1_ZERO_REALITY_EVIDENCE_EXHAUSTED__TWO_TERMINAL_SCOPE_RESIDUALS_REMAIN",out
assert out["zero_reality_fixed_point_reached"] is True
assert out["can_clear_p1_scope_quarantine"] is False
assert set(out["residual_obligations"])=={"P1_EXPLICIT_SCOPE_FAILURE_CLASS","P1_HETEROGENEOUS_INTERVENTION_RESCUE"}
assert out["next_proof_cut"]["new_reality_authorized"] is False
assert out["terminal_results_replayed"]==0
assert out["new_reality_units_consumed"]==0
print(json.dumps(out,indent=2,sort_keys=True))
