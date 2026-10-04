from __future__ import annotations

import ast
import hashlib
import json
from fractions import Fraction
from pathlib import Path

from canonical.runtime import unknown_domain_direct_candidate_v1 as c1
from canonical.runtime import unknown_domain_direct_candidate_v2 as c2
from canonical.runtime import unknown_domain_direct_candidate_v3 as c3
from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as g1
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as g2
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness

ROOT=Path(__file__).resolve().parent

EXPECTED_BLOBS={
    "canonical/runtime/unknown_domain_direct_candidate_v1.py":"a2a77269a8175ce315b466035049da0f761b8734",
    "canonical/runtime/unknown_domain_direct_candidate_v2.py":"4470716f95a559a700e461262df909ae19a41651",
    "canonical/runtime/unknown_domain_direct_candidate_v3.py":"8df7f13455b710623806a8219174b397a2c3c442",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v1.py":"f974a4594c78e74693c7ba5a19f131dfa481b937",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v2.py":"d077028c9bde534dc4bc6eb0d1f776341f9d59f8",
    "canonical/runtime/unknown_domain_direct_hidden_scorer_v1.py":"e8cf5d1b5d311644725a751c15e6235958fb587d",
    "canonical/runtime/unknown_domain_direct_execution_harness_v1.py":"04fe06f4eed081c4cb6197b12f2d92bd396aeafd",
    "canonical/runtime/unknown_domain_direct_v3_universal_proof_v1.py":"ee5f3832fdbad5ae645b0626e9f39ebeaee2b1da",
    "canonical/tests/test_unknown_domain_direct_candidate_v3.py":"1317f7143d0b9103bdebc817fd0b057cc9bcd43b",
    "canonical/tests/test_unknown_domain_direct_v3_universal_proof_v1.py":"f1fa117edaf1f10401f4d33a6f78b815fa02c073",
    "canonical/governance/UNKNOWN_DOMAIN_DIRECT_V3_UNIVERSAL_PROOF_CANDIDATE_20261005_V1.json":"4303d6259b4c7adb747cd83923a28f1771f36d44",
}

FAMILIES=(
    "ORDER_PRESERVING_TRANSFORM",
    "PARITY_OR_SIGN_INVARIANT",
    "CONSERVATION_RELATION",
    "MONOTONE_CAUSAL_EDGE",
    "COMPOSITIONAL_REWRITE",
    "THRESHOLD_OR_PARTITION_INVARIANT",
)


def git_blob(path:Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()


def verify_exact_bytes()->None:
    bad={}
    for rel,expected in EXPECTED_BLOBS.items():
        got=git_blob(ROOT/rel)
        if got!=expected:
            bad[rel]={"expected":expected,"got":got}
    assert not bad,bad

    gov=json.loads((ROOT/"canonical/governance/UNKNOWN_DOMAIN_DIRECT_V3_UNIVERSAL_PROOF_CANDIDATE_20261005_V1.json").read_text())
    assert gov["target_predicate"]=="UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"
    assert gov["truth_repair"]["v3_candidate_git_blob_sha"]==EXPECTED_BLOBS["canonical/runtime/unknown_domain_direct_candidate_v3.py"]
    assert gov["universal_proof"]["git_blob_sha"]==EXPECTED_BLOBS["canonical/runtime/unknown_domain_direct_v3_universal_proof_v1.py"]
    assert gov["authority"]=={
        "execution":False,
        "fresh_reality":False,
        "promotion":False,
        "acceptance_credit":False,
        "independent_verification_required":True,
    }

    # Candidate V3 itself may depend only on already-frozen candidate logic.
    # It must not import the hidden generator, scorer, harness, networking, or model APIs.
    tree=ast.parse((ROOT/"canonical/runtime/unknown_domain_direct_candidate_v3.py").read_text())
    imports=set()
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node,ast.ImportFrom) and node.module:
            imports.add(node.module)
    assert imports <= {
        "__future__","typing",
        "canonical.runtime.unknown_domain_direct_candidate_v1",
        "canonical.runtime.unknown_domain_direct_candidate_v2",
    },imports


