#!/usr/bin/env python3
import importlib.util, json, pathlib, subprocess, sys, types

BASE=pathlib.Path("subject/synthesis_dimension_scorers_reducer_20261004_sol")
FILES={
 "contract":BASE/"CONTRACT.json",
 "runtime":BASE/"RUNTIME.py",
 "test":BASE/"TEST.py",
 "aggregator":BASE/"AGGREGATOR.py",
}
EXPECTED={
 "contract":"8206cb013b5cd0d653ffa70d1e867f8c4d4630b8",
 "runtime":"3e2c155e76a2a2965bd340f1fb93b7c4abc0c721",
 "test":"c20c3087ab8ad2eb85b5b449d2ce7093967ddada",
 "aggregator":"116b7394f4b0a6845056c798e966f4cc26f294bf",
}
def blob(p):
    return subprocess.check_output(["git","rev-parse",f"HEAD:{p.as_posix()}"],text=True).strip()
for k,p in FILES.items():
    got=blob(p)
    assert got==EXPECTED[k],(k,got,EXPECTED[k])

# Load frozen aggregator under its canonical import name.
canonical=types.ModuleType("canonical")
runtime_pkg=types.ModuleType("canonical.runtime")
canonical.runtime=runtime_pkg
sys.modules["canonical"]=canonical
sys.modules["canonical.runtime"]=runtime_pkg

spec=importlib.util.spec_from_file_location(
  "canonical.runtime.synthesis_matched_quality_metric_v1", FILES["aggregator"]
)
agg=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=agg
spec.loader.exec_module(agg)

spec2=importlib.util.spec_from_file_location("candidate",FILES["runtime"])
m=importlib.util.module_from_spec(spec2)
sys.modules[spec2.name]=m
spec2.loader.exec_module(m)

x=json.loads(FILES["contract"].read_text())
assert x["schema"]=="PROJECT_BRAIN_SYNTHESIS_DIMENSION_SCORERS_AND_STRICT_REDUCER_V1"
assert x["target_predicate"]=="SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR"
assert x["portfolio_reducer"]["logical_role"]=="SUFFICIENT_ONLY_STRONGER_CONDITION_FOR_MATCHED_QUALITY_NONINFERIORITY"
assert x["portfolio_reducer"]["failure_role"].startswith("FAILURE_DOES_NOT_PROVE_INFERIORITY")
assert len(x["deleted_after_activation_if_verified"])==2
assert all(v==0 for v in x["accounting"].values())
assert x["execution_authority"] is False
assert x["promotion_authority"] is False
assert x["fresh_reality_authority"] is False

BASE_FACTS={
 "total_material_claims":4,
 "supported_material_claims":4,
 "correctly_provenanced_material_claims":4,
 "unsupported_material_claims":0,
 "total_required_uncertainty_units":2,
 "preserved_required_uncertainty_units":2,
 "total_audience_requirements":2,
 "satisfied_audience_requirements":2,
 "total_format_style_constraints":3,
 "satisfied_format_style_constraints":3,
 "total_required_decision_relevant_units":5,
 "retained_decision_relevant_units":5,
 "output_budget_pass":True,
}

perfect=m.score_case(BASE_FACTS)
assert perfect["matched_quality"]==1.0
assert all(v==1.0 for v in perfect["components"].values())

bad=dict(BASE_FACTS); bad["unsupported_material_claims"]=1
assert m.score_case(bad)["matched_quality"]==0.0

half=dict(BASE_FACTS); half["preserved_required_uncertainty_units"]=1
assert m.score_case(half)["matched_quality"]==0.5

budget=dict(BASE_FACTS); budget["output_budget_pass"]=False
assert m.score_case(budget)["matched_quality"]==0.0

# Exact same scorer is applied symmetrically to Brain and Opus.
pass_out=m.strict_paired_dominance({"a":BASE_FACTS,"b":BASE_FACTS},{"a":half,"b":BASE_FACTS})
assert pass_out["sufficient_noninferiority_pass"] is True
assert pass_out["worst_case_delta"]==0.0

fail_out=m.strict_paired_dominance({"a":half},{"a":BASE_FACTS})
assert fail_out["sufficient_noninferiority_pass"] is False
assert fail_out["failure_is_negative_capability_verdict"] is False

try:
    m.strict_paired_dominance({"a":BASE_FACTS},{"b":BASE_FACTS})
    raise AssertionError("CASE_SET_MISMATCH_NOT_REJECTED")
except ValueError as e:
    assert "CASE_ID_SET_MISMATCH" in str(e)

bad_count=dict(BASE_FACTS); bad_count["supported_material_claims"]=5
try:
    m.score_case(bad_count)
    raise AssertionError("INVALID_COUNT_NOT_REJECTED")
except ValueError:
    pass

print("PASS: exact synthesis scorer/reducer candidate blobs verified")
print("PASS: five deterministic evaluator-side scorers normalize fail-closed")
print("PASS: strict paired reducer is sufficient-only and symmetric")
print("PASS: reducer failure is not a negative capability verdict")
print("PASS: zero cases, zero spend, zero credit, no execution/fresh-reality authority")
