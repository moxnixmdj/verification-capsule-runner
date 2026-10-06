from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
EXPECTED={
  "countermodel_governance.json":"14b4fad10884538ad2b5d73a9c1a6787aae965d5",
  "countermodel.py":"28c0d0d9a30210257c8cb6f6e5e7f1bbf417df9e",
  "countermodel_tests.py":"c671df61718130c57bcbfbbe8dc287dfbb47c328",
  "candidate_theorem.json":"41052a99fde4980393adbd76344b9c228453a0a1",
  "candidate_kernel.py":"f697d7a8280d416010b67a49a852b61b05fb15b9",
}

def blob_sha(path:Path)->str:
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def load(name:str,path:str):
    spec=importlib.util.spec_from_file_location(name,HERE/path)
    if spec is None or spec.loader is None: raise RuntimeError("IMPORT_SPEC_FAILED:"+name)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

def main()->None:
    for name,expected in EXPECTED.items():
        got=blob_sha(HERE/name)
        assert got==expected,(name,got,expected)

    theorem=json.loads((HERE/"candidate_theorem.json").read_text())
    gov=json.loads((HERE/"countermodel_governance.json").read_text())
    candidate=load("candidate","candidate_kernel.py")
    counter=load("counter","countermodel.py")

    defs=theorem["definitions"]
    assert "SET_OF_OUTCOME_EQUIVALENCE_CLASSES" in defs["achievable_set"]
    assert "reliability" in defs["task_preorder"].lower()

    # Current executable candidate kernel represents frontier elements only as
    # numeric points and applies coordinatewise >=; it contains no probability law.
    assert candidate.Point == tuple[float, ...]
    assert candidate.owned_frontier_simulates(((0.0,1.0),),((0.0,1.0),)) is True

    out=counter.stochastic_reliability_countermodel()
    assert out["same_outcome_support"] is True
    assert out["same_point_pareto_frontier"] == (1.0,)
    assert out["point_frontier_simulation_passes"] is True
    assert out["opus_success_probability"] == 0.99
    assert out["brain_success_probability"] == 0.51
    assert out["terminal_reliability_noninferiority_passes"] is False
    assert out["countermodel_valid"] is True

    compiled=counter.compile_countermodel()
    assert compiled["status"]=="PASS__POINT_SUPPORT_FRONTIER_INSUFFICIENT_FOR_STOCHASTIC_RELIABILITY"
    assert compiled["terminal_credit"] is False

    # Scope the falsification precisely: the theorem can be repaired if an
    # outcome point is explicitly a distribution/reliability-bearing object.
    assert "LIFT_ACHIEVABLE_SET_FROM_POINT_SUPPORT_TO_POLICY_INDUCED_OUTCOME_DISTRIBUTIONS_OR_AN_EQUIVALENT_PROBABILISTIC_OBJECT" in gov["minimum_repair"]
    assert "NO_CLAIM_THE_GENERAL_OUTCOME_FRONTIER_DIRECTION_IS_WRONG" in gov["hard_nonclaims"]
    assert "NO_CLAIM_A_DISTRIBUTION_LEVEL_SUCCESSOR_THEOREM_IS_PROVED" in gov["hard_nonclaims"]

    print(json.dumps({
      "status":"PASS",
      "verified":[
        "CURRENT_FINITE_POINT_FRONTIER_KERNEL_DOES_NOT_ENCODE_STOCHASTIC_RELIABILITY",
        "IDENTICAL_SUPPORT_FRONTIERS_CAN_HIDE_A_0_99_VS_0_51_SUCCESS_PROBABILITY_GAP",
        "POINT_SUPPORT_READING_IS_INSUFFICIENT",
        "DISTRIBUTION_LEVEL_REPAIR_REMAINS_POSSIBLE_AND_UNPROVED",
        "ZERO_TERMINAL_CREDIT"
      ]
    },indent=2,sort_keys=True))

if __name__=="__main__": main()
