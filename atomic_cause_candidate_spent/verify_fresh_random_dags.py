#!/usr/bin/env python3
from __future__ import annotations

import json
import random
from pathlib import Path

from brain_owned_candidate import intervenable_decision_ancestors
from pyrapide import Computation, Event
from pyrapide.analysis.queries import backward_slice

HERE = Path(__file__).resolve().parent
SEED = 202610010821
CASES = 1000


def donor_candidates(events, target_id):
    comp = Computation()
    by_id = {}
    for raw in events:
        e = Event(
            id=raw["id"],
            name=raw["name"],
            source=raw["role"],
            metadata={
                "role": raw["role"],
                "intervenable": raw["intervenable"],
            },
        )
        comp.record(e, caused_by=[by_id[p] for p in raw["caused_by"]] or None)
        by_id[raw["id"]] = e
    sliced = backward_slice(comp, by_id[target_id])
    members = {e.id for e in sliced.events}
    return {
        raw["id"]
        for raw in events
        if raw["id"] != target_id
        and raw["id"] in members
        and raw["intervenable"]
        and raw["role"] == "decision"
    }


def generate_case(rng, case_index):
    n = rng.randint(2, 30)
    events = []
    for i in range(n):
        eid = f"c{case_index}_e{i}"
        if i == 0:
            parents = []
        else:
            candidates = list(range(i))
            rng.shuffle(candidates)
            max_parents = min(4, i)
            k = rng.randint(0, max_parents)
            parents = sorted(candidates[:k])
        role = rng.choice(["observation", "decision", "execution", "memory"])
        intervenable = role == "decision" and rng.random() < 0.7
        events.append({
            "id": eid,
            "name": f"{role}.{i}",
            "role": role,
            "intervenable": intervenable,
            "caused_by": [f"c{case_index}_e{p}" for p in parents],
        })
    # Target is always a fresh failure event caused by 1-3 existing events, so
    # the test queries a nontrivial upstream slice even when the random DAG has
    # several independent components.
    parent_count = rng.randint(1, min(3, n))
    parents = sorted(rng.sample(range(n), parent_count))
    target = f"c{case_index}_fail"
    events.append({
        "id": target,
        "name": "verifier.failure",
        "role": "failure",
        "intervenable": False,
        "caused_by": [f"c{case_index}_e{p}" for p in parents],
    })
    return events, target


def main():
    rng = random.Random(SEED)
    mismatches = []
    total_brain_candidates = 0
    total_donor_candidates = 0
    nonempty = 0

    for i in range(CASES):
        events, target = generate_case(rng, i)
        brain = set(intervenable_decision_ancestors(events, target))
        donor = donor_candidates(events, target)
        total_brain_candidates += len(brain)
        total_donor_candidates += len(donor)
        nonempty += bool(donor)
        if brain != donor:
            mismatches.append({
                "case": i,
                "brain_only": sorted(brain - donor),
                "donor_only": sorted(donor - brain),
                "brain": sorted(brain),
                "donor": sorted(donor),
            })
            if len(mismatches) >= 20:
                break

    result = {
        "schema":"PROJECT_BRAIN_CAUSE_CANDIDATE_FRESH_RANDOM_DAG_DIFFERENTIAL_V1",
        "status":"FRESH_STRUCTURAL_DIFFERENTIAL__ZERO_FAMILY_CREDIT",
        "seed":SEED,
        "generated_cases":CASES,
        "candidate_source_blob_sha":"a35f17a3c4c4cab557f886e0825d74621cd081df",
        "donor":{
            "repo":"ShaneDolphin/pyrapide",
            "revision":"d1dc66efbefe3442e247ac896416bf00c25d3ca1",
            "license":"MIT",
        },
        "mismatch_count":len(mismatches),
        "exact_set_equivalence_fraction":1.0 - (len(mismatches)/CASES),
        "nonempty_candidate_case_fraction":nonempty/CASES,
        "total_brain_candidates":total_brain_candidates,
        "total_donor_candidates":total_donor_candidates,
        "mismatches":mismatches,
        "donor_runtime_required_by_candidate":False,
        "external_runtime_dependencies_of_candidate":[],
        "interpretation_rule":"PASS_VERIFIES_THE_BRAIN_OWNED_NARROW_EXPLICIT_CAUSAL_DAG_TRANSFORM_OVER_FRESH_RANDOM_STRUCTURES__IT_DOES_NOT_PROVE_CAUSAL_EDGE_DISCOVERY_OR_GENERAL_ROOT_CAUSE_INTELLIGENCE",
        "capability_credit_delta":0,
    }
    (HERE/"fresh_random_dag_result.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({
        "generated_cases":CASES,
        "mismatch_count":len(mismatches),
        "exact_set_equivalence_fraction":result["exact_set_equivalence_fraction"],
        "nonempty_candidate_case_fraction":result["nonempty_candidate_case_fraction"],
        "total_brain_candidates":total_brain_candidates,
        "total_donor_candidates":total_donor_candidates,
    },indent=2))
    return 0 if not mismatches and total_brain_candidates == total_donor_candidates else 1


if __name__ == "__main__":
    raise SystemExit(main())