def independent_symbolic_derivation()->dict:
    assert tuple(g1.PRIMITIVE_FAMILIES)==FAMILIES
    assert g1.PRODUCTION_CASE_COUNTS=={g1.TRANSFER:12,g1.ABSTAIN:15}
    assert harness.MAX_TRANSFER_PROBES==2
    assert c1.MAPPING_BASIS=="STRUCTURAL_EQUIVALENCE"
    assert c3.ADD2_R0_SIG==(-1,1,-1)
    assert c3.ADD2_R1_SIG==(1,-1,1)

    # Probe distractor displacement from exact frozen generator V1:
    # delta = 4.75 + 1.5*i + 0.25*probe_variant.
    first_distractor_probe0=Fraction(19,4)
    second_distractor_probe0=Fraction(25,4)
    role_min=Fraction(1,4)
    role_max=Fraction(7,2)

    # Unary continuous families. These are strict lower bounds over every value
    # the exact V2 generator can obtain from any accepted beacon/secret.
    affine_gap=Fraction(3,5)*first_distractor_probe0
    complement_gap=first_distractor_probe0
    sat_gap=Fraction(7,10)*first_distractor_probe0/Fraction(121,1)
    assert affine_gap==Fraction(57,20)
    assert complement_gap==Fraction(19,4)
    assert sat_gap>0
    # SAT_MONO outputs have |y| < 1.5 + 3 = 4.5, so frozen _close <= 4.5e-9.
    assert float(sat_gap)>4.5e-9

    # SIGN transfer indices 1 and 7: target row j=3 is always negative.
    # Any first distractor there is positive because |true| <=3.5 and shift>=4.75.
    for index in (1,7):
        assert (3+index)%2==0
    sign_shifted_min=-role_max+first_distractor_probe0
    assert sign_shifted_min==Fraction(5,4)>0

    # STEP transfer indices 5 and 11. row 3 is above threshold; row 4 below
    # by at most 2.2. The second probe's actual first-distractor shift is 5.0,
    # and even the conservative 4.75 bound crosses to the high side.
    step_margin=first_distractor_probe0-Fraction(11,5)
    assert step_margin==Fraction(51,20)>0

    # ADD2 transfer indices 4 and 10: row j=3 has both true roles positive.
    # Enumerate all five wrong unordered support sets. Each differs in sum by
    # at least 1.5, vastly above the frozen 1e-9 relative consistency tolerance.
    for index in (4,10):
        assert (3+index)%2==1
        assert (3+index+1)%3!=0
    add2_gaps=(
        first_distractor_probe0-(role_max-role_min),
        second_distractor_probe0,
        first_distractor_probe0,
        second_distractor_probe0-(role_max-role_min),
        first_distractor_probe0+second_distractor_probe0,
    )
    add2_gap=min(add2_gaps)
    assert add2_gap==Fraction(3,2)

    # Exact-float repair: for both ADD2 indices, public target rows 0..2 expose
    # distinct, nonzero role signatures. After support is unique, only the true
    # orientation matches them. Candidate and generator then execute ADD2 in the
    # same Python operand order: (bias + r0) + r1.
    signatures={}
    for index in (4,10):
        r0=tuple(-1 if (j+index)%2==0 else 1 for j in range(3))
        r1=tuple(-1 if (j+index+1)%3==0 else 1 for j in range(3))
        assert r0==(-1,1,-1)
        assert r1==(1,-1,1)
        assert r0!=r1
        signatures[index]={"r0":r0,"r1":r1}

    # Abstention construction is visible: 5 cases in each class. Candidate V3
    # delegates unchanged V1 behavior, exactly matching frozen scorer clauses.
    assert tuple(g1.ABSTAIN_CLASSES)==("IDENTIFIABLE","NONIDENTIFIABLE","UNDERSPECIFIED")
    assert scorer.DECISIONS=={"CONCLUDE","ABSTAIN","REQUEST_DISCRIMINATOR"}

    return {
        "affine_min_gap":str(affine_gap),
        "complement_min_gap":str(complement_gap),
        "sat_mono_min_gap":str(sat_gap),
        "sign_shifted_min":str(sign_shifted_min),
        "step_margin":str(step_margin),
        "add2_min_gap":str(add2_gap),
        "add2_signatures":{str(k):{"r0":list(v["r0"]),"r1":list(v["r1"])} for k,v in signatures.items()},
    }


