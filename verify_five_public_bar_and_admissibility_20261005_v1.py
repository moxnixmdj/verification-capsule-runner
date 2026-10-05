from __future__ import annotations
import hashlib, importlib.util, itertools, json, pathlib, sys

ROOT=pathlib.Path(__file__).resolve().parent
SUB=ROOT/"subject"/"five_public_bar_admissibility"
P=lambda rel: SUB/rel

EXPECTED={
"canonical/governance/FIVE_PUBLIC_BAR_OBSERVABLE_TARGET_SCOPE_CLOSURE_REDUCTION_20261005_V1.json":"26de060b9469bb1f0e650d0a5b4611280cfc54e3",
"canonical/runtime/five_public_bar_observable_target_scope_closure_verifier_v1.py":"99566ffba312d28100d6c15a985ed1f5dc210d3b",
"canonical/tests/test_five_public_bar_observable_target_scope_closure_verifier_v1.py":"3e1fce6be3691d6428915d44b58a7447c11f6f2e",
"canonical/capabilities/opus55/OPUS_5_5_USEFUL_CAPABILITY_ENVELOPE_V1.json":"661a57f839101fbf54c7e4edc76166c65ce9327d",
"canonical/governance/PUBLIC_BAR_TASK_UNION_SCOPE_COVERAGE_AUDIT_20261005_V1.json":"2295a03fe9090e6842c6bd850b7bca67d1f71131",
"canonical/governance/TARGET_BEHAVIOR_MECHANISM_SCOPE_SEPARATION_20261005_V1.json":"251cac9c9f7892e26ca90f2f5118f31e1df02099",
"canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json":"a3fd20e58fdbd9b86278b7de0c245de3063dce27",
"canonical/verification/PUBLIC_BAR_TASK_UNION_TARGET_CONDITIONED_RESIDUAL_RECONCILIATION_CONNECTOR_VERIFICATION_20261005_V1.json":"a037a51b9860b4a8404c7dc5bed3a93b290070a8",
"canonical/governance/TERMINAL_PROGRESS_ADMISSIBILITY_CUT_20261005_V1.json":"b90898cd88e9e89936bfdb0b3f7e5bf60238f08d",
"canonical/governance/OPUS55_TARGET_DISCOVERY_MINIMUM_INFORMATION_CUT_20261005_V1.json":"644550da2fe9637fc760ea82bf4f34f6892a8c5a",
"canonical/governance/TARGET_SUPERSET_COVERAGE_DOMINANCE_NORMAL_FORM_20261005_V1.json":"55a027d50e6f9d1c4d70a75b39d6a536e26a4277",
"canonical/verification/OPUS55_W3_DOMAIN_PREMISE_COLLAPSE_WOLFRAM_VERIFICATION_20261005_V1.json":"d3163328bad39f1a5a9a5885e488f9514eb65f77",
}

