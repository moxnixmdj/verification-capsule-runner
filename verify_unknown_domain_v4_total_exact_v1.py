from __future__ import annotations

import ast
import hashlib
import inspect
import itertools
import json
from fractions import Fraction
from pathlib import Path

from canonical.runtime import unknown_domain_direct_candidate_v1 as c1
from canonical.runtime import unknown_domain_direct_candidate_v2 as c2
from canonical.runtime import unknown_domain_direct_candidate_v3 as c3
from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as g1
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as g2
from canonical.runtime import unknown_domain_direct_hidden_generator_v3 as g3
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_v4_universal_proof_v1 as proposed

ROOT=Path(__file__).resolve().parent

EXPECTED={
 "canonical/runtime/unknown_domain_direct_candidate_v1.py":"a2a77269a8175ce315b466035049da0f761b8734",
 "canonical/runtime/unknown_domain_direct_candidate_v2.py":"4470716f95a559a700e461262df909ae19a41651",
 "canonical/runtime/unknown_domain_direct_candidate_v3.py":"8df7f13455b710623806a8219174b397a2c3c442",
 "canonical/runtime/unknown_domain_direct_hidden_generator_v1.py":"f974a4594c78e74693c7ba5a19f131dfa481b937",
 "canonical/runtime/unknown_domain_direct_hidden_generator_v2.py":"d077028c9bde534dc4bc6eb0d1f776341f9d59f8",
 "canonical/runtime/unknown_domain_direct_hidden_generator_v3.py":"8b855851b8a0fec3a0811c5033cc4ea6d2436954",
 "canonical/runtime/unknown_domain_direct_hidden_scorer_v1.py":"e8cf5d1b5d311644725a751c15e6235958fb587d",
 "canonical/runtime/unknown_domain_direct_execution_harness_v1.py":"04fe06f4eed081c4cb6197b12f2d92bd396aeafd",
 "canonical/runtime/unknown_domain_direct_v4_universal_proof_v1.py":"72bbed393ac1bcaccb4cf33cd37835662c421f6c",
 "canonical/tests/test_unknown_domain_direct_v4_universal_proof_v1.py":"b39d166a6de231dcafa62458c6ad6d59a1e595ac",
 "canonical/governance/UNKNOWN_DOMAIN_DIRECT_V4_TOTAL_UNIVERSAL_PROOF_CANDIDATE_20261005_V1.json":"46d9571fc3c66f86f24a62870e3b65da662e1c5b",
}

FAMILIES=(
 "ORDER_PRESERVING_TRANSFORM",
 "PARITY_OR_SIGN_INVARIANT",
 "CONSERVATION_RELATION",
 "MONOTONE_CAUSAL_EDGE",
 "COMPOSITIONAL_REWRITE",
 "THRESHOLD_OR_PARTITION_INVARIANT",
)


def blob(path:Path)->str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()


def bind_exact_bytes()->None:
    bad={}
    for rel,want in EXPECTED.items():
        got=blob(ROOT/rel)
        if got!=want:
            bad[rel]={"want":want,"got":got}
    assert not bad,bad

    gov=json.loads((ROOT/"canonical/governance/UNKNOWN_DOMAIN_DIRECT_V4_TOTAL_UNIVERSAL_PROOF_CANDIDATE_20261005_V1.json").read_text())
    assert gov["target_predicate"]=="UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"
    assert gov["exact_subject_blobs"]["canonical/runtime/unknown_domain_direct_candidate_v3.py"]==EXPECTED["canonical/runtime/unknown_domain_direct_candidate_v3.py"]
    assert gov["exact_subject_blobs"]["canonical/runtime/unknown_domain_direct_hidden_generator_v3.py"]==EXPECTED["canonical/runtime/unknown_domain_direct_hidden_generator_v3.py"]
    assert gov["authority"]["acceptance_credit"] is False
    assert gov["authority"]["independent_verification_required"] is True


