from __future__ import annotations
import hashlib, json, os, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
EXPECTED={
  "canonical/runtime/p1_v6_universal_terminal_generator_refinement_v1.py": "4faed3d100d3618992756aada8df455b6c1efc79",
  "canonical/tests/test_p1_v6_universal_terminal_generator_refinement_v1.py": "e59ab4b543e9a13065de2301b27fd0d5928299e8",
  "canonical/governance/P1_V6_UNIVERSAL_TERMINAL_GENERATOR_REFINEMENT_ACTIVATION_V1.json": "2138fe2566977f406b9300066abc54938dfdc80d",
  "canonical/runtime/contract_native_proof_suites.py": "0210790c7dd705ef328e1b55d529a30c5c6c3337",
  "canonical/runtime/contract_native_brain_candidate.py": "afc18af1d1da6f25166c6cc57dcbc0cd3070bb85",
  "canonical/runtime/terminal_parent_portfolio_runner_v1.py": "431b62e503a6a179f19339ae5e0ab6948424a650",
  "canonical/governance/TERMINAL_PARENT_PORTFOLIO_RUNNER_BINDING_V1.json": "a1630299d29ea9c07e55b4314c07ddb3228c3287",
  "canonical/runtime/trajectory_failure_typed_ir_candidate_v6.py": "18d4de68ee8352410e986c318868642333ec085a",
  "canonical/runtime/trajectory_failure_typed_ir_proof_v6.py": "0f41a36e6ad16722ce05b180e036fb921a2ef886",
  "canonical/verification/P1_TYPED_CAUSAL_INTERVENTION_V6_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json": "1e722621db8f0f1cb3b9689e48d4bfe356dcb36e"
}

def blob(path:Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

for rel,sha in EXPECTED.items():
    got=blob(ROOT/rel)
    assert got==sha,(rel,got,sha)

env=dict(os.environ)
env["PYTHONPATH"]=str(ROOT)
cp=subprocess.run(
    [sys.executable,"-m","unittest","canonical.tests.test_p1_v6_universal_terminal_generator_refinement_v1","-v"],
    cwd=ROOT,env=env,text=True,capture_output=True,
)
print(cp.stdout)
print(cp.stderr,file=sys.stderr)
assert cp.returncode==0,cp.returncode

sys.path.insert(0,str(ROOT))
from canonical.runtime import p1_v6_universal_terminal_generator_refinement_v1 as theorem
out=theorem.evaluate()
assert out["pass"] is True,out
assert out["structural_equivalence_class_count"]==30,out
assert out["refinement_checks"]==540,out
assert out["forward_rescue_checks"]==540,out
assert out["symptom_only_negative_checks"]==540,out
assert out["terminal_results_replayed"]==0,out
assert out["historical_terminal_case_ids_read"]==0,out

print(json.dumps({
 "status":"PASS",
 "exact_brain_blob_count":len(EXPECTED),
 "structural_equivalence_classes":out["structural_equivalence_class_count"],
 "refinement_checks":out["refinement_checks"],
 "forward_rescue_checks":out["forward_rescue_checks"],
 "symptom_only_negative_checks":out["symptom_only_negative_checks"],
 "historical_terminal_case_ids_read":out["historical_terminal_case_ids_read"],
 "terminal_results_replayed":out["terminal_results_replayed"],
 "relation":out["relation"],
 "capability_credit_delta":0,
 "family_credit_delta":0
},indent=2,sort_keys=True))
