from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path

from canonical.runtime.opus55_typed_coverage_dominance_bridge_v1 import compile_typed_sandwich

ROOT = Path(__file__).resolve().parent
EXPECTED = {
    "canonical/governance/OPUS55_TYPED_COVERAGE_DOMINANCE_BRIDGE_20261005_V1.json": "9a53ac18797014456ea985a9f14b8ed26eed9340",
    "canonical/runtime/opus55_typed_coverage_dominance_bridge_v1.py": "35d077bc7451fbbb9b065aef4be3ed0d06c466f2",
    "canonical/tests/test_opus55_typed_coverage_dominance_bridge_v1.py": "bd9c3b48885610ebd204e92f5e824268f56289c7",
}

def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def req(x: bool, msg: str) -> None:
    if not x:
        raise AssertionError(msg)

def powerset(items):
    items=list(items)
    for mask in range(1 << len(items)):
        yield {items[i] for i in range(len(items)) if mask & (1 << i)}

def universe_digest(atoms):
    raw=json.dumps(atoms,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()
    return hashlib.sha256(raw).hexdigest()

def base():
    atoms={"A":"1"*40,"B":"2"*40,"C":"3"*40}
    uhash=universe_digest(atoms)
    return {
        "universe_id":"OMEGA-VERIFY",
        "universe_sha256":uhash,
        "universe_atoms":atoms,
        "coverage_certificates":[{
            "id":"C1","universe_id":"OMEGA-VERIFY","universe_sha256":uhash,
            "source_sha":"a"*40,"cells":["A","B","C"],
            "independent_or_objective":True,"u_subset_domain_proved":True,
        }],
        "dominance_certificates":[{
            "id":"B1","universe_id":"OMEGA-VERIFY","universe_sha256":uhash,
            "source_sha":"b"*40,"cells":["A","B"],
            "independent_or_objective":True,"scope_complete":True,"b_subset_q_proved":True,
        }],
    }

def main():
    for rel,want in EXPECTED.items():
        got=git_blob_sha((ROOT/rel).read_bytes())
        req(got==want,f"blob mismatch {rel}: {got} != {want}")

    gov=json.loads((ROOT/"canonical/governance/OPUS55_TYPED_COVERAGE_DOMINANCE_BRIDGE_20261005_V1.json").read_text())
    req(gov["independent_verification_required"] is True,"independent verification weakened")
    for k in ("scheduling_authority","execution_authority","promotion_authority","fresh_reality_authority"):
        req(gov[k] is False,f"{k} unexpectedly true")
    for k in ("acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta"):
        req(gov["accounting"][k]==0,f"{k} nonzero")
    req(gov["accounting"]["new_reality_units_consumed"]==0,"fresh reality consumed")
    req("NO_LITERAL_TERMINAL_COMPLETION" in gov["hard_nonclaims"],"terminal nonclaim missing")
    req(gov["current_truth_repair"]["current_14_of_38_predicates_are_not_a_global_behavioral_region_universe"] is True,
        "heterogeneous-ledger truth repair missing")
    req("TASK_ACCEPTANCE" in gov["theorem"]["definitions"]["OMEGA"],
        "Omega regressed from task-acceptance semantics")
    req("DO_NOT_USE_AS_THE_DOMINANCE_ORDER" in gov["current_truth_repair"]["protocol_schema_role"],
        "protocol carrier incorrectly promoted to dominance order")

    # Exhaustive theorem check over a 3-atom universe:
    # U⊆C1 and U⊆C2; B1⊆Q and B2⊆Q; if C1∩C2⊆B1∪B2 then U⊆Q.
    atoms=("A","B","C")
    subsets=list(powerset(atoms))
    theorem_cases=0
    premise_cases=0
    for U,C1,C2,B1,B2,Q in itertools.product(subsets, repeat=6):
        theorem_cases += 1
        premise=(U<=C1 and U<=C2 and B1<=Q and B2<=Q and (C1 & C2) <= (B1 | B2))
        if premise:
            premise_cases += 1
            req(U<=Q, f"set theorem counterexample: {U,C1,C2,B1,B2,Q}")

    # Direct compiler set-semantics check over every C/B subset pair.
    exact_compiler_cases=0
    for C in subsets:
        for B in subsets:
            m=base()
            m["coverage_certificates"][0]["cells"]=sorted(C)
            m["dominance_certificates"][0]["cells"]=sorted(B)
            v=compile_typed_sandwich(m)
            req(v["status"]==("CLOSED" if not (C-B) else "OPEN"),f"status wrong C={C} B={B}")
            req(set(v["c_star"])==C,f"C* wrong C={C}")
            req(set(v["b_star"])==B,f"B* wrong B={B}")
            req(set(v["residual"])==(C-B),f"R wrong C={C} B={B}")
            exact_compiler_cases += 1

    adversarial=[]
    m=base(); m["universe_atoms"]["A"]="9"*40
    v=compile_typed_sandwich(m)
    req(v["status"]=="FAIL_CLOSED" and "UNIVERSE_SHA256_CONTENT_MISMATCH" in v["reason"],"atom drift admitted")
    adversarial.append("semantic_atom_drift")

    m=base(); m["dominance_certificates"][0]["universe_sha256"]="f"*64
    v=compile_typed_sandwich(m)
    req(v["status"]=="FAIL_CLOSED" and "UNIVERSE_SHA256_MISMATCH" in v["reason"],"universe digest mismatch admitted")
    adversarial.append("certificate_universe_digest_mismatch")

    m=base(); m["coverage_certificates"][0]["source_sha"]="garbage"
    v=compile_typed_sandwich(m)
    req(v["status"]=="FAIL_CLOSED" and "INVALID_CONTENT_ADDRESS" in v["reason"],"bad source address admitted")
    adversarial.append("invalid_source_content_address")

    m=base(); m["coverage_certificates"][0]["independent_or_objective"]=False
    v=compile_typed_sandwich(m)
    req(v["status"]=="FAIL_CLOSED","non-independent coverage admitted")
    adversarial.append("non_independent_coverage")

    m=base(); m["coverage_certificates"][0]["u_subset_domain_proved"]=False
    v=compile_typed_sandwich(m)
    req(v["status"]=="FAIL_CLOSED","unproved target coverage admitted")
    adversarial.append("unproved_u_subset_coverage")

    m=base(); m["dominance_certificates"][0]["scope_complete"]=False
    v=compile_typed_sandwich(m)
    req(v["status"]=="FAIL_CLOSED","scope-incomplete dominance admitted")
    adversarial.append("scope_incomplete_dominance")

    m=base(); m["dominance_certificates"][0]["b_subset_q_proved"]=False
    v=compile_typed_sandwich(m)
    req(v["status"]=="FAIL_CLOSED","unproved dominance admitted")
    adversarial.append("unproved_b_subset_q")

    m=base(); m["coverage_certificates"][0]["cells"].append("Z")
    v=compile_typed_sandwich(m)
    req(v["status"]=="FAIL_CLOSED" and "UNKNOWN_REGION" in v["reason"],"unknown region admitted")
    adversarial.append("unknown_region")

    print(json.dumps({
        "status":"PASS",
        "brain_pr":2206,
        "brain_head":"da75d8cbb6dbae56b094791bebef401630c470be",
        "exact_blobs":EXPECTED,
        "exhaustive_set_theorem_cases":theorem_cases,
        "premise_satisfying_theorem_cases":premise_cases,
        "exact_compiler_subset_pairs":exact_compiler_cases,
        "adversarial_dimensions":adversarial,
        "semantic_target_coverage_proved":False,
        "brain_global_dominance_proved":False,
        "terminal_completion":False,
        "acceptance_credit_delta":0
    },indent=2))

if __name__=="__main__":
    main()
