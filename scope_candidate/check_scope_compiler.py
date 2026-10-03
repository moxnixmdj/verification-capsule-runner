import importlib.util

P="scope_candidate/canonical/runtime/universal_scope_closure_compiler_v1.py"
spec=importlib.util.spec_from_file_location("scopev1",P)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def base(basis, scope):
    return {"id":"c","basis":basis,"verified":True,"independent":True,"scope_relation":"EXACT","target_scope_id":scope}

u=base(m.UNIVERSAL,"u")
u.update(formal_completeness=True,all_admissible_target_inputs_proved=True,premise_set_id="p")
assert m.evaluate(u)["scope_complete"] is True

for key in ("verified","independent","formal_completeness","all_admissible_target_inputs_proved"):
    x=dict(u)
    x[key]=False
    assert m.evaluate(x)["scope_complete"] is False

e=base(m.EXACT,"e")
e.update(complete_target_case_set=True,universe_identity_bound=True,case_universe_digest="sha256:x")
assert m.evaluate(e)["scope_complete"] is True
x=dict(e)
x["complete_target_case_set"]=False
x["sample_pass_rate"]=1.0
assert m.evaluate(x)["scope_complete"] is False

s=base(m.SUPERSET,"s")
s.update(exhaustive=True,target_subset_proved=True,superset_universe_digest="sha256:y")
assert m.evaluate(s)["scope_complete"] is True

d=base(m.DECOMPOSITION,"d")
d.update(coverage_complete=True,coverage_relation="EXACT_UNION",coverage_proof_verified=True,children=[u,e])
assert m.evaluate(d)["scope_complete"] is True

out=m.compile_targets({"targets":[{"predicate_id":"X","scope_certificate":u}]})
assert out["scope_complete_count"]==1
assert out["targets"][0]["performance_state"]=="SEPARATE_UNCHANGED"
assert out["acceptance_credit_delta"]==0
assert out["promotion_authority"] is False
print("PASS")
