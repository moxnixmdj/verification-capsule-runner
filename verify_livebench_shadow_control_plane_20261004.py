from __future__ import annotations
import hashlib, importlib.util, json, sys, types
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SUB=ROOT/"subject"/"livebench_shadow_control_plane_20261004"

EXPECTED={
 "claim":("SHADOW_GIT_REF_ONE_USE_CLAIM_BACKEND_V1.json","b660e2ee70f42c7872a9b65c78198c5bdbf03609"),
 "escrow":("SHADOW_WRITE_ONLY_ESCROW_CONTRACT_V1.json","3fde5a915dec9cadf138650536820c972a9b8fb1"),
 "workflow":("SHADOW_WORKFLOW_CONTROL_CONTRACT_V1.json","d2722e7759b8045178458e1e7a8ed7904954a36d"),
 "plan":("LIVEBENCH_IF_SHADOW_PREEXPOSURE_PLAN_V2.json","1618d6f51bd63d8a2ec969f2cc5dc007f22ca572"),
 "preflight":("livebench_shadow_point_of_use_preflight_v1.py","43be0d05982a604a4c1122190a7b78fc50557121"),
 "plan_runtime":("pre_exposure_isolation_plan_v1.py","f23d632d2ad315b0c800587cd4bb09376a41f085"),
}

def git_blob_sha(path: Path) -> str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

for name,(filename,expected) in EXPECTED.items():
    got=git_blob_sha(SUB/filename)
    assert got==expected,(name,got,expected)

canonical=types.ModuleType("canonical")
runtime=types.ModuleType("canonical.runtime")
canonical.runtime=runtime
sys.modules["canonical"]=canonical
sys.modules["canonical.runtime"]=runtime

def load(name: str,path: Path):
    spec=importlib.util.spec_from_file_location(name,path)
    assert spec and spec.loader
    mod=importlib.util.module_from_spec(spec)
    sys.modules[name]=mod
    spec.loader.exec_module(mod)
    return mod

planmod=load(
 "canonical.runtime.pre_exposure_isolation_plan_v1",
 SUB/"pre_exposure_isolation_plan_v1.py",
)
preflight=load(
 "canonical.runtime.livebench_shadow_point_of_use_preflight_v1",
 SUB/"livebench_shadow_point_of_use_preflight_v1.py",
)

plan=json.loads((SUB/"LIVEBENCH_IF_SHADOW_PREEXPOSURE_PLAN_V2.json").read_text())
pv=planmod.verify_pre_exposure_plan(plan)
assert pv["pre_exposure_plan_pass"] is True,pv
assert pv["case_reveal_authority"] is False
assert pv["fresh_reality_authority"] is False
assert pv["acceptance_credit_authorized"] is False

digest="a"*64
receipt={
  "lease_digest_sha256":digest,
  "claim_ref":preflight.expected_claim_ref(digest),
  "claim_ref_absent_observed":True,
  "case_reveal_has_occurred":False,
  "execution_has_started":False,
  "evaluation_output_exists":False,
  "paid_external_model_or_api_used":False,
  "paid_or_larger_runner_used":False,
  "public_standard_github_runner":True,
  "dependency_lock_install_pass":True,
  "candidate_runtime_import_pass":True,
  "response_adapter_import_pass":True,
  "scorer_import_pass":True,
  "synthetic_zero_case_smoke_pass":True,
  "candidate_component_hashes_match_plan":True,
  "harness_component_hashes_match_plan":True,
  "scorer_component_hashes_match_plan":True,
  "environment_component_hashes_match_plan":True,
  "policy_component_hashes_match_plan":True,
  "terminal_case_source_inaccessible":True,
  "write_only_escrow_contract_bound":True,
  "workflow_control_contract_bound":True,
  "zero_incremental_spend_guard_pass":True,
  "claim_backend_receipt":{
    "path":"canonical/governance/SHADOW_GIT_REF_ONE_USE_CLAIM_BACKEND_V1.json",
    "git_blob_sha":"b660e2ee70f42c7872a9b65c78198c5bdbf03609",
  },
}
out=preflight.verify_point_of_use_preflight(plan,receipt)
assert out["point_of_use_preflight_pass"] is True,out
assert out["terminal_cases_consumed"] == 0
assert out["case_reveal_authority"] is False
assert out["shadow_collection_authority"] is False
assert out["one_use_claim_still_required"] is True
assert out["acceptance_credit_authorized"] is False

bad=dict(receipt); bad["claim_ref"]="refs/heads/shadow-claims/wrong"
assert preflight.verify_point_of_use_preflight(plan,bad)["point_of_use_preflight_pass"] is False

bad=dict(receipt); bad["case_reveal_has_occurred"]=True
assert preflight.verify_point_of_use_preflight(plan,bad)["point_of_use_preflight_pass"] is False

bad=dict(receipt); bad["synthetic_zero_case_smoke_pass"]=False
assert preflight.verify_point_of_use_preflight(plan,bad)["point_of_use_preflight_pass"] is False

claim=json.loads((SUB/"SHADOW_GIT_REF_ONE_USE_CLAIM_BACKEND_V1.json").read_text())
assert claim["claim_backend_verified"] is False
assert claim["shadow_collection_authority"] is False
assert claim["fresh_reality_authority"] is False
assert claim["observed_probe"]["first_create"]=="SUCCEEDED"
assert claim["observed_probe"]["second_identical_create"]=="REJECTED"
assert claim["observed_probe"]["second_status"]==422

for filename in ("SHADOW_WRITE_ONLY_ESCROW_CONTRACT_V1.json","SHADOW_WORKFLOW_CONTROL_CONTRACT_V1.json"):
    x=json.loads((SUB/filename).read_text())
    assert x["shadow_collection_authority"] is False
    assert x["fresh_reality_authority"] is False
    assert x["execution_authority"] is False
    assert x["promotion_authority"] is False

print(json.dumps({
  "status":"PASS",
  "exact_blob_count":len(EXPECTED),
  "livebench_preexposure_plan_pass":True,
  "point_of_use_fail_closed_pass":True,
  "terminal_cases_consumed":0,
  "case_reveal_authority":False,
  "shadow_collection_authority":False,
  "fresh_reality_authority":False,
  "acceptance_credit_authorized":False,
},sort_keys=True))
