from __future__ import annotations
import copy, hashlib, importlib.util, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def blob(path: Path) -> str:
    data=path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()

expected=json.loads((ROOT/"EXPECTED_BRAIN_BLOBS.json").read_text())
mirrors={
 "canonical/runtime/trajectory_failure_typed_ir_candidate_v5.py":ROOT/"candidate.py",
 "canonical/runtime/trajectory_failure_typed_ir_proof_v5.py":ROOT/"proof.py",
 "canonical/tests/test_trajectory_failure_typed_ir_v5.py":ROOT/"test.py",
 "canonical/governance/P1_TYPED_INTERVENTION_ENVELOPE_V5.json":ROOT/"governance.json",
}
actual={k:blob(v) for k,v in mirrors.items()}
assert actual==expected["exact_brain_blobs"], (actual,expected["exact_brain_blobs"])

def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec); assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod

candidate=load_module("candidate",ROOT/"candidate.py")
proof=load_module("proof",ROOT/"proof.py")
gov=json.loads((ROOT/"governance.json").read_text())

cases=proof.suite_cases()
assert len(cases)==192
failures=[]
for case in cases:
    public=proof.public_task(case)
    assert "_oracle" not in public and "_intervention_model" not in public
    out=candidate.solve(public)
    verdict=proof.score_case(case,out)
    if verdict.get("pass") is not True:
        failures.append((case["seed"],verdict,out))
assert failures==[], failures[:5]

scope_cases=[c for c in cases if c["_oracle"]["mechanisms"]["A1"][0]=="SCOPE"]
assert len(scope_cases)==24
assert {c["task"]["domain"] for c in scope_cases}==set(proof.DOMAINS)
for case in scope_cases:
    out=candidate.solve(proof.public_task(case))
    assert proof.score_case(case,out)["pass"] is True

# Missing visible provenance must fail closed.
case=proof.generate_case(61001,pattern="SINGLE",domain="RESEARCH",kind="PROVENANCE")
public=copy.deepcopy(proof.public_task(case))
for row in public["task"]["trajectory"]:
    for check in row["checks"]:
        if check["pass"] is False:
            check["evidence"]=[]
out=candidate.solve(public)
assert out["status"]=="FAIL_CLOSED"
assert proof.score_case(case,out)["pass"] is False

# Extra unfalsifiable diagnosis must be rejected.
case=proof.generate_case(61002,pattern="DELAYED",domain="CODE",kind="SCOPE")
out=candidate.solve(proof.public_task(case))
assert proof.score_case(case,out)["pass"] is True
mut=dict(out); mut["diagnosis"]={"claim":"UNOBSERVABLE_FORCE","falsifiable":False}
verdict=proof.score_case(case,mut)
assert verdict["pass"] is False and verdict["reason"]=="OUTPUT_SCHEMA_NOT_EXACT"

# Interaction needs every root repair.
case=proof.generate_case(61003,pattern="INTERACTION",domain="TOOL_API",kind="SCOPE")
out=candidate.solve(proof.public_task(case))
repairs=out["repair_targets"]
assert len(repairs)==2
assert proof.evaluate_intervention(case,repairs)["rescued"] is True
for repair in repairs:
    assert proof.evaluate_intervention(case,[repair])["rescued"] is False

# Symptom-only repair must not rescue.
case=proof.generate_case(61004,pattern="DELAYED",domain="BROWSER",kind="AUTHORITY")
symptoms=case["_intervention_model"]["downstream_symptom_repairs"]
assert symptoms and proof.evaluate_intervention(case,symptoms)["rescued"] is False

# Ambiguous case must remain non-identifiable.
case=proof.generate_case(61006,pattern="AMBIGUOUS",domain="ARTIFACT",kind="SCOPE")
out=candidate.solve(proof.public_task(case))
assert out["status"]=="AMBIGUOUS" and out["cause_action_id"] is None
assert proof.score_case(case,out)["pass"] is True

assert gov["scope"]["cross_product_case_count"]==192
assert gov["residuals_targeted"]==[
    "P1_EXPLICIT_SCOPE_FAILURE_CLASS",
    "P1_HETEROGENEOUS_INTERVENTION_RESCUE",
]
assert gov["terminal_results_replayed"]==0
assert gov["new_reality_units_consumed"]==0
assert gov["capability_credit_delta"]==0 and gov["family_credit_delta"]==0
assert gov["execution_authority"] is False and gov["promotion_authority"] is False

print(json.dumps({
 "status":"PASS",
 "exact_blob_shas":actual,
 "case_count":192,
 "scope_case_count":24,
 "scope_first_class":"PASS",
 "hidden_intervention_rescue":"PASS",
 "adversarial_checks":"PASS",
 "terminal_results_replayed":0,
 "new_reality_units_consumed":0,
 "credit_delta":0
},indent=2,sort_keys=True))
