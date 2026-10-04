#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SUB=ROOT/"subject/unknown_domain_collision_total_v3_20261005"
sys.path.insert(0,str(SUB))

from canonical.runtime import unknown_domain_direct_candidate_v2 as candidate
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as g1
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as g2
from canonical.runtime import unknown_domain_direct_hidden_generator_v3 as g3
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer
from canonical.runtime import unknown_domain_direct_v3_universal_proof_v2 as proof

BEACON="INDEPENDENT-COLLISION-TOTAL-VERIFIER-20261005"

def execute_population(pop):
    results=[]
    assert pop["case_count"]==27
    assert len(pop["visible_cases"])==len(pop["hidden_records"])==27
    assert len({x["case_id"] for x in pop["visible_cases"]})==27
    for visible,hidden in zip(pop["visible_cases"],pop["hidden_records"]):
        ex=harness.execute_case(
            candidate_step=candidate.step,
            case_visible=visible,
            hidden_record=hidden,
        )
        sr=ex["scorer_result"]
        assert sr["pass"] is True,(visible["case_id"],sr,ex)
        results.append(sr)
    agg=scorer.aggregate(results)
    assert agg["all_27_cases_pass"] is True,agg
    return agg

def lo(secret,beacon,lower,upper,*parts):
    return lower

def hi(secret,beacon,lower,upper,*parts):
    return upper

def mid(secret,beacon,lower,upper,*parts):
    return (lower+upper)/2.0

def alternating(secret,beacon,lower,upper,*parts):
    key="|".join(map(str,parts))
    return lower if sum(map(ord,key))%2==0 else upper

def main():
    theorem=proof.prove(SUB)
    assert theorem["status"]=="PASS__UNIVERSAL_OVER_COLLISION_TOTAL_V3_GENERATOR_DOMAIN"
    assert theorem["scope"]["terminal_or_production_cases_generated"]==0
    assert theorem["identifier_proof"]["independent_of_truncated_hmac_collision_freedom"] is True

    ordinary_v2=g2.generate_qualification_fixture_population(beacon=BEACON)
    ordinary_v3=g3.generate_qualification_fixture_population(beacon=BEACON)
    assert ordinary_v3["visible_cases"]==ordinary_v2["visible_cases"]
    assert ordinary_v3["hidden_records"]==ordinary_v2["hidden_records"]
    execute_population(ordinary_v3)

    range_results={}
    collision_results={}
    original_range=g2._range
    original_token=g1._token
    try:
        for name,fn in (("lo",lo),("hi",hi),("mid",mid),("alternating",alternating)):
            g2._range=fn
            pop=g3.generate_qualification_fixture_population(beacon=BEACON+"-"+name)
            range_results[name]=execute_population(pop)["status"]

        def total_collision(secret,beacon,*parts,width=14):
            return "f"*width

        g1._token=total_collision
        for name,fn in (("lo",lo),("hi",hi),("mid",mid),("alternating",alternating)):
            g2._range=fn
            pop=g3.generate_qualification_fixture_population(
                beacon=BEACON+"-TOTAL-COLLISION-"+name
            )
            collision_results[name]=execute_population(pop)["status"]

        extreme=g3._disambiguate(
            "X-",
            [(f"k{i}","deadbeef","same-rank") for i in range(64)],
        )
        assert len(extreme)==len(set(extreme.values()))==64
    finally:
        g2._range=original_range
        g1._token=original_token

    receipt={
        "schema":"INDEPENDENT_UNKNOWN_DOMAIN_COLLISION_TOTAL_V3_VERIFICATION_20261005",
        "status":"PASS",
        "subject_blobs":proof.EXPECTED_BLOBS,
        "universal_theorem_status":theorem["status"],
        "ordinary_v2_packet_preservation":True,
        "ordinary_27_case_exact_scorer_pass":True,
        "boundary_range_regimes":range_results,
        "forced_total_raw_token_collision_regimes":collision_results,
        "forced_collision_case_executions":4*27,
        "boundary_case_executions":4*27,
        "terminal_or_production_cases_generated":0,
        "acceptance_credit_delta":0
    }
    print(json.dumps(receipt,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
