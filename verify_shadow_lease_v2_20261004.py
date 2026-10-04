from __future__ import annotations
import hashlib, importlib.util, json, sys, types
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SUB=ROOT/"subject"/"shadow_lease_v2_20261004"
FILES={
 "generic":(SUB/"generic_precommit_isolation_theorem_v1.py","58f2ae9c3f0ef0ac55da2e58d0ed81ae88560296"),
 "plan":(SUB/"pre_exposure_isolation_plan_v1.py","f23d632d2ad315b0c800587cd4bb09376a41f085"),
 "lease":(SUB/"shadow_reality_lease_v2.py","8a13e29ddc160ea4af62aed434fb8a1a65afb998"),
}
def blob(path):
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
for _,(p,expected) in FILES.items():
    assert blob(p)==expected,(p,blob(p),expected)

canonical=types.ModuleType("canonical")
runtime=types.ModuleType("canonical.runtime")
canonical.runtime=runtime
sys.modules["canonical"]=canonical
sys.modules["canonical.runtime"]=runtime

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    assert spec and spec.loader
    mod=importlib.util.module_from_spec(spec)
    sys.modules[name]=mod
    spec.loader.exec_module(mod)
    return mod

generic=load("canonical.runtime.generic_precommit_isolation_theorem_v1",FILES["generic"][0])
planmod=load("canonical.runtime.pre_exposure_isolation_plan_v1",FILES["plan"][0])
leasev2=load("canonical.runtime.shadow_reality_lease_v2",FILES["lease"][0])

SHA40="a"*40
def receipt(path): return {"path":path,"git_blob_sha":SHA40}

def mkplan():
    x={"schema":planmod.SCHEMA}
    for i,c in enumerate(("candidate","harness","scorer","environment","policy"),start=1):
        x[f"{c}_sha256"]=str(i)*64
        x[f"pre_reveal_observed_{c}_sha256"]=str(i)*64
    x.update({
      "commit_event_sequence":10,
      "pre_reveal_verification_event_sequence":20,
      "case_reveal_has_occurred":False,
      "execution_has_started":False,
      "evaluation_output_exists":False,
      "independent_executor_bound":True,
      "committed_components_immutable":True,
      "candidate_mutation_blocked":True,
      "unrelated_work_mutation_blocked":True,
      "terminal_case_source_inaccessible_before_claim":True,
      "reveal_step_requires_verified_activation":True,
      "reveal_step_requires_verified_one_use_claim":True,
      "reveal_step_requires_point_of_use_preflight_pass":True,
      "outputs_bound_to_commitment_and_lease":True,
      "write_only_escrow_sink_bound":True,
      "result_read_blocked_until_zero_reality_fixed_point":True,
      "post_execution_isolation_receipt_mandatory":True,
      "fail_closed_on_any_component_drift":True,
      "workflow_control_receipt":receipt("verification/workflow.json"),
      "escrow_contract_receipt":receipt("verification/escrow.json"),
    })
    x["commitment_sha256"]=planmod.commitment_digest(x)
    x["plan_sha256"]=planmod.plan_digest(x)
    return x

def adapter():
    return {
      "population_identity_verified":True,
      "scorer_or_grader_equivalence_verified":True,
      "effort_and_context_semantics_verified":True,
      "tool_and_environment_boundary_verified":True,
      "exact_comparator_identity_verified":True,
      "no_proxy_substitution_verified":True,
      "zero_incremental_spend_or_entitlement_verified":True,
      "acceptance_rule_bound":True,
    }

def activation():
    return {
      "schema":leasev2.AUTHORITY_SCHEMA,
      "active":True,
      "shadow_collection_authority":True,
      "independent_verification_pass":True,
      "zero_incremental_spend_only":True,
      "write_only_escrow_only":True,
      "two_phase_isolation_protocol_required":True,
      "durable_one_use_claim_backend_verified":True,
      "point_of_use_preflight_required":True,
      "post_execution_isolation_receipt_required":True,
      "global_fresh_reality_authority":False,
      "acceptance_credit_authority":False,
      "promotion_authority":False,
      "independent_verification_receipt":receipt("verification/activation.json"),
      "claim_backend_verification_receipt":receipt("verification/claim-backend.json"),
    }