def independent_permutation_totality()->dict:
    # Independent pure Fisher-Yates model.  For n<=7, exhaust every legal swap
    # sequence. This covers every possible digest-derived modulo outcome on
    # every within-case semantic identifier group, including adversarially
    # repeated/colliding HMAC outputs.
    paths=0
    for n in range(1,8):
        labels=tuple(range(n))
        domains=[range(i+1) for i in range(n-1,0,-1)]
        seqs=itertools.product(*domains) if domains else [()]
        for swaps in seqs:
            arr=list(labels)
            for k,i in enumerate(range(n-1,0,-1)):
                j=swaps[k]
                arr[i],arr[j]=arr[j],arr[i]
            assert len(arr)==n
            assert set(arr)==set(labels)
            paths+=1
    assert paths==5913

    # The same invariant extends to case-tag permutations of size 12 and 15:
    # each loop step swaps two members of an already-unique list, so cardinality
    # and element set are invariant by induction. Verify the bound implementation
    # has exactly that operation and no hash-derived identifier concatenation
    # is used as a uniqueness source.
    src=inspect.getsource(g3._perm)
    compact="".join(src.split())
    assert "out=list(range(n))" in compact
    assert "j=_draw(secret,beacon,label,i)%(i+1)" in compact
    assert "out[i],out[j]=out[j],out[i]" in compact
    assert "set(result)!=set(range(n))" in compact

    # Force the worst distributional case: every HMAC-derived draw behaves as
    # the same integer. Generation must remain total and injective.
    old=g3._draw
    try:
        g3._draw=lambda *args,**kwargs: 0
        packet=g3._generate(
            beacon="VERIFY-V4-TOTALITY-0000000001",
            evaluator_secret=b"V"*32,
            namespace="VERIFYV4",
        )
    finally:
        g3._draw=old
    assert packet["case_count"]==27

    case_ids=[x["case_id"] for x in packet["visible_cases"]]
    assert len(case_ids)==len(set(case_ids))==27
    for visible,hidden in zip(packet["visible_cases"],packet["hidden_records"]):
        assert visible["case_id"]==hidden["case_id"]
        if hidden["leaf_id"]==g1.TRANSFER:
            relevant=list(hidden["transfer_relevant_feature_ids"])
            distractors=list(hidden["distractor_feature_ids"])
            assert len(relevant)==len(set(relevant))
            assert len(distractors)==len(set(distractors))
            assert not (set(relevant)&set(distractors))
            a_ids=set()
            for row in visible["domain_a"]["tasks"]:
                a_ids.update(row["inputs"])
            b_ids=set()
            for row in visible["domain_b"]["tasks"]:
                b_ids.update(row["inputs"])
            assert not (a_ids&b_ids)
            pids=[p["probe_id"] for p in visible["domain_b"]["allowed_probes"]]
            assert len(pids)==len(set(pids))==2
        else:
            hyps=visible["hypotheses"]
            hids=[h["hypothesis_id"] for h in hyps]
            assert len(hids)==len(set(hids))==2
            status=hidden["identifiability_status"]
            vals=[h["terminal_consequence"] for h in hyps]
            if status=="IDENTIFIABLE":
                assert len(set(vals))==1
            else:
                assert len(set(vals))==2
            pids=[p["probe_id"] for p in visible["allowed_probes"]]
            assert len(pids)==len(set(pids))

    return {
      "exhaustive_small_group_swap_paths":paths,
      "large_case_tag_sizes_proved_by_swap_invariant":[12,15],
      "constant_draw_adversary_population_pass":True,
      "hash_collision_resistance_required":False,
      "accepted_input_rejection_for_collision_required":False,
    }


