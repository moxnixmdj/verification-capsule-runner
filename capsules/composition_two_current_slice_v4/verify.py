from __future__ import annotations
import hashlib, importlib.util, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def blob(p:Path)->str:
    b=p.read_bytes()
    return hashlib.sha1(f"blob {len(b)}\0".encode()+b).hexdigest()

exp=json.loads((ROOT/"EXPECTED_BRAIN_BLOBS.json").read_text())
local={
 "canonical/runtime/composition_component_proof_slicer_v1.py":"composition_component_proof_slicer_v1.py",
 "canonical/governance/COMPOSITION_COMPONENT_PROOF_SLICE_INPUT_V4.json":"input.json",
 "canonical/verification/COMPOSITION_COMPONENT_PROOF_SLICE_20261003_V4.json":"output.json",
 "canonical/governance/FROZEN_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_V1.json":"manifest.json",
 "canonical/verification/COMPOSITION_MEMORY_OWNED_FAMILY_BRIDGE_V2_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"memory_verification.json",
 "canonical/verification/COMPOSITION_DELEGATION_SCOPE_COMPLETE_BRIDGE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"delegation_verification.json",
}
actual={k:blob(ROOT/v) for k,v in local.items()}
assert actual==exp["exact_brain_blobs"],(actual,exp["exact_brain_blobs"])

spec=importlib.util.spec_from_file_location("slicer",ROOT/"composition_component_proof_slicer_v1.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

doc=json.loads((ROOT/"input.json").read_text())
stored=json.loads((ROOT/"output.json").read_text())
manifest=json.loads((ROOT/"manifest.json").read_text())
memory_ver=json.loads((ROOT/"memory_verification.json").read_text())
delegation_ver=json.loads((ROOT/"delegation_verification.json").read_text())

# Frozen universe binding: V4 may not silently edit, omit, or add a component.
assert doc["claim_id"]==manifest["claim_id"]
assert doc["source_manifest_git_blob_sha"]==actual["canonical/governance/FROZEN_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_V1.json"]
manifest_interfaces=[{
    "component_id":r["component_id"],
    "interface_id":r["interface_id"],
    "required_properties":r["required_properties"],
} for r in manifest["interfaces"]]
assert manifest["isolated_component_interface_count"]==12
assert doc["interfaces"]==manifest_interfaces,(doc["interfaces"],manifest_interfaces)

# Receipt authority binding: V4 cannot self-certify verified=True.
by_component={r["component_id"]:r for r in doc["receipts"]}
assert set(by_component)=={"memory","delegation"}
assert by_component["memory"]==memory_ver["verified_component_receipt"]
assert by_component["delegation"]==delegation_ver["verified_component_receipt"]
for ver,pr,run in [
    (memory_ver,1120,37086511516),
    (delegation_ver,1129,37086752998),
]:
    assert ver["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
    assert ver["public_runner"]["pull_request"]==pr
    assert ver["public_runner"]["workflow_run_id"]==run
    assert ver["public_runner"]["conclusion"]=="success"
    assert ver["new_reality_units_consumed"]==0
    assert ver["capability_credit_delta"]==0 and ver["family_credit_delta"]==0
    assert ver["execution_authority"] is False and ver["promotion_authority"] is False

assert doc["receipt_verifications"]==[
 "canonical/verification/COMPOSITION_MEMORY_OWNED_FAMILY_BRIDGE_V2_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
 "canonical/verification/COMPOSITION_DELEGATION_SCOPE_COMPLETE_BRIDGE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
]
assert set(doc["quarantined_historical_receipts"])=={
 "COMPOSITION_BRIDGE::TOOL_ROUTE_DISCOVERY_AND_SELECTION_001::tool_discovery",
 "COMPOSITION_BRIDGE::TASK_TO_DELEGATION_GRAPH_001::delegation",
}

# Independently recompute with the unchanged canonical slicer.
out=mod.evaluate(doc)
assert out==stored,(out,stored)
assert out["status"]=="RESIDUAL_COMPONENT_INTERFACE_PROOFS_OPEN"
assert out["all_used_component_interfaces_scoped_proved"] is False
rows=out["interfaces"]
assert len(rows)==12
proved=[r for r in rows if r["state"]=="SCOPED_PROVED"]
opened=[r for r in rows if r["state"]=="OPEN"]
assert [r["component_id"] for r in proved]==["memory","delegation"],proved
assert len(proved)==2 and len(opened)==10
assert {"tool discovery","evidence synthesis","artifact production"} <= {r["component_id"] for r in opened}
assert out["new_reality_units_consumed"]==0
assert out["capability_credit_delta"]==0 and out["family_credit_delta"]==0
assert doc["new_reality_units_consumed"]==0 and doc["terminal_results_replayed"]==0
assert doc["incremental_spend_usd"]==0
assert doc["capability_credit_delta"]==0 and doc["family_credit_delta"]==0

# Falsification: removing independent authority must remove both credits.
mut=json.loads(json.dumps(doc))
for r in mut["receipts"]:
    r["independent"]=False
bad=mod.evaluate(mut)
assert not any(r["state"]=="SCOPED_PROVED" for r in bad["interfaces"]),bad

print(json.dumps({
 "status":"PASS",
 "brain_ref":exp["brain_ref"],
 "authority_bindings":"EXACT",
 "stored_output_recomputed_exactly":True,
 "scoped_proved":2,
 "open":10,
 "proved_components":["memory","delegation"],
 "parent_open":True,
 "zero_reality":True,
},indent=2,sort_keys=True))
