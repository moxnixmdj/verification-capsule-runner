from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as generator
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer
from canonical.runtime import unknown_domain_direct_candidate_v1 as candidate

ROOT=Path(__file__).resolve().parent

EXPECTED={
  "canonical/runtime/unknown_domain_direct_candidate_v1.py":"a2a77269a8175ce315b466035049da0f761b8734",
  "canonical/tests/test_unknown_domain_direct_candidate_v1.py":"88cf44844b4d0f4e3e899d04205c87a7fc967b1d",
  "canonical/governance/UNKNOWN_DOMAIN_DIRECT_CANDIDATE_QUALIFICATION_V1.json":"666e7bb9e512a16d6da0ab011a06145d724ec16b",
  "canonical/governance/UNKNOWN_DOMAIN_DIRECT_EVALUATOR_FAMILY_V1.json":"52090daf78d12020af48c1b6ffaea056d9029e1b",
  "canonical/runtime/unknown_domain_direct_hidden_scorer_v1.py":"e8cf5d1b5d311644725a751c15e6235958fb587d",
  "canonical/governance/UNKNOWN_DOMAIN_DIRECT_GENERATOR_FREEZE_V1.json":"26108d0d06f7a308c3eaf4b9821ff0c4551dcda3",
  "canonical/runtime/unknown_domain_direct_hidden_generator_v1.py":"f974a4594c78e74693c7ba5a19f131dfa481b937",
  "canonical/governance/UNKNOWN_DOMAIN_DIRECT_GENERATOR_FREEZE_V2.json":"6bf6042a7a36c12d6d5ebfc5d16ea23ed2befbb6",
  "canonical/runtime/unknown_domain_direct_hidden_generator_v2.py":"d077028c9bde534dc4bc6eb0d1f776341f9d59f8",
  "canonical/governance/UNKNOWN_DOMAIN_DIRECT_EXECUTION_HARNESS_FREEZE_V1.json":"3e3a87962c13ad4c76621508763fab74df25cb44",
  "canonical/runtime/unknown_domain_direct_execution_harness_v1.py":"04fe06f4eed081c4cb6197b12f2d92bd396aeafd",
}

FRESH_BEACONS=[
  "INDEPENDENT-QUALIFICATION-D-271828182845",
  "INDEPENDENT-QUALIFICATION-E-161803398874",
  "INDEPENDENT-QUALIFICATION-F-141421356237",
]

def blob(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def verify_exact_bytes():
    for rel,expected in EXPECTED.items():
        got=blob((ROOT/rel).read_bytes())
        assert got==expected,(rel,got,expected)

def run_population(beacon:str):
    packet=generator.generate_qualification_fixture_population(beacon=beacon)
    assert packet["production"] is False,packet
    assert packet["case_count"]==27,packet
    results=[]
    for visible,hidden in zip(packet["visible_cases"],packet["hidden_records"]):
        out=harness.execute_case(
            candidate_step=candidate.step,
            case_visible=visible,
            hidden_record=hidden,
        )
        results.append(out["scorer_result"])
    agg=scorer.aggregate(results)
    assert agg["all_27_cases_pass"] is True,agg
    assert agg["transfer_leaf_pass"] is True,agg
    assert agg["abstention_leaf_pass"] is True,agg
    return agg

if __name__=="__main__":
    verify_exact_bytes()
    subprocess.check_call([
      "python","-m","unittest",
      "canonical.tests.test_unknown_domain_direct_candidate_v1","-v",
    ])
    rows=[run_population(x) for x in FRESH_BEACONS]
    print(json.dumps({
      "status":"INDEPENDENT_CANDIDATE_QUALIFICATION_PASS",
      "fresh_population_count":len(rows),
      "fresh_case_count":sum(r["case_count"] for r in rows),
      "all_27_cases_pass_each":all(r["all_27_cases_pass"] for r in rows),
      "transfer_leaf_pass_each":all(r["transfer_leaf_pass"] for r in rows),
      "abstention_leaf_pass_each":all(r["abstention_leaf_pass"] for r in rows),
      "persistent_learned_bytes":0,
      "external_frontier_model_calls":0,
      "external_learned_capability_calls":0,
      "production_cases_generated":0,
    },indent=2,sort_keys=True))
