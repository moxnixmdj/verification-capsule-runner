from fractions import Fraction
import importlib.util
import json
import pathlib
import subprocess

FILES = {
    "theorem": "subject/FINANCE_INDEX_DIRECT_THRESHOLD_THEOREM_V1.json",
    "runtime": "subject/finance_index_direct_threshold_v1.py",
    "tests": "subject/test_finance_index_direct_threshold_v1.py",
    "residual": "subject/FINANCE_INDEX_COMPONENTWISE_RESIDUAL_VECTOR_V1.json",
    "identity": "subject/FINANCE_ACCOUNTING_INDEX_IDENTITY_RECONCILIATION_V1.json",
    "aggregation": "subject/FINANCE_INDEX_MONOTONE_AGGREGATION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
}
EXPECTED = {
    "theorem": "37f47143f62fe2f59e56d8eca4a64bae18a1ce8b",
    "runtime": "57cbcc0f45c0823ab38d1ef3939d2e66f891faeb",
    "tests": "359aa1daa772ea1f108605fd1373a9f305e7e6e6",
    "residual": "1f8b7ebd377ba06548d46399f62ed883c49dc0c3",
    "identity": "dcd910e2af97c1648ab29d614552b072c66d647e",
    "aggregation": "ebe67fc336d905b347790db8499b143c28d08345",
}

def blob(path):
    return subprocess.check_output(["git","rev-parse",f"HEAD:{path}"], text=True).strip()

for key,path in FILES.items():
    got=blob(path)
    assert got==EXPECTED[key], (key,got,EXPECTED[key])

theorem=json.loads(pathlib.Path(FILES["theorem"]).read_text())
residual=json.loads(pathlib.Path(FILES["residual"]).read_text())
identity=json.loads(pathlib.Path(FILES["identity"]).read_text())
agg=json.loads(pathlib.Path(FILES["aggregation"]).read_text())

assert theorem["target_predicate"]=="FINANCE_ACCOUNTING_INDEX_GE_61"
assert theorem["target"]=="61"
assert theorem["authority"]["identity_blob"]==EXPECTED["identity"]
assert theorem["authority"]["weighted_average_verification_blob"]==EXPECTED["aggregation"]
assert theorem["authority"]["prior_residual_blob"]=="c386e8f792170bd5a249d7e10d7d4df9d3a41c78"

published={x["capability"]:Fraction(str(x["weight"])) for x in identity["resolved_identity"].get("published_composition", identity["published_composition"])}
# identity file stores published_composition at top level in current schema.
if not published:
    published={x["capability"]:Fraction(str(x["weight"])) for x in identity["published_composition"]}
candidate={k:Fraction(v) for k,v in theorem["weights"].items()}
name_map={
    "BUSINESS_KNOWLEDGE":"Business Knowledge",
    "AGENTIC_KNOWLEDGE_WORK":"Agentic Knowledge Work",
    "REASONING":"Reasoning",
    "AGENTIC_TOOL_USE":"Agentic Tool Use",
    "LONG_CONTEXT":"Long-Context",
    "NON_HALLUCINATION":"Non-Hallucination",
}
assert {name_map[k]:v for k,v in candidate.items()}==published
assert sum(candidate.values(), Fraction(0))==1
assert all(v>=0 for v in candidate.values())
assert identity["resolved_identity"]["opus55_target"]==61
assert identity["resolved_identity"]["higher_is_better"] is True
assert agg["verified"]["aggregation_kind"]=="PUBLISHED_WEIGHTED_AVERAGE"
assert agg["verified"]["all_weights_nonnegative"] is True
assert agg["verified"]["weight_sum"]==1

# The proof: if true component scores B_i >= independently verified lower bounds L_i,
# then nonnegative weights imply sum(w_i B_i) >= sum(w_i L_i). Therefore any
# verified lower-bound weighted sum >= 61 is sufficient for the published index >= 61.
assert theorem["theorem"]=="IF_VERIFIED_NORMALIZED_BRAIN_LOWER_BOUNDS_L_i_SATISFY_SUM_i(w_i*L_i)>=61_THEN_FINANCE_ACCOUNTING_INDEX_GE_61"
assert theorem["componentwise_opus_noninferiority"]=="SUFFICIENT_BUT_NOT_NECESSARY"
assert theorem["opus_component_values_required_for_direct_route"] is False
assert theorem["compensation_across_components_allowed"] is True

spec=importlib.util.spec_from_file_location("finance_threshold", FILES["runtime"])
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

names=list(mod.WEIGHTS)
def rows(vals, verified=True):
    return {n:{"verified":verified,"lower_bound":v,"receipt":"sha256:"+n} for n,v in zip(names,vals)}

out=mod.compile_verified_lower_bounds(rows([61,61,61,61,61,61]))
assert out["mathematically_sufficient"] is True
assert Fraction(out["weighted_lower_bound"])==61

# Compensation proves componentwise Opus dominance is not necessary.
out=mod.compile_verified_lower_bounds(rows([100,100,5,0,0,0]))
assert out["mathematically_sufficient"] is True
assert Fraction(out["weighted_lower_bound"])==61
assert out["componentwise_opus_noninferiority_required"] is False

out=mod.compile_verified_lower_bounds(rows([60,60,60,60,60,60]))
assert out["mathematically_sufficient"] is False

for mutate in ("missing","extra","unverified","empty_receipt","boolean"):
    x=rows([61]*6)
    if mutate=="missing": x.pop(names[-1])
    elif mutate=="extra": x["EXTRA"]={"verified":True,"lower_bound":100,"receipt":"x"}
    elif mutate=="unverified": x[names[0]]["verified"]=False
    elif mutate=="empty_receipt": x[names[0]]["receipt"]=""
    elif mutate=="boolean": x[names[0]]["lower_bound"]=True
    try:
        mod.compile_verified_lower_bounds(x)
        raise AssertionError("expected fail closed: "+mutate)
    except mod.FinanceThresholdError:
        pass

assert residual["target_predicate"]=="FINANCE_ACCOUNTING_INDEX_GE_61"
shortcut=residual["direct_threshold_shortcut"]
assert shortcut["theorem_path"]=="canonical/governance/FINANCE_INDEX_DIRECT_THRESHOLD_THEOREM_V1.json"
assert shortcut["componentwise_opus_noninferiority"]=="SUFFICIENT_BUT_NOT_NECESSARY"
assert shortcut["opus_component_values_required_for_direct_route"] is False
assert shortcut["status"]=="CANDIDATE__INDEPENDENT_VERIFICATION_REQUIRED"

# This verifier explicitly does NOT validate any future component receipt.
# It validates only the algebraic implication conditional on independently
# verified lower-bound premises.
for obj in (theorem,residual):
    assert obj["acceptance_credit_delta"]==0
    assert obj["execution_authority"] is False
    assert obj["promotion_authority"] is False
    assert obj["fresh_reality_authority"] is False

print("PASS: Finance direct weighted-threshold theorem is sound conditional on independently verified normalized component lower bounds")
print("PASS: componentwise Opus dominance is sufficient but not necessary")
print("PASS: compensation across components is mathematically valid")
print("PASS: no component receipt, score, acceptance, ownership, or fresh-reality credit is inferred")
