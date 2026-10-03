from __future__ import annotations
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
EXPECTED={
"canonical/runtime/p1_v5_indistinguishability_counterexample_v1.py":"0c42687af6a1974d36e610203943e32e92f3ddef",
"canonical/tests/test_p1_v5_indistinguishability_counterexample_v1.py":"15673b8b3859b27210521c9c537d5ff6af5c6f9c",
"canonical/governance/P1_V5_INDISTINGUISHABILITY_COUNTEREXAMPLE_V1.json":"c1564488e966d3f4a73bb93d7377b4515cfbb650",
"canonical/runtime/trajectory_failure_typed_ir_candidate_v5.py":"2a8613ddac7402c7e6d2f349f9d3c32d3fb95e1d",
"canonical/runtime/trajectory_failure_typed_ir_proof_v5.py":"3fc600a8176dac250219e3d98b92cf93d8fceef5",
"canonical/governance/P1_TRAJECTORY_ABSOLUTE_TERMINAL_BINDING_V1.json":"e2fd56a5074e007506c151cfc81a2b3bca62b804",
"canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json":"8703c6aa08227467a619a7ae90d0d61f8e54da39",
"canonical/governance/P1_V5_DIRECT_SURFACE_SCOPE_SUPERSET_V1.json":"a25ab34f2bd2ee7f127ecdc572187d6f40fe7b13",
}
def blob(path):
 b=path.read_bytes()
 return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
for rel,want in EXPECTED.items():
 got=blob(ROOT/rel)
 assert got==want,(rel,got,want)
subprocess.run([sys.executable,"-m","unittest","canonical.tests.test_p1_v5_indistinguishability_counterexample_v1","-v"],cwd=ROOT,check=True)
sys.path.insert(0,str(ROOT))
from canonical.runtime import p1_v5_indistinguishability_counterexample_v1 as ce
out=ce.evaluate()
assert out["audit_valid"] is True,out
assert out["public_payloads_identical"] is True,out
assert out["correct_outputs_provably_different"] is True,out
assert out["v5_deterministic_output_identical"] is True,out
assert out["v5_passes_both_worlds"] is False,out
assert out["one_shot_unique_identification_possible_under_current_information_boundary"] is False,out
assert out["scope_superset_claim_falsified"] is True,out
assert out["new_reality_units_consumed"]==0,out
assert out["capability_credit_delta"]==0 and out["family_credit_delta"]==0,out
assert out["execution_authority"] is False and out["promotion_authority"] is False,out
print(json.dumps({
 "status":"PASS",
 "exact_brain_blob_count":len(EXPECTED),
 "declared_population_class":out["declared_population_class"],
 "public_payloads_identical":out["public_payloads_identical"],
 "correct_outputs_provably_different":out["correct_outputs_provably_different"],
 "v5_same_output":out["v5_deterministic_output_identical"],
 "v5_passes_both_worlds":out["v5_passes_both_worlds"],
 "one_shot_unique_identification_possible":out["one_shot_unique_identification_possible_under_current_information_boundary"],
 "scope_superset_claim_falsified":out["scope_superset_claim_falsified"],
 "new_reality_units_consumed":out["new_reality_units_consumed"],
 "credit_delta":0
},indent=2,sort_keys=True))