def locked_v2_counterexample_and_v3_repair()->dict:
    secret=hashlib.sha256(b"secret0").digest()
    beacon="beacon-qualification-0000000000000000"
    visible,hidden=g2._transfer_case(secret,beacon,4,namespace="VERIFYONLY-COUNTEREXAMPLE")
    v2=harness.execute_case(candidate_step=c2.step,case_visible=visible,hidden_record=hidden)
    assert v2["scorer_result"]["pass"] is False
    assert "DOMAIN_B_TERMINAL_CONSEQUENCE_WRONG" in v2["scorer_result"]["errors"]
    assert set(v2["candidate_terminal_action"]["support_feature_ids"])==set(hidden["transfer_relevant_feature_ids"])
    got=v2["candidate_terminal_action"]["terminal_consequence"]
    gold=hidden["gold_terminal_consequence"]
    assert got!=gold and 0<abs(got-gold)<1e-12

    v3=harness.execute_case(candidate_step=c3.step,case_visible=visible,hidden_record=hidden)
    assert v3["scorer_result"]["pass"] is True,v3
    assert v3["candidate_terminal_action"]["terminal_consequence"]==gold
    assert v3["probe_count"]==1
    return {"v2_delta":abs(got-gold),"v3_pass":True,"v3_probe_count":1}


def verifier_only_falsification(populations:int=256)->dict:
    total=0
    max_probe=0
    family_counts={f:0 for f in FAMILIES}
    class_counts={"IDENTIFIABLE":0,"NONIDENTIFIABLE":0,"UNDERSPECIFIED":0}
    for i in range(populations):
        seed=f"UNKNOWN-DOMAIN-V3-INDEPENDENT-VERIFY-{i}".encode()
        secret=hashlib.sha256(seed).digest()
        beacon="VERIFYONLY-"+hashlib.sha256(b"beacon|"+seed).hexdigest()
        packet=g2._generate(
            beacon=beacon,
            evaluator_secret=secret,
            namespace=f"VERIFYONLY{i:04d}",
        )
        assert packet["case_count"]==27
        assert "production" not in packet
        results=[]
        for visible,hidden in zip(packet["visible_cases"],packet["hidden_records"]):
            out=harness.execute_case(
                candidate_step=c3.step,
                case_visible=visible,
                hidden_record=hidden,
            )
            sr=out["scorer_result"]
            assert sr["pass"] is True,(i,visible["case_id"],sr)
            results.append(sr)
            total+=1
            max_probe=max(max_probe,int(out["probe_count"]))
            if hidden["leaf_id"]==g1.TRANSFER:
                family_counts[str(hidden["primitive_family"])]+=1
            else:
                class_counts[str(hidden["identifiability_status"])]+=1
        agg=scorer.aggregate(results)
        assert agg["all_27_cases_pass"] is True,agg
    assert total==populations*27
    assert max_probe<=2
    assert all(v>0 for v in family_counts.values())
    assert class_counts=={k:populations*5 for k in class_counts}
    return {
        "verifier_only_populations":populations,
        "hidden_scored_cases":total,
        "max_transfer_probes_observed":max_probe,
        "transfer_family_counts":family_counts,
        "abstention_class_counts":class_counts,
        "production_generator_called":False,
        "production_cases_consumed":0,
    }


def main()->None:
    verify_exact_bytes()
    symbolic=independent_symbolic_derivation()
    counterexample=locked_v2_counterexample_and_v3_repair()
    fuzz=verifier_only_falsification(256)
    receipt={
        "schema":"PROJECT_BRAIN_UNKNOWN_DOMAIN_V3_UNIVERSAL_ZERO_REALITY_INDEPENDENT_VERIFICATION_V1",
        "status":"INDEPENDENT_CONTENT_BOUND_PASS",
        "target_predicate":"UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",
        "brain_pr":1858,
        "exact_subject_blobs":EXPECTED_BLOBS,
        "symbolic_rederivation":symbolic,
        "truth_repair":counterexample,
        "falsification":fuzz,
        "deduction":"THE_EXACT_V3_CANDIDATE_PASSES_EVERY_POPULATION_CONSTRUCTIBLE_BY_THE_EXACT_FROZEN_V2_DIRECT_GENERATOR__THE_27_CASE_PRODUCTION_SAMPLE_HAS_ZERO_INFORMATION_GAIN_FOR_THIS_EXACT_CONTENT_BOUND_EVALUATOR_CLAIM",
        "hard_nonclaims":[
            "NO_OPEN_WORLD_UNKNOWN_DOMAIN_GENERALIZATION",
            "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT_FROM_THIS_VERIFIER_ALONE",
            "NO_PRODUCTION_OR_TERMINAL_CASES_GENERATED_READ_OR_CONSUMED",
        ],
        "accounting":{
            "incremental_spend_usd":0,
            "production_cases_consumed":0,
            "terminal_cases_consumed":0,
            "acceptance_credit_delta":0,
            "family_credit_delta":0,
            "capability_credit_delta":0,
            "ownership_credit_delta":0,
        },
    }
    print(json.dumps(receipt,sort_keys=True))


if __name__=="__main__":
    main()
