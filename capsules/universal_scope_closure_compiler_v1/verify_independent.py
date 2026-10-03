from __future__ import annotations
from canonical.runtime.universal_scope_closure_compiler_v1 import (
    UNIVERSAL, EXACT, SUPERSET, DECOMPOSITION, evaluate, compile_targets
)

def base(basis, scope="S"):
    return {
        "id":"C::"+scope, "basis":basis, "verified":True, "independent":True,
        "scope_relation":"EXACT", "target_scope_id":scope,
    }

# Positive bases.
u=base(UNIVERSAL,"U"); u.update(formal_completeness=True,all_admissible_target_inputs_proved=True,premise_set_id="P")
e=base(EXACT,"E"); e.update(complete_target_case_set=True,universe_identity_bound=True,case_universe_digest="sha256:e")
s=base(SUPERSET,"X"); s.update(exhaustive=True,target_subset_proved=True,superset_universe_digest="sha256:x")
for c in (u,e,s):
    out=evaluate(c)
    assert out["scope_complete"] is True, out
    assert out["performance_credit"] is False, out
    assert out["acceptance_credit_delta"]==0 and out["family_credit_delta"]==0
    assert out["capability_credit_delta"]==0 and out["ownership_credit_delta"]==0
    assert out["execution_authority"] is False and out["promotion_authority"] is False
    assert out["fresh_reality_authority"] is False

# Lossless decomposition is all-children, not sample optimism.
d=base(DECOMPOSITION,"D")
d.update(coverage_complete=True,coverage_relation="EXACT_UNION",coverage_proof_verified=True,children=[u,e,s])
assert evaluate(d)["scope_complete"] is True
bad=dict(d); bad["coverage_complete"]=False
assert evaluate(bad)["scope_complete"] is False

# Adversarial mutations must fail closed.
mutations=[]
for key,val in [
    ("verified",False),("independent",False),("scope_relation","OVERLAP_ONLY"),
    ("target_scope_id",""),("basis","MAGIC")
]:
    c=dict(u); c[key]=val; mutations.append(c)
sample=base(EXACT,"SAMPLE"); sample.update(complete_target_case_set=False,universe_identity_bound=True,case_universe_digest="sha256:sample",sample_pass_rate=1.0)
mutations.append(sample)
univ_missing=base(UNIVERSAL,"UP"); univ_missing.update(formal_completeness=True,all_admissible_target_inputs_proved=True,premise_set_id="")
mutations.append(univ_missing)
sup_missing=base(SUPERSET,"SP"); sup_missing.update(exhaustive=True,target_subset_proved=False,superset_universe_digest="sha256:sp")
mutations.append(sup_missing)
dup=base(DECOMPOSITION,"DUP"); dup.update(coverage_complete=True,coverage_relation="EXACT_UNION",coverage_proof_verified=True,children=[u,dict(u)])
mutations.append(dup)
for c in mutations:
    assert evaluate(c)["scope_complete"] is False, c

compiled=compile_targets({"targets":[{"predicate_id":"P", "scope_certificate":u}]})
assert compiled["scope_complete_count"]==1
assert compiled["targets"][0]["performance_state"]=="SEPARATE_UNCHANGED"
assert compiled["acceptance_credit_delta"]==0
assert compiled["promotion_authority"] is False
print("UNIVERSAL_SCOPE_CLOSURE_COMPILER_INDEPENDENT_ADVERSARIAL_PASS")