def mklease(p):
    x={
      "lease_id":"shadow:livebench-if:epoch-1",
      "benchmark_id":"LIVEBENCH_IF_GE_65_7",
      "candidate_sha256":"1"*64,
      "benchmark_contract_sha256":"b"*64,
      "population_manifest_sha256":"c"*64,
      "escrow_sink_contract_sha256":"d"*64,
      "pre_exposure_plan_sha256":p["plan_sha256"],
      "one_use_nonce":"nonce-001",
      "lease_claimed":False,
      "case_reveal_has_occurred":False,
      "result_exists":False,
      "candidate_frozen":True,
      "candidate_mutation_blocked":True,
      "unrelated_work_mutation_blocked":True,
      "zero_incremental_spend_guard_bound":True,
      "independent_executor_bound":True,
      "one_use_lease":True,
      "escrow_write_only":True,
      "result_read_blocked_until_zero_reality_fixed_point":True,
      "outputs_bound_to_lease":True,
      "point_of_use_preflight_required":True,
      "post_execution_isolation_receipt_required":True,
    }
    x["lease_digest_sha256"]=leasev2.lease_digest(x)
    return x

def mkclaim(l):
    x={
      "schema":leasev2.CLAIM_SCHEMA,
      "lease_digest_sha256":l["lease_digest_sha256"],
      "one_use_nonce":l["one_use_nonce"],
      "claim_store_key":"claims/"+l["lease_digest_sha256"],
      "preflight_event_sequence":30,
      "claim_event_sequence":31,
      "case_reveal_has_occurred":False,
      "execution_has_started":False,
      "durable_unique_insert_succeeded":True,
      "claim_backend_independently_verified":True,
      "point_of_use_preflight_pass":True,
      "claim_store_previously_absent":True,
      "claim_backend_receipt":receipt("verification/claim-backend.json"),
    }
    x["claim_digest_sha256"]=leasev2.claim_digest(x)
    return x

# V2 plan is a real pre-exposure state and grants no reveal authority.
p=mkplan()
pv=planmod.verify_pre_exposure_plan(p)
assert pv["pre_exposure_plan_pass"] is True
assert pv["case_reveal_authority"] is False
assert pv["fresh_reality_authority"] is False
assert pv["acceptance_credit_authorized"] is False

# A supplied future-event sequence is categorically invalid pre-exposure.
bad=dict(p)
bad["case_reveal_event_sequence"]=21
bad["plan_sha256"]=planmod.plan_digest(bad)
bv=planmod.verify_pre_exposure_plan(bad)
assert bv["pre_exposure_plan_pass"] is False
assert "FUTURE_EVENT_FIELD_FORBIDDEN_PRE_EXPOSURE:case_reveal_event_sequence" in bv["reasons"]

# Whole-plan mutation is detectable.
mut=dict(p)
mut["candidate_mutation_blocked"]=False
mv=planmod.verify_pre_exposure_plan(mut)
assert mv["pre_exposure_plan_pass"] is False
assert "PLAN_DIGEST_MISMATCH" in mv["reasons"]

# Preclaim readiness explicitly does not grant reveal authority.
l=mklease(p)
pre=leasev2.verify_preclaim_readiness(l,p,adapter(),activation())
assert pre["preclaim_ready"] is True,pre
assert pre["case_reveal_authority"] is False
assert pre["one_use_claim_required"] is True
assert pre["acceptance_credit_authorized"] is False

# The one-use claim is the only stage that may grant shadow reveal authority.
cl=mkclaim(l)
cv=leasev2.verify_one_use_claim(cl,l,preclaim_ready=pre["preclaim_ready"])
assert cv["one_use_claim_pass"] is True,cv
assert cv["case_reveal_authority"] is True
assert cv["global_fresh_reality_authority"] is False
assert cv["acceptance_credit_authorized"] is False

# Claim must be backed by a durable unique insertion.
badcl=dict(cl)
badcl["durable_unique_insert_succeeded"]=False
badcl["claim_digest_sha256"]=leasev2.claim_digest(badcl)
bcv=leasev2.verify_one_use_claim(badcl,l,preclaim_ready=True)
assert bcv["one_use_claim_pass"] is False
assert bcv["case_reveal_authority"] is False
assert "DURABLE_UNIQUE_INSERT_NOT_PROVED" in bcv["reasons"]

# Claim after reveal is invalid.
late=dict(cl)
late["case_reveal_has_occurred"]=True
late["claim_digest_sha256"]=leasev2.claim_digest(late)
lv=leasev2.verify_one_use_claim(late,l,preclaim_ready=True)
assert lv["one_use_claim_pass"] is False
assert lv["case_reveal_authority"] is False

print(json.dumps({
  "status":"PASS",
  "pre_exposure_plan_blob":FILES["plan"][1],
  "shadow_lease_v2_blob":FILES["lease"][1],
  "generic_post_receipt_dependency_blob":FILES["generic"][1],
  "future_event_fields_rejected_pre_exposure":True,
  "whole_plan_digest_enforced":True,
  "preclaim_grants_case_reveal_authority":False,
  "durable_unique_claim_required":True,
  "claim_must_precede_case_reveal":True,
  "global_fresh_reality_authority":False,
  "acceptance_credit_authorized":False
},sort_keys=True))
