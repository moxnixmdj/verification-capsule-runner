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
 "canonical/governance/COMPOSITION_COMPONENT_PROOF_SLICE_INPUT_V3.json":blob(ROOT/"input.json"),
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
assert len(proved)==1 and len(open_rows)==11,(proved,open_rows)
m=proved[0]
assert m["component_id"]=="memory"
assert m["interface_id"]=="browser/computer action+memory+recovery"
assert m["proved_properties"]==["SCOPED_ACCEPTANCE_PROOF"]
assert m["missing_properties"]==[]
assert m["supporting_receipt_ids"]==["COMPOSITION_OWNED_FAMILY_BRIDGE_V2::LONG_HORIZON_MEMORY_AND_CONTINUITY::memory"]
assert all(r["component_id"]!="memory" for r in open_rows)
assert out["new_reality_units_consumed"]==0
assert out["capability_credit_delta"]==0 and out["family_credit_delta"]==0
print(json.dumps({"status":"PASS","scoped_proved":1,"open":11,"proved_component":"memory","slicer_output":out},indent=2,sort_keys=True))
