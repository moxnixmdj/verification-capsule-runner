#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util, json, pathlib, sys, types

ROOT=pathlib.Path(__file__).resolve().parent
SUB=ROOT/"subject"/"livebench_successor_point_of_use_preflight_v2_20261004_sol"
PLAN=ROOT/"subject"/"livebench_successor_preexposure_v3_20261004_sol"/"LIVEBENCH_IF_SHADOW_PREEXPOSURE_PLAN_V3.json"
PRE=ROOT/"subject"/"shadow_lease_v2_20261004"/"pre_exposure_isolation_plan_v1.py"
RUNTIME=SUB/"livebench_shadow_point_of_use_preflight_v2.py"
TEST=SUB/"test_livebench_shadow_point_of_use_preflight_v2.py"

def blob(p):
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

assert blob(RUNTIME)=="654791671e1c3b834021dbd5d62d2797755b4c46"
assert blob(TEST)=="ef7d62701f3de9769054600852580d83d7948c65"
assert blob(PLAN)=="2663f794033cf779fdecb8806a95e932f6084004"

canonical=types.ModuleType("canonical"); runtime_pkg=types.ModuleType("canonical.runtime")
canonical.runtime=runtime_pkg
sys.modules["canonical"]=canonical
sys.modules["canonical.runtime"]=runtime_pkg

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    assert spec and spec.loader
    m=importlib.util.module_from_spec(spec)
    sys.modules[name]=m
    spec.loader.exec_module(m)
    return m

pre=load("canonical.runtime.pre_exposure_isolation_plan_v1",PRE)
runtime_pkg.pre_exposure_isolation_plan_v1=pre
mod=load("canonical.runtime.livebench_shadow_point_of_use_preflight_v2",RUNTIME)

plan=json.loads(PLAN.read_text())
digest="a"*64

def receipt():
    return {
      "lease_digest_sha256":digest,
      "claim_ref":mod.expected_claim_ref(digest),
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
      "resource_truth_repair":{
        "path":"canonical/verification/LIVEBENCH_ZERO_CASE_RESOURCE_FIT_TRUTH_REPAIR_20261004_V1.json",
        "git_blob_sha":"8a603c1f48aad6e0fc79c2c76d2db437efde3893",
        "positive_run_id":37184530130,
        "positive_job_id":111383591914,
        "positive_run_conclusion":"success",
        "terminal_cases_consumed":0,
        "paid_external_model_or_api_used":False,
        "exact_scorer_import_pass":True,
        "astra_model_independent_synthetic_smoke":True,
      },
      "claim_backend_receipt":{
        "path":"canonical/governance/SHADOW_GIT_REF_ONE_USE_CLAIM_BACKEND_V1.json",
        "git_blob_sha":"b660e2ee70f42c7872a9b65c78198c5bdbf03609",
      },
    }

out=mod.verify_point_of_use_preflight(plan,receipt())
assert out["point_of_use_preflight_pass"] is True,out
assert out["case_reveal_authority"] is False
assert out["shadow_collection_authority"] is False
assert out["global_fresh_reality_authority"] is False
assert out["acceptance_credit_authorized"] is False
assert out["one_use_claim_still_required"] is True
assert out["terminal_cases_consumed"]==0

mutations=[
 ("resource_blob",lambda r:r["resource_truth_repair"].__setitem__("git_blob_sha","0"*40),"RESOURCE_TRUTH_REPAIR_BLOB_MISMATCH"),
 ("resource_failure",lambda r:r["resource_truth_repair"].__setitem__("positive_run_conclusion","failure"),"RESOURCE_TRUTH_REPAIR_SUCCESS_NOT_BOUND"),
 ("claim_ref",lambda r:r.__setitem__("claim_ref","refs/heads/shadow-claims/wrong"),"CLAIM_REF_NOT_DERIVED_FROM_LEASE_DIGEST"),
 ("case_exposure",lambda r:r.__setitem__("case_reveal_has_occurred",True),"PREFLIGHT_FALSE_GATE_FAILED:case_reveal_has_occurred"),
 ("smoke",lambda r:r.__setitem__("synthetic_zero_case_smoke_pass",False),"PREFLIGHT_TRUE_GATE_FAILED:synthetic_zero_case_smoke_pass"),
 ("backend",lambda r:r["claim_backend_receipt"].__setitem__("git_blob_sha","0"*40),"CLAIM_BACKEND_BLOB_MISMATCH"),
]
for name,mut,reason in mutations:
    r=receipt(); mut(r)
    o=mod.verify_point_of_use_preflight(plan,r)
    assert o["point_of_use_preflight_pass"] is False,(name,o)
    assert reason in o["reasons"],(name,o)

bad_plan=dict(plan); bad_plan["plan_sha256"]="0"*64
o=mod.verify_point_of_use_preflight(bad_plan,receipt())
assert o["point_of_use_preflight_pass"] is False
assert "LIVEBENCH_SUCCESSOR_PLAN_SHA256_MISMATCH" in o["reasons"]

print(json.dumps({
 "status":"PASS",
 "runtime_git_blob_sha":blob(RUNTIME),
 "test_git_blob_sha":blob(TEST),
 "plan_git_blob_sha":blob(PLAN),
 "negative_mutation_count":len(mutations)+1,
 "terminal_cases_consumed":0,
 "case_reveal_authority":False,
 "shadow_collection_authority":False,
},sort_keys=True))
