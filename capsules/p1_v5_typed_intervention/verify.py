from __future__ import annotations
import hashlib, importlib.util, json, pathlib, sys

ROOT=pathlib.Path(__file__).resolve().parent
EXPECTED={
  "candidate.py": "2a8613ddac7402c7e6d2f349f9d3c32d3fb95e1d",
  "proof.py": "3fc600a8176dac250219e3d98b92cf93d8fceef5",
  "brain_tests.py": "abc87ada119e42b720af5fb0f472816df975bc25",
  "governance.json": "26cd9f4c626d4754200c64c3f298383580d67c14"
}

def git_blob_sha(path):
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

for name,sha in EXPECTED.items():
    got=git_blob_sha(ROOT/name)
    assert got==sha,(name,got,sha)

def loadmod(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    mod=importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name]=mod
    spec.loader.exec_module(mod)
    return mod

candidate=loadmod("candidate","candidate.py")
proof=loadmod("proof","proof.py")
gov=json.loads((ROOT/"governance.json").read_text(encoding="utf-8"))

cases=proof.suite_cases()
assert len(cases)==192
failures=[]
rescued=0
scope_cases=0
ambiguous=0
for case in cases:
    public=proof.public_task(case)
    assert "_oracle" not in public
    assert "_intervention_model" not in public
    assert "required_root_repairs" not in str(public)
    out=candidate.solve(public)
    verdict=proof.score_case(case,out)
    if verdict.get("pass") is not True:
        failures.append((case["seed"],verdict,out))
    if case["_oracle"]["mechanisms"]["A1"][0]=="SCOPE":
        scope_cases+=1
    if case["_oracle"]["status"]=="AMBIGUOUS":
        ambiguous+=1
        assert out["status"]=="AMBIGUOUS"
        assert out["cause_action_id"] is None
    else:
        iv=proof.evaluate_intervention(case,out["repair_targets"])
        assert iv["rescued"] is True,(case["seed"],iv,out)
        rescued+=1

assert failures==[],failures[:3]
assert scope_cases==24,scope_cases
assert rescued==144,rescued
assert ambiguous==48,ambiguous
assert set(candidate.ALLOWED_KINDS)==set(proof.KINDS)
assert "SCOPE" in candidate.ALLOWED_KINDS
assert gov["scope"]["cross_product_case_count"]==192
assert set(gov["residuals_targeted"])=={
  "P1_EXPLICIT_SCOPE_FAILURE_CLASS",
  "P1_HETEROGENEOUS_INTERVENTION_RESCUE",
}
assert set(gov["counterexamples_targeted"])=={
  "V4_DROP_PROVENANCE_MUTATION_SURVIVES_SCORER",
  "TERMINAL_UNFALSIFIABLE_DIAGNOSIS_MUTATION_SURVIVES_SCORER",
}
print(json.dumps({
 "status":"PASS",
 "exact_brain_blob_count":len(EXPECTED),
 "cross_product_case_count":len(cases),
 "scope_first_class_case_count":scope_cases,
 "nonambiguous_intervention_rescue_count":rescued,
 "ambiguous_nonoverclaim_case_count":ambiguous,
 "residuals_discharged":["P1_EXPLICIT_SCOPE_FAILURE_CLASS","P1_HETEROGENEOUS_INTERVENTION_RESCUE"],
 "counterexamples_killed":["V4_DROP_PROVENANCE_MUTATION_SURVIVES_SCORER","TERMINAL_UNFALSIFIABLE_DIAGNOSIS_MUTATION_SURVIVES_SCORER"],
 "new_reality_units_consumed":0,
 "capability_credit_delta":0,
 "family_credit_delta":0
},indent=2,sort_keys=True))
