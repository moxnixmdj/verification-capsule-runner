from __future__ import annotations
import copy
import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def load(name, rel):
    spec=importlib.util.spec_from_file_location(name, ROOT/rel)
    m=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(m)
    return m

candidate=load("candidate_v6","canonical/runtime/trajectory_failure_typed_ir_candidate_v6.py")
proof=load("proof_v6","canonical/runtime/trajectory_failure_typed_ir_proof_v6.py")

def check(kind, aid, passed, semantics="DIRECT_CONTRACT"):
    return {
        "kind":kind,
        "id":f"{aid}:{kind}",
        "pass":passed,
        "evidence":[f"receipt:{aid}",f"check:{aid}:{kind}"],
        "failure_semantics":semantics,
    }

def row(i, *, reads, writes, deps, failed=None, semantics="DIRECT_CONTRACT"):
    aid=f"A{i}"
    checks=[check("INVARIANT",aid,True)]
    if failed is not None:
        checks.append(check(failed,aid,False,semantics))
    return {
        "step":i,
        "action_id":aid,
        "domain":"TOOL_API",
        "reads":reads,
        "writes":writes,
        "depends_on":deps,
        "dependency_composition":"SEQUENTIAL",
        "checks":checks,
    }

def serial_direct_cofault_case():
    p="tool_api:"
    return {
        "schema":"PROJECT_BRAIN_TRAJECTORY_CAUSAL_IR_SERIAL_COFAULT_COUNTEREXAMPLE_V1",
        "behavior_id":"TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001",
        "task":{
            "domain":"TOOL_API",
            "trajectory":[
                row(0,reads=[],writes=[p+"seed"],deps=[]),
                row(1,reads=[p+"seed"],writes=[p+"scope_state"],deps=["A0"],failed="SCOPE"),
                row(2,reads=[p+"scope_state"],writes=[p+"tool_state"],deps=["A1"],failed="TOOL_CONTRACT"),
                row(3,reads=[p+"tool_state"],writes=[p+"symptom"],deps=["A2"],failed="INVARIANT",semantics="DERIVED_UPSTREAM"),
                row(4,reads=[p+"symptom"],writes=[p+"terminal"],deps=["A3"]),
            ],
            "terminal_failed_resources":[p+"terminal"],
            "goal":"LOCALIZE_CAUSAL_FAILURES_AND_NOMINATE_REPAIR_SET_THAT_ACTUALLY_RESCUES_TERMINAL_OUTCOME",
        },
    }

def test_v6_candidate_drops_downstream_direct_cofault_and_its_repair_does_not_rescue():
    case=serial_direct_cofault_case()
    out=candidate.solve(copy.deepcopy(case))
    assert out["status"]=="IDENTIFIED", out
    assert out["cause_action_ids"]==["A1"], out
    assert out["mechanism_classes"]==["SCOPE"], out
    assert out["repair_targets"]==["restore:A1:SCOPE"], out

    iv=proof.execute_intervention(copy.deepcopy(case),out)
    assert iv["terminal_rescued"] is False, iv
    assert "A2:TOOL_CONTRACT" in iv["active_direct_failures"], iv

    complete=copy.deepcopy(out)
    complete["repair_targets"]=["restore:A1:SCOPE","restore:A2:TOOL_CONTRACT"]
    iv2=proof.execute_intervention(copy.deepcopy(case),complete)
    assert iv2["terminal_rescued"] is True, iv2

def test_counterexample_uses_only_v6_declared_public_mechanisms_and_semantics():
    case=serial_direct_cofault_case()
    kinds={
        c["kind"]
        for r in case["task"]["trajectory"]
        for c in r["checks"]
    }
    assert kinds <= candidate.ALLOWED_KINDS
    failed=[
        c
        for r in case["task"]["trajectory"]
        for c in r["checks"]
        if c["pass"] is False
    ]
    assert [c["failure_semantics"] for c in failed].count("DIRECT_CONTRACT")==2
    assert [c["failure_semantics"] for c in failed].count("DERIVED_UPSTREAM")==1

def test_candidate_parser_ignores_failure_semantics_load_bearing_distinction():
    case=serial_direct_cofault_case()
    out1=candidate.solve(copy.deepcopy(case))
    mutated=copy.deepcopy(case)
    for r in mutated["task"]["trajectory"]:
        for c in r["checks"]:
            if c["pass"] is False:
                c["failure_semantics"]="DERIVED_UPSTREAM"
    out2=candidate.solve(mutated)
    assert out1==out2


if __name__ == "__main__":
    test_v6_candidate_drops_downstream_direct_cofault_and_its_repair_does_not_rescue()
    test_counterexample_uses_only_v6_declared_public_mechanisms_and_semantics()
    test_candidate_parser_ignores_failure_semantics_load_bearing_distinction()
    print("P1 V6 serial direct co-fault counterexample: PASS")
