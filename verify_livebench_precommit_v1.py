from __future__ import annotations
import hashlib, importlib.util, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SUB=ROOT/"subject"/"livebench_precommit_v1"
MANIFEST=SUB/"LIVEBENCH_IF_EXECUTION_PRECOMMIT_V1.json"
RUNTIME=SUB/"livebench_if_execution_precommit_v1.py"

EXPECTED_MANIFEST_BLOB="a5e7315670ff4bc59fa81a683dd621e4aa1773c6"
EXPECTED_RUNTIME_BLOB="efed99a69e2ce3c39d4e497ce8cb9d6e81317cf3"

def git_blob_sha(path: Path)->str:
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

assert git_blob_sha(MANIFEST)==EXPECTED_MANIFEST_BLOB
assert git_blob_sha(RUNTIME)==EXPECTED_RUNTIME_BLOB

spec=importlib.util.spec_from_file_location("livebench_if_execution_precommit_v1",RUNTIME)
assert spec and spec.loader
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
manifest=json.loads(MANIFEST.read_text())

out=mod.verify_precommit(manifest)
assert out["precommit_pass"] is True, out
assert out["terminal_cases_consumed"]==0
assert out["resource_fit_proved"] is False
assert out["generic_isolation_instantiation_proved"] is False
assert out["shadow_collection_authority"] is False
assert out["fresh_reality_authority"] is False
assert out["acceptance_credit_authorized"] is False

assert manifest["candidate"]["commit"]=="d5de4f5808dced840da34d051e3f9a5ff06e2e54"
assert manifest["candidate"]["tree"]=="fd39e966d4686c7317b9a1558b360eb0c58ad76f"
assert manifest["case_exposure"]["terminal_case_content_read"] is False
assert manifest["case_exposure"]["terminal_cases_consumed"]==0
assert manifest["policy"]["allow_optional_model_planner"] is False
assert manifest["policy"]["external_tools_allowed"] is False
assert manifest["policy"]["required_cognition_dependency_class"]=="MODEL_INDEPENDENT"
assert manifest["policy"]["result_sink"]=="WRITE_ONLY_ESCROW"

for component in ("candidate","harness","scorer","environment","policy"):
    x=json.loads(MANIFEST.read_text())
    x[component]["_changed"]="x"
    assert mod.verify_precommit(x)["precommit_pass"] is False

x=json.loads(MANIFEST.read_text())
x["policy"]["result_visible_to_candidate_before_fixed_point"]=True
assert mod.verify_precommit(x)["precommit_pass"] is False

x=json.loads(MANIFEST.read_text())
x["environment"]["resource_fit_status"]="PASS"
assert mod.verify_precommit(x)["precommit_pass"] is False

print(json.dumps({
  "status":"PASS",
  "manifest_git_blob_sha":EXPECTED_MANIFEST_BLOB,
  "runtime_git_blob_sha":EXPECTED_RUNTIME_BLOB,
  "five_component_precommit_verified":True,
  "terminal_cases_consumed":0,
  "resource_fit_proved":False,
  "generic_isolation_instantiation_proved":False,
  "shadow_collection_authority":False,
  "fresh_reality_authority":False,
  "acceptance_credit_authorized":False
},sort_keys=True))
