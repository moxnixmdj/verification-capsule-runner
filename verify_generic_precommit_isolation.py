from __future__ import annotations
import hashlib, importlib.util, itertools, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SUB=ROOT/"subject"/"generic_precommit_isolation_20261004_sol"
EXPECTED={
 "THEOREM.json":"0da944ca987ef249557057ed31343c8f26b7f009",
 "RUNTIME.py":"58f2ae9c3f0ef0ac55da2e58d0ed81ae88560296",
 "TEST.py":"e404f46007483dff129af71b10b1377cab37a835",
}
def git_blob_sha(p:Path)->str:
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
for n,s in EXPECTED.items():
    got=git_blob_sha(SUB/n)
    assert got==s,(n,got,s)

theorem=json.loads((SUB/"THEOREM.json").read_text())
spec=importlib.util.spec_from_file_location("candidate",SUB/"RUNTIME.py")
m=importlib.util.module_from_spec(spec); assert spec and spec.loader
spec.loader.exec_module(m)

assert theorem["theorem"]["quantified_domain"]=="ANY_BENCHMARK_OR_EVALUATION_PROTOCOL"
assert theorem["theorem"]["proof_boundary"]=="GENERIC_ADAPTATION_INDEPENDENCE_ONLY"
assert len(theorem["benchmark_thin_adapter_required"])==7
for x in (
 "NO_CLAIM_ANY_CURRENT_BENCHMARK_ALREADY_INSTANTIATES_THE_THEOREM",
 "NO_CLAIM_BENCHMARK_PROTOCOL_COMPARABILITY",
 "NO_FRESH_REALITY_AUTHORITY",
 "NO_EXECUTION_OR_PROMOTION_AUTHORITY",
 "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
):
    assert x in theorem["hard_nonclaims"]
assert all(v==0 for v in theorem["accounting"].values())

def base():
    r={}
    for i,c in enumerate(m.COMPONENTS,start=1):
        r[f"{c}_sha256"]=str(i)*64
        r[f"observed_{c}_sha256"]=str(i)*64
    r.update({
      "commit_event_sequence":10,
      "case_reveal_event_sequence":11,
      "execution_start_event_sequence":12,
      "independent_executor":True,
      "committed_components_immutable":True,
      "no_case_or_evaluation_feedback_to_committed_components":True,
      "unrelated_work_cannot_mutate_committed_components":True,
      "outputs_bound_to_commitment":True,
      "observed_causal_edges":[
        ["case_content","execution_output"],
        ["evaluation_output","receipt_store"],
        ["unrelated_zero_reality_work","unrelated_artifact"],
      ],
    })
    r["commitment_sha256"]=m.commitment_digest(r)
    return r

def adapter():
    return {k:True for k in (
      "population_identity_verified","scorer_or_grader_equivalence_verified",
      "effort_and_context_semantics_verified","tool_and_environment_boundary_verified",
      "exact_comparator_identity_verified","no_proxy_substitution_verified",
      "zero_incremental_spend_or_entitlement_verified","acceptance_rule_bound",
    )}

ok=m.verify_generic_isolation(base())
assert ok["generic_isolation_kernel_pass"] is True
assert ok["conditional_adaptation_independence_proved"] is True
assert ok["benchmark_comparability_proved"] is False
assert ok["fresh_reality_authority"] is False
assert ok["execution_authority"] is False
assert ok["promotion_authority"] is False
assert ok["acceptance_credit_authorized"] is False

# Every source->committed-component direct feedback edge must be rejected.
for src,component in itertools.product(m.SOURCES,m.COMPONENTS):
    r=base(); r["observed_causal_edges"].append([src,component])
    out=m.verify_generic_isolation(r)
    assert out["generic_isolation_kernel_pass"] is False,(src,component)
    assert f"FORBIDDEN_CAUSAL_PATH:{src}->{component}" in out["reasons"]

# Every source->shared->component indirect feedback path must also be rejected.
for src,component in itertools.product(m.SOURCES,m.COMPONENTS):
    r=base(); r["observed_causal_edges"].extend([[src,"shared_mutable_state"],["shared_mutable_state",component]])
    out=m.verify_generic_isolation(r)
    assert out["generic_isolation_kernel_pass"] is False,(src,component)

# All invalid reveal/commit orderings are rejected; exact strict order passes.
for commit,reveal,execute in [(10,10,11),(11,10,12),(10,12,11),(12,11,10)]:
    r=base(); r["commit_event_sequence"]=commit; r["case_reveal_event_sequence"]=reveal; r["execution_start_event_sequence"]=execute
    assert m.verify_generic_isolation(r)["generic_isolation_kernel_pass"] is False

# Drift in every committed component is rejected.
for component in m.COMPONENTS:
    r=base(); r[f"observed_{component}_sha256"]="f"*64
    out=m.verify_generic_isolation(r)
    assert out["generic_isolation_kernel_pass"] is False
    assert f"EXECUTED_{component.upper()}_DIFFERS_FROM_COMMITTED" in out["reasons"]

# Generic isolation and benchmark semantics remain separate.
ad=adapter()
assert m.verify_benchmark_thin_adapter(ad)["benchmark_thin_adapter_pass"] is True
for k in list(ad):
    bad=dict(ad); bad[k]=False
    assert m.verify_benchmark_thin_adapter(bad)["benchmark_thin_adapter_pass"] is False

# Concurrency readiness is conjunctive and the module itself grants no authority.
assert m.concurrency_admissibility(base(),adapter(),explicit_fresh_reality_authority=False)["concurrent_collection_ready"] is False
ready=m.concurrency_admissibility(base(),adapter(),explicit_fresh_reality_authority=True)
assert ready["concurrent_collection_ready"] is True
assert ready["fresh_reality_authority_granted_by_this_module"] is False
bad=adapter(); bad["exact_comparator_identity_verified"]=False
assert m.concurrency_admissibility(base(),bad,explicit_fresh_reality_authority=True)["concurrent_collection_ready"] is False

print(json.dumps({
 "status":"PASS",
 "exact_candidate_blobs":EXPECTED,
 "direct_forbidden_paths_checked":len(m.SOURCES)*len(m.COMPONENTS),
 "indirect_forbidden_paths_checked":len(m.SOURCES)*len(m.COMPONENTS),
 "component_drift_checks":len(m.COMPONENTS),
 "generic_conditional_isolation_theorem":True,
 "benchmark_comparability_separate":True,
 "fresh_reality_authority":False,
 "acceptance_credit_delta":0,
},sort_keys=True))
