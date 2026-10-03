from __future__ import annotations
import hashlib, importlib.util, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def blob(path: Path) -> str:
    data=path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()

exp=json.loads((ROOT/"EXPECTED_BRAIN_BLOBS.json").read_text())
actual={
 "canonical/runtime/composition_component_proof_slicer_v1.py":blob(ROOT/"composition_component_proof_slicer_v1.py"),
 "canonical/governance/COMPOSITION_COMPONENT_PROOF_SLICE_INPUT_V4.json":blob(ROOT/"input.json"),
}
assert actual==exp["exact_brain_blobs"],(actual,exp["exact_brain_blobs"])

spec=importlib.util.spec_from_file_location("slicer",ROOT/"composition_component_proof_slicer_v1.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
doc=json.loads((ROOT/"input.json").read_text())
out=mod.evaluate(doc)
assert out["status"]=="RESIDUAL_COMPONENT_INTERFACE_PROOFS_OPEN",out
assert out["all_used_component_interfaces_scoped_proved"] is False
rows=out["interfaces"]
assert len(rows)==12
proved=[r for r in rows if r["state"]=="SCOPED_PROVED"]
open_rows=[r for r in rows if r["state"]=="OPEN"]
assert len(proved)==2 and len(open_rows)==10,(proved,open_rows)
by={r["component_id"]:r for r in proved}
assert set(by)=={"memory","delegation"},by
assert by["memory"]["supporting_receipt_ids"]==["COMPOSITION_OWNED_FAMILY_BRIDGE_V2::LONG_HORIZON_MEMORY_AND_CONTINUITY::memory"]
assert by["delegation"]["supporting_receipt_ids"]==["COMPOSITION_SCOPE_COMPLETE_BRIDGE::SUBAGENT_DELEGATION_AND_COORDINATION::delegation::V1"]
for cid in ("evidence synthesis","artifact production","tool discovery"):
    assert any(r["component_id"]==cid and r["state"]=="OPEN" for r in rows),cid
assert out["new_reality_units_consumed"]==0
assert out["capability_credit_delta"]==0 and out["family_credit_delta"]==0
print(json.dumps({"status":"PASS","scoped_proved":2,"open":10,"proved_components":sorted(by),"slicer_output":out},indent=2,sort_keys=True))
