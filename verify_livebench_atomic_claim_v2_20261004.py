from __future__ import annotations
import ast, hashlib, importlib.util, json, sys, types
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SUB=ROOT/"subject"/"livebench_atomic_claim_v2_20261004"

EXPECTED={
  "candidate":("LIVEBENCH_SHADOW_ATOMIC_CLAIM_TRANSACTION_CANDIDATE_V2.json","ef8924151327bbc3c769bca426fa4027a52642b7"),
  "plan":("LIVEBENCH_IF_SHADOW_PREEXPOSURE_PLAN_V3.json","2663f794033cf779fdecb8806a95e932f6084004"),
  "preflight":("livebench_shadow_point_of_use_preflight_v1.py","4c12fa8c2a7dcf549a991da470ab50b7faaac399"),
  "atomic":("livebench_shadow_atomic_claim_transaction_v1.py","f4a5b0ac63214277befdca79f6cb32e2acedc0c6"),
}
PLAN_SHA="9608157e7ef52fab08bc387bb19ccfb10001cbb5367849a9806d6b0e7df34b31"

def blob_sha(path:Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

for name,(filename,expected) in EXPECTED.items():
    got=blob_sha(SUB/filename)
    assert got==expected,(name,got,expected)

candidate=json.loads((SUB/EXPECTED["candidate"][0]).read_text())
plan=json.loads((SUB/EXPECTED["plan"][0]).read_text())
assert candidate["compiled_from_main"]=="947626745b7fc8f7120ae9cb8b0cce767fa4834e"
assert candidate["subjects"]["pre_exposure_plan_v3"]["git_blob_sha"]==EXPECTED["plan"][1]
assert candidate["subjects"]["pre_exposure_plan_v3"]["plan_sha256"]==PLAN_SHA
assert candidate["subjects"]["point_of_use_preflight"]["git_blob_sha"]==EXPECTED["preflight"][1]
assert candidate["subjects"]["atomic_transaction"]["git_blob_sha"]==EXPECTED["atomic"][1]
assert candidate["current_verified_foundation"]["execution_precommit_v2_verification"]["git_blob_sha"]=="f123064a5ebed27c8636a2ebc031fb9a31067a13"
assert candidate["current_verified_foundation"]["pre_exposure_v3_verification"]["git_blob_sha"]=="7aee430ee0de0fdf3347526a5cb592caaac64bb7"
assert candidate["current_verified_foundation"]["shadow_control_plane_verification"]["git_blob_sha"]=="af01458bfb36ede0f494214fd2f240e5aa36b3c5"
assert candidate["accounting"]["terminal_cases_consumed"]==0
assert candidate["shadow_collection_authority"] is False
assert candidate["fresh_reality_authority"] is False
assert candidate["promotion_authority"] is False

preflight_src=(SUB/EXPECTED["preflight"][0]).read_text()
atomic_src=(SUB/EXPECTED["atomic"][0]).read_text()
ast.parse(preflight_src); ast.parse(atomic_src)
assert "claim_ref_absent_observed" not in preflight_src
assert f'EXPECTED_PLAN_SHA256="{PLAN_SHA}"' in preflight_src
assert '"ATOMIC_CREATE_RESPONSE"' in atomic_src
assert 'create_http_status") != 201' in atomic_src

canonical=types.ModuleType("canonical")
runtime=types.ModuleType("canonical.runtime")
canonical.runtime=runtime
sys.modules["canonical"]=canonical
sys.modules["canonical.runtime"]=runtime

planmod=types.ModuleType("canonical.runtime.pre_exposure_isolation_plan_v1")
def verify_pre_exposure_plan(x):
    ok=(x.get("schema")=="PROJECT_BRAIN_PRE_EXPOSURE_ISOLATION_PLAN_V1" and x.get("plan_sha256")==PLAN_SHA
        and x.get("case_reveal_has_occurred") is False and x.get("execution_has_started") is False
        and x.get("evaluation_output_exists") is False)
    return {"pre_exposure_plan_pass":ok}
planmod.verify_pre_exposure_plan=verify_pre_exposure_plan
sys.modules["canonical.runtime.pre_exposure_isolation_plan_v1"]=planmod

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    assert spec and spec.loader
    mod=importlib.util.module_from_spec(spec)
    sys.modules[name]=mod
    spec.loader.exec_module(mod)
    return mod

preflight=load("canonical.runtime.livebench_shadow_point_of_use_preflight_v1",SUB/EXPECTED["preflight"][0])
runtime.livebench_shadow_point_of_use_preflight_v1=preflight

shadow=types.ModuleType("canonical.runtime.shadow_reality_lease_v2")
def verify_activation_receipt(r):
    reasons=[]
    if r.get("schema")!="PROJECT_BRAIN_SHADOW_REALITY_COLLECTION_ACTIVATION_V2":
        reasons.append("SCHEMA")
    for f in ("active","shadow_collection_authority","independent_verification_pass","zero_incremental_spend_only",
              "write_only_escrow_only","two_phase_isolation_protocol_required","durable_one_use_claim_backend_verified",
              "point_of_use_preflight_required","post_execution_isolation_receipt_required"):
        if r.get(f) is not True: reasons.append(f)
    for f in ("global_fresh_reality_authority","acceptance_credit_authority","promotion_authority"):
        if r.get(f) is not False: reasons.append(f)
    for f in ("independent_verification_receipt","claim_backend_verification_receipt"):
        x=r.get(f)
        if not isinstance(x,dict) or not x.get("path") or not isinstance(x.get("git_blob_sha"),str) or len(x["git_blob_sha"])!=40:
            reasons.append(f)
    return not reasons,reasons
shadow.verify_activation_receipt=verify_activation_receipt
sys.modules["canonical.runtime.shadow_reality_lease_v2"]=shadow
runtime.shadow_reality_lease_v2=shadow

atomic=load("canonical.runtime.livebench_shadow_atomic_claim_transaction_v1",SUB/EXPECTED["atomic"][0])

digest="a"*64
receipt={
 "lease_digest_sha256":digest,
 "claim_ref":preflight.expected_claim_ref(digest),
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
p=preflight.verify_point_of_use_preflight(plan,receipt)
assert p["point_of_use_preflight_pass"] is True,p
assert p["claim_ref_absence_precheck_required"] is False
assert p["case_reveal_authority"] is False
legacy=dict(receipt); legacy["claim_ref_absent_observed"]=False
assert preflight.verify_point_of_use_preflight(plan,legacy)["point_of_use_preflight_pass"] is True
bad=dict(receipt); bad["claim_ref"]="refs/heads/shadow-claims/wrong"
assert preflight.verify_point_of_use_preflight(plan,bad)["point_of_use_preflight_pass"] is False

activation={
 "schema":"PROJECT_BRAIN_SHADOW_REALITY_COLLECTION_ACTIVATION_V2",
 "benchmark_id":"LIVEBENCH_IF_2026_06_25",
 "target_predicate":"LIVEBENCH_IF_GE_65_7",
 "active":True,"shadow_collection_authority":True,"independent_verification_pass":True,
 "zero_incremental_spend_only":True,"write_only_escrow_only":True,
 "two_phase_isolation_protocol_required":True,"durable_one_use_claim_backend_verified":True,
 "point_of_use_preflight_required":True,"post_execution_isolation_receipt_required":True,
 "global_fresh_reality_authority":False,"acceptance_credit_authority":False,"promotion_authority":False,
 "independent_verification_receipt":{"path":"verified/atomic","git_blob_sha":"1"*40},
 "claim_backend_verification_receipt":{"path":"verified/backend","git_blob_sha":"2"*40},
}
def claim(status=201):
    ref=receipt["claim_ref"]
    return {
      "schema":atomic.CLAIM_SCHEMA,"claim_ref":ref,"create_http_status":status,
      "reference_created":status==201,"response_ref":ref,"response_object_sha":"3"*40,
      "preflight_binding_sha256":atomic.preflight_binding_sha256(plan,receipt),
      "case_reveal_has_occurred_before_claim":False,"execution_has_started_before_claim":False,
      "evaluation_output_exists_before_claim":False,"claim_uniqueness_source":"ATOMIC_CREATE_RESPONSE",
    }

ok=atomic.verify_atomic_claim_transaction(plan=plan,preflight_receipt=receipt,activation_receipt=activation,claim_receipt=claim())
assert ok["atomic_claim_transaction_pass"] is True,ok
assert ok["case_reveal_authority"] is True
assert ok["shadow_collection_authority"] is True
assert ok["authority_scope"]=="THIS_EXACT_LEASE_ONLY"
assert ok["global_fresh_reality_authority"] is False
assert ok["acceptance_credit_authorized"] is False
assert ok["promotion_authority"] is False
assert ok["terminal_cases_consumed_by_verifier"]==0

dup=atomic.verify_atomic_claim_transaction(plan=plan,preflight_receipt=receipt,activation_receipt=activation,claim_receipt=claim(422))
assert dup["atomic_claim_transaction_pass"] is False
assert dup["case_reveal_authority"] is False

a2=dict(activation); a2["active"]=False
assert atomic.verify_atomic_claim_transaction(plan=plan,preflight_receipt=receipt,activation_receipt=a2,claim_receipt=claim())["atomic_claim_transaction_pass"] is False

c=claim(); c["preflight_binding_sha256"]="0"*64
assert atomic.verify_atomic_claim_transaction(plan=plan,preflight_receipt=receipt,activation_receipt=activation,claim_receipt=c)["atomic_claim_transaction_pass"] is False

c=claim(); c["case_reveal_has_occurred_before_claim"]=True
assert atomic.verify_atomic_claim_transaction(plan=plan,preflight_receipt=receipt,activation_receipt=activation,claim_receipt=c)["atomic_claim_transaction_pass"] is False

print(json.dumps({
 "status":"PASS",
 "exact_subject_blob_count":len(EXPECTED),
 "v3_plan_bound":True,
 "claim_absence_precheck_deleted":True,
 "atomic_201_grants_exact_lease_only":True,
 "duplicate_non_201_fails_closed":True,
 "verified_activation_required":True,
 "preflight_binding_enforced":True,
 "terminal_cases_consumed":0,
 "global_fresh_reality_authority":False,
 "acceptance_credit_authorized":False,
 "promotion_authority":False,
},sort_keys=True))
