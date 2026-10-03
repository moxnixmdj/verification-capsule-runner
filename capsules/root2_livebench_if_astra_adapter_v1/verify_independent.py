from __future__ import annotations
import ast, hashlib, json, pathlib, subprocess, sys

ROOT=pathlib.Path(__file__).resolve().parent

def blob(path):
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

m=json.loads((ROOT/"EXPECTED_BRAIN_BLOBS.json").read_text())
for rel,expected in m["exact_brain_blobs"].items():
    got=blob(ROOT/rel)
    assert got==expected,(rel,got,expected)

adapter_path=ROOT/"canonical/runtime/root2_livebench_if_astra_inference_adapter_v1.py"
tree=ast.parse(adapter_path.read_text())
text=adapter_path.read_text()
assert 'BENCHMARK_ID="LIVEBENCH_IF_2026_06_25"' in text
assert '"allow_optional_model_planner":False' in text
assert 'MODEL_INDEPENDENT' in text
assert 'MODEL_DEPENDENCY_FORBIDDEN' in text
assert 'LIVEBENCH_IF_EXTERNAL_TOOLS_FORBIDDEN' in text
assert 'EMPTY_ANSWER' in text

reg=json.loads((ROOT/"canonical/governance/ROOT2_EXTERNAL_TASK_ADAPTER_REGISTRY_V1.json").read_text())
rows=[x for x in reg["adapters"] if x["benchmark_id"]=="LIVEBENCH_IF_2026_06_25"]
assert len(rows)==1
r=rows[0]
assert r["inference_capable"] is True
assert r["mode"]=="INFERENCE"
assert r["adapter_blob_sha"]==m["exact_brain_blobs"]["canonical/runtime/root2_livebench_if_astra_inference_adapter_v1.py"]

clean=json.loads((ROOT/"canonical/verification/ROOT2_LIVEBENCH_IF_ASTRA_ADAPTER_CLEANROOM_VERIFICATION_20261004_V1.json").read_text())
assert clean["test_result"]["passed"]==6 and clean["test_result"]["failed"]==0
assert clean["acceptance_credit_delta"]==0
assert clean["fresh_reality_authority"] is False

sys.path.insert(0,str(ROOT))
from canonical.runtime import root2_livebench_if_astra_inference_adapter_v1 as adapter
from canonical.runtime import root2_external_task_entrypoint_v1 as ep

class Fake:
    def __init__(self, payload): self.payload=payload
    def run_goal(self,step,mission): return dict(self.payload)

adapter.astra_runtime=Fake({"stdout":"answer","trace":[],"cognition_dependency_class":"MODEL_INDEPENDENT","model_dependency_count":0})
out=adapter.infer({"benchmark_id":"LIVEBENCH_IF_2026_06_25","task_id":"synthetic","task_payload":{"instruction":"Rewrite this."},"allowed_tools":[]})
assert out["answer"]=="answer" and out["model_dependency_count"]==0

adapter.astra_runtime=Fake({"stdout":"answer","trace":[],"cognition_dependency_class":"MODEL_ASSISTED","model_dependency_count":1})
try:
    adapter.infer({"benchmark_id":"LIVEBENCH_IF_2026_06_25","task_id":"synthetic","task_payload":{"instruction":"Rewrite this."},"allowed_tools":[]})
    raise AssertionError("MODEL_ASSISTED_NOT_REJECTED")
except adapter.Root2InferenceBlocked:
    pass

try:
    adapter.infer({"benchmark_id":"LIVEBENCH_IF_2026_06_25","task_id":"synthetic","task_payload":{"instruction":"test"},"allowed_tools":["web_search"]})
    raise AssertionError("TOOLS_NOT_REJECTED")
except adapter.Root2InferenceBlocked:
    pass

pf=ep.preflight("LIVEBENCH_IF_2026_06_25")
assert pf["inference_ready"] is True and pf["status"]=="PASS__INFERENCE_ADAPTER_BOUND"
assert ep.preflight("NOT_A_REAL_BENCHMARK")["inference_ready"] is False

print("ROOT2_LIVEBENCH_IF_ASTRA_ADAPTER_PUBLIC_INDEPENDENT_PASS")