def exact_float_order_and_counterexample()->dict:
    # Content-bound source audit: both gold and candidate evaluator execute ADD2
    # in explicit bias,r0,r1 left-to-right Python order. Candidate V3's only job
    # is to recover the true r0/r1 orientation before c2._conclude calls c1.
    csrc="".join(inspect.getsource(c1._program_eval).split())
    gsrc="".join(inspect.getsource(g1._eval).split())
    assert 'ifop=="ADD2":return_finite(params["bias"],"bias")+_finite(role_values["r0"],"r0")+_finite(role_values["r1"],"r1")' in csrc
    assert 'ifop=="ADD2":returnfloat(p["bias"])+float(role_values["r0"])+float(role_values["r1"])' in gsrc

    v3src=inspect.getsource(c3)
    tree=ast.parse(v3src)
    imports=set()
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):
            imports.update(a.name for a in node.names)
        elif isinstance(node,ast.ImportFrom) and node.module:
            imports.add(node.module)
    assert imports <= {
      "__future__","typing",
      "canonical.runtime.unknown_domain_direct_candidate_v1",
      "canonical.runtime.unknown_domain_direct_candidate_v2",
    },imports
    assert c3.ADD2_R0_SIG==(-1,1,-1)
    assert c3.ADD2_R1_SIG==(1,-1,1)

    # Reproduce a generator-reachable exact-float counterexample on the totalized
    # generator. V2 must fail only the terminal exactness; V3 must pass the same
    # case with the exact gold float and the same one-probe budget.
    secret=hashlib.sha256(b"secret-full-6").digest()
    beacon="CEFULL-00000006-20261005-LONG"
    visible,hidden=g3._transfer_case(secret,beacon,4,namespace="VERIFYV4CE")
    bad=harness.execute_case(candidate_step=c2.step,case_visible=visible,hidden_record=hidden)
    good=harness.execute_case(candidate_step=c3.step,case_visible=visible,hidden_record=hidden)
    assert bad["scorer_result"]["pass"] is False,bad
    assert "DOMAIN_B_TERMINAL_CONSEQUENCE_WRONG" in bad["scorer_result"]["errors"]
    assert set(bad["candidate_terminal_action"]["support_feature_ids"])==set(hidden["transfer_relevant_feature_ids"])
    delta=abs(bad["candidate_terminal_action"]["terminal_consequence"]-hidden["gold_terminal_consequence"])
    assert 0<delta<1e-12
    assert good["scorer_result"]["pass"] is True,good
    assert good["candidate_terminal_action"]["terminal_consequence"]==hidden["gold_terminal_consequence"]
    assert good["probe_count"]==1

    return {
      "v2_counterexample_delta":delta,
      "v2_correct_support_but_exact_float_fail":True,
      "v3_same_case_pass":True,
      "v3_exact_gold_equality":True,
      "candidate_hidden_imports":False,
    }


def independent_transfer_and_abstention_derivation()->dict:
    assert tuple(g1.PRIMITIVE_FAMILIES)==FAMILIES
    assert g1.PRODUCTION_CASE_COUNTS=={g1.TRANSFER:12,g1.ABSTAIN:15}
    assert harness.MAX_TRANSFER_PROBES==2
    assert c1.MAPPING_BASIS=="STRUCTURAL_EQUIVALENCE"

    d0=Fraction(19,4)
    d1=Fraction(25,4)
    lo=Fraction(1,4)
    hi=Fraction(7,2)
    affine=Fraction(3,5)*d0
    complement=d0
    sat=Fraction(7,10)*d0/Fraction(121,1)
    sign=-hi+d0
    step=d0-Fraction(11,5)
    add2=min(
      d0-(hi-lo),
      d1,
      d0,
      d1-(hi-lo),
      d0+d1,
    )
    assert affine==Fraction(57,20)
    assert complement==Fraction(19,4)
    assert float(sat)>4.5e-9
    assert sign==Fraction(5,4)>0
    assert step==Fraction(51,20)>0
    assert add2==Fraction(3,2)

    for index in (4,10):
        r0=tuple(-1 if (j+index)%2==0 else 1 for j in range(3))
        r1=tuple(-1 if (j+index+1)%3==0 else 1 for j in range(3))
        assert r0==c3.ADD2_R0_SIG
        assert r1==c3.ADD2_R1_SIG
        assert r0!=r1

    assert tuple(g1.ABSTAIN_CLASSES)==("IDENTIFIABLE","NONIDENTIFIABLE","UNDERSPECIFIED")
    assert scorer.DECISIONS=={"CONCLUDE","ABSTAIN","REQUEST_DISCRIMINATOR"}

    return {
      "six_transfer_families":True,
      "affine_min_gap":str(affine),
      "complement_min_gap":str(complement),
      "sat_mono_min_gap":str(sat),
      "sign_shifted_min":str(sign),
      "step_margin":str(step),
      "add2_min_wrong_support_gap":str(add2),
      "add2_visible_orientation_unique":True,
      "three_abstention_classes":True,
    }


