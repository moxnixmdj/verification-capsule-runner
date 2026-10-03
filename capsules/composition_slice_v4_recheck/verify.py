import importlib.util,json
from pathlib import Path

s=Path("capsules/composition_memory_slice_v3/composition_component_proof_slicer_v1.py")
p=Path("capsules/composition_slice_v4_recheck/input.json")

def blob(path):
    data=path.read_bytes()
    import hashlib
    return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()

assert blob(s)=="0e5028d8547bc3e17e7128b6311f734ac30a16d8"
assert blob(p)=="869b48bdb4140fa6a4172f4b5d6c65774c51395b"
spec=importlib.util.spec_from_file_location("slicer",s)
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
out=mod.evaluate(json.loads(p.read_text()))
proved=[r["component_id"] for r in out["interfaces"] if r["state"]=="SCOPED_PROVED"]
opened=[r["component_id"] for r in out["interfaces"] if r["state"]=="OPEN"]
assert proved==["memory","delegation"],(proved,opened)
assert len(opened)==10
assert out["all_used_component_interfaces_scoped_proved"] is False
assert out["new_reality_units_consumed"]==0
assert out["capability_credit_delta"]==0 and out["family_credit_delta"]==0
print(json.dumps({"status":"PASS","scoped_proved":2,"open":10,"proved_components":proved,"parent_closed":False},sort_keys=True))
