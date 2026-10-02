from __future__ import annotations
import hashlib, importlib.util, json, os
from pathlib import Path

ROOT=Path(__file__).resolve().parent
EXPECTED=json.loads((ROOT/"EXPECTED_BRAIN_BLOBS.json").read_text(encoding="utf-8"))

def blob_sha(path: Path) -> str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

for rel, expected in EXPECTED["exact_brain_blobs"].items():
    actual=blob_sha(ROOT/rel)
    assert actual==expected,(rel,actual,expected)

os.chdir(ROOT)

def load(name, rel):
    spec=importlib.util.spec_from_file_location(name, ROOT/rel)
    assert spec and spec.loader
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

c=load("candidate_v5","canonical/runtime/trajectory_failure_typed_ir_candidate_v5.py")
p=load("proof_v5","canonical/runtime/trajectory_failure_typed_ir_proof_v5.py")
t=load("tests_v5","canonical/tests/test_trajectory_failure_typed_ir_v5.py")

exact_test_count=0
for name in sorted(x for x in dir(t) if x.startswith("test_")):
    fn=getattr(t,name)
    if callable(fn):
        fn()
        exact_test_count+=1
assert exact_test_count==7, exact_test_count

cases=p.suite_cases()
assert len(cases)==192
assert set(p.DOMAINS)=={"BROWSER","FILESYSTEM","TOOL_API","ARTIFACT","RESEARCH","CODE"}
assert "SCOPE" in set(p.KINDS)
assert "AUTHORITY" in set(p.KINDS)

nonambiguous=0
ambiguous=0
necessity_checks=0
wrong_kind_checks=0
scope_cases=0

for case in cases:
    public=p.public_task(case)
    assert "_oracle" not in public
    out=c.solve(public)
    verdict=p.score_case(case,out)
    assert verdict["pass"] is True,(case["seed"],verdict,out)

    mechanisms={
        str(kind)
        for kinds in case["_oracle"]["mechanisms"].values()
        for kind in kinds
    }
    if "SCOPE" in mechanisms:
        scope_cases+=1

    if case["_oracle"]["status"]=="AMBIGUOUS":
        ambiguous+=1
        assert out["status"]=="AMBIGUOUS"
        assert out["cause_action_id"] is None
        r=p.intervention_rescue(case,[])
        assert r["applicable"] is False and r["rescued"] is False
        continue

    nonambiguous+=1
    repairs=list(out["repair_targets"])
    full=p.intervention_rescue(case,repairs)
    assert full["applicable"] is True and full["rescued"] is True,(case["seed"],full)

    for i,target in enumerate(repairs):
        ablated=repairs[:i]+repairs[i+1:]
        r=p.intervention_rescue(case,ablated)
        assert r["rescued"] is False,(case["seed"],target,r)
        assert r["unrepaired_hidden_root_defect_count"]>=1
        necessity_checks+=1

        parts=target.split(":",2)
        assert len(parts)==3 and parts[0]=="restore"
        wrong_kind="AUTHORITY" if parts[2]!="AUTHORITY" else "SCOPE"
        wrong=list(repairs)
        wrong[i]=f"restore:{parts[1]}:{wrong_kind}"
        r2=p.intervention_rescue(case,wrong)
        assert r2["rescued"] is False,(case["seed"],target,wrong,r2)
        wrong_kind_checks+=1

assert nonambiguous==144,nonambiguous
assert ambiguous==48,ambiguous
assert necessity_checks>=144,necessity_checks
assert wrong_kind_checks==necessity_checks
assert scope_cases>0

scope_case=p.generate_case(9001,pattern="SINGLE",domain="TOOL_API",kind="SCOPE")
scope_out=c.solve(p.public_task(scope_case))
assert scope_out["status"]=="IDENTIFIED"
assert scope_out["mechanism_classes"]==["SCOPE"]
assert scope_out["repair_targets"]==["restore:A1:SCOPE"]
assert p.intervention_rescue(scope_case,scope_out["repair_targets"])["rescued"] is True
assert p.intervention_rescue(scope_case,["restore:A1:AUTHORITY"])["rescued"] is False

gov=json.loads((ROOT/"canonical/governance/P1_TYPED_IR_V5_SCOPE_RESCUE_ACTIVATION_V1.json").read_text(encoding="utf-8"))
assert gov["targets"]==["P1_EXPLICIT_SCOPE_FAILURE_CLASS","P1_HETEROGENEOUS_INTERVENTION_RESCUE"]
assert gov["terminal_results_observed"]==0
assert gov["fresh_terminal_evidence_consumed"]==0
assert gov["new_reality_units_consumed"]==0
assert gov["capability_credit_delta"]==0
assert gov["family_credit_delta"]==0
assert gov["execution_authority"] is False
assert gov["promotion_authority"] is False

print(json.dumps({
    "status":"PASS",
    "exact_brain_blob_count":len(EXPECTED["exact_brain_blobs"]),
    "exact_brain_regression_tests":exact_test_count,
    "cross_product_cases":len(cases),
    "nonambiguous_intervention_rescue_cases":nonambiguous,
    "ambiguous_abstention_cases":ambiguous,
    "repair_necessity_ablations":necessity_checks,
    "wrong_mechanism_ablations":wrong_kind_checks,
    "scope_cases":scope_cases,
    "scope_distinct_from_authority":True,
    "hidden_oracle_excluded_from_candidate_payload":True,
    "terminal_results_observed":0,
    "new_reality_units_consumed":0,
    "credit_delta":0
},indent=2,sort_keys=True))
