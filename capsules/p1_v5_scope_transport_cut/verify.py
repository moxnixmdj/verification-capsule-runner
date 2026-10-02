from __future__ import annotations
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
EXPECTED={
"canonical/runtime/p1_v5_scope_transport_cut_v1.py":"70d703fcfb61c544ba006083964054cfefc00507",
"canonical/tests/test_p1_v5_scope_transport_cut_v1.py":"fc54fd4be51bd600c506f4b55e9bac07298c85f7",
"canonical/governance/P1_V5_SCOPE_TRANSPORT_CUT_V1.json":"82aba92399b9145bcc496f85035933c148a1ef6b",
"canonical/verification/P1_TYPED_INTERVENTION_V5_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json":"89fb2e7e3e246b058cc5f5108f23e28606936df7",
"canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json":"8703c6aa08227467a619a7ae90d0d61f8e54da39",
"canonical/governance/P1_TERMINAL_EXECUTION_SCOPE_MISMATCH_QUARANTINE_V1.json":"f4fe68c78ccdf5392b5e24519ae9a57e620221a7",
"canonical/verification/P1_V4_SCOPE_SAFE_RESIDUAL_DISCHARGE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json":"4dd7cf140e2a5d1c01cfd589d9fb8a69ec4fa24a",
}
def blob(p):
 b=p.read_bytes()
 return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
for rel,want in EXPECTED.items():
 got=blob(ROOT/rel); assert got==want,(rel,got,want)
subprocess.run([sys.executable,"-m","unittest","canonical.tests.test_p1_v5_scope_transport_cut_v1","-v"],cwd=ROOT,check=True)
sys.path.insert(0,str(ROOT))
from canonical.runtime import p1_v5_scope_transport_cut_v1 as cut
out=cut.evaluate()
assert out["status"].startswith("PASS__V5_MECHANISM_RESIDUALS_DISCHARGED")
assert out["transport_atom_count"]==3
assert len(out["transport_atoms"])==3
assert out["can_clear_p1_scope_quarantine"] is False
assert out["next_proof_cut"]["full_terminal_replay_authorized"] is False
assert out["new_reality_units_consumed"]==0
assert out["capability_credit_delta"]==0
assert out["family_credit_delta"]==0
assert out["execution_authority"] is False
assert out["promotion_authority"] is False
print(json.dumps({
 "status":"PASS",
 "exact_brain_blob_count":len(EXPECTED),
 "transport_atom_count":out["transport_atom_count"],
 "transport_surfaces":[x["surface"] for x in out["transport_atoms"]],
 "p1_quarantine_cleared":out["can_clear_p1_scope_quarantine"],
 "full_terminal_replay_authorized":out["next_proof_cut"]["full_terminal_replay_authorized"],
 "new_reality_units_consumed":out["new_reality_units_consumed"],
 "credit_delta":0
},indent=2,sort_keys=True))