def blob(path:pathlib.Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def need(ok,msg):
    if not ok:
        raise AssertionError(msg)

for rel,sha in EXPECTED.items():
    need(P(rel).exists(),"missing:"+rel)
    need(blob(P(rel))==sha,"blob drift:"+rel)

# Run the subject's own deterministic verifier against the frozen copy.
modpath=P("canonical/runtime/five_public_bar_observable_target_scope_closure_verifier_v1.py")
spec=importlib.util.spec_from_file_location("scopev",modpath)
mod=importlib.util.module_from_spec(spec); assert spec.loader is not None; spec.loader.exec_module(mod)
subject_result=mod.verify(SUB)
need(subject_result["status"]=="PASS","subject verifier did not pass")
need(subject_result["family_count"]==5,"family count")

cand=json.loads(P("canonical/governance/FIVE_PUBLIC_BAR_OBSERVABLE_TARGET_SCOPE_CLOSURE_REDUCTION_20261005_V1.json").read_text())
bindings=json.loads(P("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json").read_text())
guard=json.loads(P("canonical/governance/TARGET_BEHAVIOR_MECHANISM_SCOPE_SEPARATION_20261005_V1.json").read_text())

# Independent anti-overclaim checks the subject verifier does not itself enforce.
need("DEFAULT_PUBLIC_BENCHMARK_PROFILE_STRUCTURAL_SCOPE_ONLY" in cand["status"],"profile-conditioned status missing")
need(cand["aggregate"]["global_profile_union_structural_scope_closed"] is False,"U_star falsely closed")
need(cand["aggregate"]["default_public_benchmark_profile_structural_scope_closed_candidate"] is True,"default-profile candidate not preserved")
need(cand["aggregate"]["public_performance_predicates_deleted"]==0,"performance predicate deletion")
need(cand["aggregate"]["target_epoch_or_harness_guards_deleted"]==0,"target identity guard deletion")
need("NO_U_STAR_PROFILE_UNION_SCOPE_CLOSURE" in cand["hard_nonclaims"],"U_star nonclaim missing")
need(all(f.get("structural_scope_residuals")==[] for f in cand["families"]),"scope residual not empty")
need(all(bool(f.get("remaining_load_bearing")) for f in cand["families"]),"load-bearing obligations deleted")

claim={x["predicate_id"]:x for x in bindings["claims"]}
for fam in cand["families"]:
    for rec in fam.get("stronger_observable_receipts",[]):
        c=claim.get(rec["predicate"])
        need(c is not None and c.get("state")=="PROVED" and c.get("scope_complete") is True,"invalid stronger receipt:"+rec["predicate"])

edges={(e["family"],e["behavior_id"]):e for e in guard["current_frontier_audit"]["edges"]}
for fam in cand["families"]:
    for mech in fam.get("nonmandatory_mechanisms",[]):
        e=edges.get((fam["family"],mech))
        need(e is not None and e.get("mandatory_from_registry_incidence") is False,"nonmandatory mechanism not justified:"+fam["family"]+":"+mech)

# Conditional verification of the terminal admissibility theorem.
adm=json.loads(P("canonical/governance/TERMINAL_PROGRESS_ADMISSIBILITY_CUT_20261005_V1.json").read_text())
mic=json.loads(P("canonical/governance/OPUS55_TARGET_DISCOVERY_MINIMUM_INFORMATION_CUT_20261005_V1.json").read_text())
nf=json.loads(P("canonical/governance/TARGET_SUPERSET_COVERAGE_DOMINANCE_NORMAL_FORM_20261005_V1.json").read_text())
w3=json.loads(P("canonical/verification/OPUS55_W3_DOMAIN_PREMISE_COLLAPSE_WOLFRAM_VERIFICATION_20261005_V1.json").read_text())

need(adm.get("independent_verification_required") is True,"admissibility self-authorized")
need(all(adm.get(k) is False for k in ("scheduling_authority","execution_authority","promotion_authority","fresh_reality_authority")),"admissibility authority nonzero")
need(adm["theorem"]["definitions"]["T"]=="C_AND_E","T definition drift")
need(adm["theorem"]["definitions"]["C_normal_form"]=="W1_OR_W2_OR_W3","C normal form drift")
ids=[x["id"] for x in mic["minimal_sufficient_witness_classes"]]
need(ids==["W1_TARGET_OWNER_EXHAUSTIVE_BEHAVIOR_SPECIFICATION","W2_IMPLEMENTATION_LEVEL_COMPLETE_CHARACTERIZATION","W3_UNIVERSAL_BEHAVIORAL_DOMINANCE_THEOREM"],"witness-class list drift")
need(nf["current_verdict"]["target_coverage_certificate_proved"] is False,"coverage silently promoted")
need(nf["current_verdict"]["domain_dominance_proved"] is False,"dominance silently promoted")
need(w3["checks"]["with_subset_premise"]["pass"] is True and w3["checks"]["without_subset_premise"]["pass"] is True,"W3 premise verification absent")

# Exhaustively check the conditional state-transition theorem for three live E conjuncts:
# if C and each E conjunct are unchanged by action A, T=C AND all(E) cannot change.
for bits in itertools.product([False,True], repeat=4):
    c,*es=bits
    t=c and all(es)
    c2=c; es2=list(es)
    need((c2 and all(es2))==t,"conditional admissibility theorem counterexample")

out={
 "schema":"PROJECT_BRAIN_FIVE_PUBLIC_BAR_AND_ADMISSIBILITY_INDEPENDENT_VERIFICATION_20261005_V1",
 "status":"PASS__FIVE_PUBLIC_BAR_PROFILE_CONDITIONED_SCOPE_REDUCTION__PASS_CONDITIONAL_ADMISSIBILITY_THEOREM__NO_GLOBAL_WITNESS_CLASS_EXHAUSTIVENESS_CREDIT",
 "subject_scope_check_count":subject_result["check_count"],
 "profile_union_scope_closed":False,
 "public_performance_credit":False,
 "admissibility_conditional_logic_pass":True,
 "witness_class_exhaustiveness_independently_proved":False,
 "reason_for_conditional_only":"The state-transition theorem is valid conditional on the minimum-information-cut premise; this verifier does not prove that no fourth logically sufficient completeness witness class exists.",
 "promotion_authority":False,
 "execution_authority":False,
 "fresh_reality_authority":False,
 "acceptance_credit_delta":0,
}
print(json.dumps(out,sort_keys=True,indent=2))
