from __future__ import annotations
import hashlib, importlib.util, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
EXPECTED={
"canonical/governance/COMPOSITION_COMPONENT_PROOF_SLICE_INPUT_V4.json":"f648369447455e84d8660117537c91b935df288d",
"canonical/verification/COMPOSITION_COMPONENT_PROOF_SLICE_20261003_V4.json":"7081165dc1052c62436d4a0b2b23726675da321f",
"canonical/governance/COMPOSITION_CURRENT_SOURCE_TWO_COMPONENT_SLICE_CANDIDATE_V1.json":"638086624f61f853073e534f2040702e56180a05",
"canonical/runtime/composition_component_proof_slicer_v1.py":"0e5028d8547bc3e17e7128b6311f734ac30a16d8",
"canonical/verification/COMPOSITION_DELEGATION_BRIDGE_V1_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"97bd385a20f78f86d03d78939d2552411c9c1cca",
"canonical/verification/COMPOSITION_MEMORY_OWNED_FAMILY_BRIDGE_V2_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"88783df170065d3ff23e4ff3c2d2ab30ec7bc314",
}
def blob_sha(path:Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(f"blob {len(b)}\0".encode()+b).hexdigest()
def load(rel):
    return json.loads((ROOT/rel).read_text(encoding="utf-8"))
for rel,sha in EXPECTED.items():
    got=blob_sha(ROOT/rel)
    assert got==sha,(rel,got,sha)

inp=load("canonical/governance/COMPOSITION_COMPONENT_PROOF_SLICE_INPUT_V4.json")
expected=load("canonical/verification/COMPOSITION_COMPONENT_PROOF_SLICE_20261003_V4.json")
candidate=load("canonical/governance/COMPOSITION_CURRENT_SOURCE_TWO_COMPONENT_SLICE_CANDIDATE_V1.json")
deleg=load("canonical/verification/COMPOSITION_DELEGATION_BRIDGE_V1_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json")
memory=load("canonical/verification/COMPOSITION_MEMORY_OWNED_FAMILY_BRIDGE_V2_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json")

assert str(deleg["status"]).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert str(memory["status"]).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
assert deleg["public_runner"]["workflow_run_id"]==37086752998
assert deleg["public_runner"]["conclusion"]=="success"
assert memory["public_runner"]["workflow_run_id"]==37086511516
assert memory["public_runner"]["conclusion"]=="success"
receipts=inp["receipts"]
assert len(receipts)==2
assert {r["component_id"] for r in receipts}=={"memory","delegation"}
for r in receipts:
    assert r["verified"] is True
    assert r["independent"] is True
    assert r["contamination_clean"] is True
    assert r["acceptance_scoped"] is True
    assert r["binds_frozen_claim"]=="MULTI_CAPABILITY_COMPOSITION::FROZEN_PROTOCOL_V1"
assert next(r for r in receipts if r["component_id"]=="memory")["receipt_id"]==memory["verified_component_receipt"]["receipt_id"]
assert next(r for r in receipts if r["component_id"]=="delegation")["receipt_id"]==deleg["verified_component_receipt"]["receipt_id"]

spec=importlib.util.spec_from_file_location("slicer",ROOT/"canonical/runtime/composition_component_proof_slicer_v1.py")
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
actual=mod.evaluate(inp)
assert actual==expected,(actual,expected)
proved=[x["component_id"] for x in actual["interfaces"] if x["state"]=="SCOPED_PROVED"]
open_=[x["component_id"] for x in actual["interfaces"] if x["state"]=="OPEN"]
assert set(proved)=={"memory","delegation"},proved
assert len(proved)==2
assert len(open_)==10
assert "tool discovery" in open_
assert "evidence synthesis" in open_
assert "artifact production" in open_
assert actual["all_used_component_interfaces_scoped_proved"] is False
assert candidate["expected_result"]["scoped_proved_count"]==2
assert candidate["expected_result"]["open_count"]==10
assert candidate["expected_result"]["parent_composition_predicate_closed"] is False
assert candidate["expected_result"]["acceptance_change"]==0
for k in ("new_reality_units_consumed","terminal_results_replayed","incremental_spend_usd","capability_credit_delta","family_credit_delta"):
    assert candidate[k]==0
assert candidate["execution_authority"] is False
assert candidate["promotion_authority"] is False
print("PASS: exact current-source composition slice = memory + delegation = 2/12; 10 open; parent open; zero terminal credit")
