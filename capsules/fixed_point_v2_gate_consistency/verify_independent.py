from __future__ import annotations
import hashlib, json, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
EXPECTED={
    "canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V1.json": "1b4078b9c4c2a0d6540a7f1708a6de1f056dc708",
    "canonical/governance/OPUS55_PROTOCOL_IMPLICATION_GATE_REFINEMENT_V1.json": "0d96aae59ec910f5395dbf277ca1762454440550",
    "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json": "562536d9ba3f245a6bd24490a1eb3b30f27e0c3a",
    "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json": "f500b56e7349ce8c0f97cfd0bd1db4888ec6887c",
    "canonical/runtime/acceptance_ir_compiler_v1.py": "c6961bcd87e16c9ff63b4c365e8547a0885b2eb4",
    "canonical/runtime/minimum_terminal_cut_solver_v1.py": "bbdaaa750ed8d2e640145c8eafaebf00763c9eed",
    "canonical/tests/test_protocol_implication_gate_refinement_v1.py": "1af970b932b4dca3239e9a90aea1e282186cdc58",
    "canonical/tests/test_current_acceptance_fixed_point_v2.py": "dfdb73ddbdf156c39604f36832505a173a008080"
}

def blob(path):
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

for rel,sha in EXPECTED.items():
    got=blob(ROOT/rel)
    assert got==sha,(rel,got,sha)

for test in [
    "canonical/tests/test_protocol_implication_gate_refinement_v1.py",
    "canonical/tests/test_current_acceptance_fixed_point_v2.py",
]:
    subprocess.run([sys.executable,test],cwd=ROOT,check=True)

gate=json.loads((ROOT/"canonical/governance/OPUS55_PROTOCOL_IMPLICATION_GATE_REFINEMENT_V1.json").read_text())
hg=json.loads((ROOT/"canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V1.json").read_text())
assert gate["exact_gate_state"]["protocol_implication_scope_algebra_available"] is False
act=next(a for a in hg["actions"] if a["id"]=="RUN_PROTOCOL_IMPLICATION_SCOPE_ALGEBRA")
pre={x["id"]:x for x in act["preconditions"]}
assert pre["MATCHED_BRAIN_WITNESS_TARGET_ATOM_METRIC_BINDINGS_INDEPENDENT_PASS"]["satisfied"] is False
assert pre["MATCHED_BRAIN_WITNESS_CONTAMINATION_ADMISSIBILITY_INDEPENDENT_PASS"]["satisfied"] is False
print("independent fixed-point v2 gate consistency: PASS")
