from __future__ import annotations
import hashlib, json, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
EXPECTED={
 "canonical/runtime/p1_v5_direct_surface_scope_superset_v1.py":"7eea82aa47585030db01f9df0d49006f499bd196",
 "canonical/tests/test_p1_v5_direct_surface_scope_superset_v1.py":"2a0901705d8f3e5427b19993177e7e92ce0a807a",
 "canonical/governance/P1_V5_DIRECT_SURFACE_SCOPE_SUPERSET_V1.json":"329d157a991a0da64fa815122ca139a391ee1b54",
 "canonical/runtime/trajectory_failure_typed_ir_candidate_v5.py":"2a8613ddac7402c7e6d2f349f9d3c32d3fb95e1d",
 "canonical/runtime/trajectory_failure_typed_ir_proof_v5.py":"3fc600a8176dac250219e3d98b92cf93d8fceef5",
 "canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json":"8703c6aa08227467a619a7ae90d0d61f8e54da39",
 "canonical/governance/TERMINAL_PORTFOLIO_BINDING_MANIFESTS_V1.json":"8b439403a05b4a912f06a8866db25f6e53b52473",
 "canonical/governance/CONTRACT_NATIVE_PRIVATE_SURFACE_PROOF_ROUTES_V1.json":"75cd1ad0ec0739ebd894cf6075af5837b93d83f8",
 "canonical/governance/FOUR_UNCOVERED_BEHAVIORAL_PROOF_CONTRACTS_V1.json":"8c7ffe3d9ff789eddd286496f6de3ce84472c909",
 "canonical/verification/P1_V4_SCOPE_SAFE_RESIDUAL_DISCHARGE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json":"4dd7cf140e2a5d1c01cfd589d9fb8a69ec4fa24a",
 "canonical/verification/P1_TYPED_INTERVENTION_ENVELOPE_V5_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json":"9221744bafba669a8b596e2fcce63d4a5537654b",
 "canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json":"bd86b4c53992b47a4a60b64a60ba03db9a442cfc",
}
def blob(path:Path)->str:
 b=path.read_bytes()
 return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
for rel,want in EXPECTED.items():
 got=blob(ROOT/rel)
 assert got==want,(rel,got,want)

subprocess.run(
 [sys.executable,"-m","unittest","canonical.tests.test_p1_v5_direct_surface_scope_superset_v1","-v"],
 cwd=ROOT,check=True
)
sys.path.insert(0,str(ROOT))
from canonical.runtime import p1_v5_direct_surface_scope_superset_v1 as gate
out=gate.evaluate()
assert out["pass"] is True,out
assert out["surface_count"]==3,out
assert out["mutation_audit"]["all_frozen_mutations_killed"] is True,out
assert out["mutation_audit"]["mutation_count"]==9,out
assert all(out["mutation_audit"]["results"].values()),out
assert out["scope_relation"]=="SUPERSET_OF_FROZEN_P1_DIRECT_PROOF_CONTRACT_SEMANTICS_BOUND_TO_ALL_THREE_DECLARED_SURFACES",out
assert out["private_benchmark_population_scope_claimed"] is False,out
assert out["quarantine_lift_eligible"] is False,out
assert out["terminal_receipts_preserved"]["terminal_results_replayed"]==0,out
assert out["new_reality_units_consumed"]==0,out
assert out["capability_credit_delta"]==0 and out["family_credit_delta"]==0,out
print(json.dumps({
 "status":"PASS",
 "exact_brain_blob_count":len(EXPECTED),
 "surface_count":out["surface_count"],
 "scope_relation":out["scope_relation"],
 "frozen_mutation_count":out["mutation_audit"]["mutation_count"],
 "all_frozen_mutations_killed":out["mutation_audit"]["all_frozen_mutations_killed"],
 "private_benchmark_population_scope_claimed":out["private_benchmark_population_scope_claimed"],
 "terminal_results_replayed":out["terminal_receipts_preserved"]["terminal_results_replayed"],
 "new_reality_units_consumed":out["new_reality_units_consumed"],
 "credit_delta":0
},indent=2,sort_keys=True))