def verifier_only_regression(populations:int=64)->dict:
    total=0
    fam={f:0 for f in FAMILIES}
    cls={x:0 for x in g1.ABSTAIN_CLASSES}
    max_probe=0
    for i in range(populations):
        seed=f"V4-INDEPENDENT-VERIFY-{i}".encode()
        secret=hashlib.sha256(seed).digest()
        beacon="VERIFY-V4-"+hashlib.sha256(b"beacon|"+seed).hexdigest()
        packet=g3._generate(
          beacon=beacon,
          evaluator_secret=secret,
          namespace=f"V4IV{i:04d}",
        )
        assert packet["case_count"]==27
        results=[]
        for visible,hidden in zip(packet["visible_cases"],packet["hidden_records"]):
            out=harness.execute_case(
              candidate_step=c3.step,
              case_visible=visible,
              hidden_record=hidden,
            )
            assert out["scorer_result"]["pass"] is True,(i,visible["case_id"],out["scorer_result"])
            results.append(out["scorer_result"])
            max_probe=max(max_probe,int(out["probe_count"]))
            total+=1
            if hidden["leaf_id"]==g1.TRANSFER:
                fam[hidden["primitive_family"]]+=1
            else:
                cls[hidden["identifiability_status"]]+=1
        assert scorer.aggregate(results)["all_27_cases_pass"] is True
    assert total==populations*27
    assert max_probe<=2
    assert all(v>0 for v in fam.values())
    assert cls=={x:populations*5 for x in g1.ABSTAIN_CLASSES}
    return {
      "verifier_only_populations":populations,
      "hidden_scored_cases":total,
      "max_probe":max_probe,
      "family_counts":fam,
      "abstention_counts":cls,
      "production_authority_function_called":False,
      "production_cases_consumed":0,
    }


def main()->None:
    bind_exact_bytes()
    identifier=independent_permutation_totality()
    exact=exact_float_order_and_counterexample()
    semantic=independent_transfer_and_abstention_derivation()
    regression=verifier_only_regression(64)

    candidate=proposed.prove()
    assert candidate["status"]=="PASS__UNIVERSAL_OVER_ALL_VALID_TOTALIZED_V3_INPUTS_WITH_EXACT_FLOAT_V3_CANDIDATE"
    assert candidate["scope"]["terminal_or_production_cases_generated"]==0
    assert candidate["accounting"]["acceptance_credit_delta"]==0

    receipt={
      "schema":"PROJECT_BRAIN_UNKNOWN_DOMAIN_V4_TOTAL_EXACT_INDEPENDENT_VERIFICATION_V1",
      "status":"INDEPENDENT_CONTENT_BOUND_PASS",
      "target_predicate":"UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",
      "source_brain_pr":1934,
      "exact_brain_blobs":EXPECTED,
      "identifier_totality":identifier,
      "exact_float":exact,
      "semantic_derivation":semantic,
      "falsification":regression,
      "deduction":"EXACT_BOUND_V4_CONJUNCTION_CLOSES_BOTH_KNOWN_V2_UNIVERSAL_HOLES_WITHOUT_WEAKENING_THE_INPUT_QUANTIFIER__FRESH_27_CASE_PRODUCTION_HAS_ZERO_INFORMATION_GAIN_FOR_THIS_EXACT_EVALUATOR_CONTRACT",
      "hard_nonclaims":[
        "NO_OPEN_WORLD_UNKNOWN_DOMAIN_GENERALIZATION",
        "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT_FROM_THIS_VERIFIER_ALONE",
        "NO_PRODUCTION_OR_TERMINAL_CASE_GENERATED_READ_OR_CONSUMED",
        "SEPARATE_ROOT3_SCOPE_AND_ACCEPTANCE_REDUCTION_REQUIRED",
      ],
      "accounting":{
        "incremental_spend_usd":0,
        "new_reality_units_consumed":0,
        "terminal_cases_consumed":0,
        "production_cases_generated":0,
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
      },
    }
    print(json.dumps(receipt,sort_keys=True))


if __name__=="__main__":
    main()
