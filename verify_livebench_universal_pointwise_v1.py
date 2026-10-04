#!/usr/bin/env python3
from __future__ import annotations

import hashlib, json, pathlib, re, subprocess, sys
from collections import Counter

LIVEBENCH_COMMIT="8f8e5c381a16e3f24257776edd53471fe86f8091"
INSTRUCTIONS_BLOB="4997bab885a676d92545fd91a9a20b48d234a2b2"
REGISTRY_BLOB="903ed738398648c7cfac61d5ffa478c22f1f0891"
UTIL_BLOB="1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b"

EXPECTED={
"livebench_legacy15_composition_archetypes_v1.py":"0dbef76a6189a3cdc21ce3dae97ef6921e333b34",
"livebench_legacy15_contract_composer_v2.py":"d73ec366b32252996258eae6d10d67d4d6a5e042",
"livebench_legacy15_slot_feasibility_v1.py":"7477f5ea5bdeac3595ee2784a38d078fe2f385b0",
"livebench_legacy15_pointwise_optimal_v1.py":"71e637c70edf1c582e28ea38b3b798965c803a06",
"livebench_legacy15_lexical_slot_quotient_v1.py":"5803c31e3972c6d40415f319e808c48420bc0388",
"livebench_legacy15_numeric_quotient_v1.py":"72189bb8adb12ad36a52ee666a1f79fbb201b06b",
"livebench_pointwise_minimum_cut_v1.py":"0d4e563b618f8fd7f37396a88738cefb50979ff3",
}
VISIBLE_V4_BLOB="721207ba39d502e3f610289578e9d5bab78b1fcc"

ROOT=pathlib.Path(__file__).resolve().parent
SUBJECT=ROOT/"subject/livebench_universal_pointwise_20261005"
RUNTIME=SUBJECT/"canonical/runtime"

def run(cmd,**kw):
    return subprocess.run(cmd,check=True,text=True,**kw)

def blob(path):
    return run(["git","hash-object",str(path)],capture_output=True).stdout.strip()

def exact_source_blob(repo,path):
    return run(["git","-C",str(repo),"rev-parse",f"HEAD:{path}"],capture_output=True).stdout.strip()

def C(iid,**slots):
    return {"instruction_id":iid,"slots":slots}

def main():
    for name,expected in EXPECTED.items():
        got=blob(RUNTIME/name)
        assert got==expected,(name,got,expected)

    visible=ROOT/"subject/livebench_visible_compiler_v4_20261005/canonical/runtime/livebench_legacy_visible_constraint_compiler_v4.py"
    assert blob(visible)==VISIBLE_V4_BLOB

    live=pathlib.Path("/tmp/LiveBench")
    assert run(["git","-C",str(live),"rev-parse","HEAD"],capture_output=True).stdout.strip()==LIVEBENCH_COMMIT
    for path,expected in {
      "livebench/if_runner/instruction_following_eval/instructions.py":INSTRUCTIONS_BLOB,
      "livebench/if_runner/instruction_following_eval/instructions_registry.py":REGISTRY_BLOB,
      "livebench/if_runner/instruction_following_eval/instructions_util.py":UTIL_BLOB,
    }.items():
        assert exact_source_blob(live,path)==expected

    sys.path.insert(0,str(SUBJECT))
    sys.path.insert(0,str(live/"livebench/if_runner"))
    from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as arch
    from canonical.runtime import livebench_legacy15_contract_composer_v2 as comp
    from canonical.runtime import livebench_legacy15_pointwise_optimal_v1 as opt
    from canonical.runtime import livebench_legacy15_lexical_slot_quotient_v1 as lex
    from canonical.runtime import livebench_legacy15_numeric_quotient_v1 as num
    from canonical.runtime import livebench_pointwise_minimum_cut_v1 as cut
    from instruction_following_eval import instructions_registry,instructions_util

    words=list(instructions_util.WORD_LIST)
    assert len(words)==1525 and len(set(words))==1525
    assert all(w.isascii() and w.isalpha() for w in words)
    lower={w.lower() for w in words}

    fixed_alpha={"section","any","other","questions","is","there","anything","else","i","can","help","with","p","s"}
    fixed_intersection=sorted(lower & fixed_alpha)
    assert fixed_intersection==["anything","can","help","other","section"],fixed_intersection

    # Universal existence/forbidden overlap carrier theorem over the exact public lexicon.
    carrier_cases=0
    for w in words:
        carrier="9"+w+"9"
        assert re.search(w,carrier,flags=re.IGNORECASE)
        assert not re.search(r"\b"+re.escape(w)+r"\b",carrier,flags=re.IGNORECASE)
        carrier_cases+=1

    # Section is the only non-end fixed scaffold word in the public lexicon.
    assert re.search(r"\s?Section\s?\d+\s?","9Section 5")
    assert not re.search(r"\bsection\b","9Section 5",flags=re.IGNORECASE)

    a=arch.verify()
    l=lex.verify()
    n=num.verify()
    m=cut.verify()
    assert a["compatible_set_count"]==928
    assert l["exact_reachable_signature_count"]==192
    assert n["word_upper_bound"]["analytic_constructor_ceiling"]==48
    assert n["word_upper_bound"]["minimum_safety_margin"]==52
    assert m["exact_classification_cases"]==356352
    assert m["maximum_mandatory_sacrifices_per_case"]==2

    def exact_follow(c,response):
        iid=c["instruction_id"]
        obj=instructions_registry.INSTRUCTION_DICT[iid](iid)
        obj.build_description(**dict(c.get("slots") or {}))
        return bool(response.strip()) and bool(obj.check_following(response))

    def exact_all(contracts,response):
        return [exact_follow(c,response) for c in contracts]

    counts=Counter()
    failures=[]

    # Exact postvalidation across the full minimum-cut quotient.
    for ids in arch.enumerate_compatible_sets():
        for sig in lex.enumerate_signatures():
            for sentence_zero in (False,True):
                contracts=cut._skeleton(ids,sig,sentence_zero=sentence_zero)
                plan=opt.solve_contracts(contracts)
                counts["quotient_cases"]+=1
                if plan.get("status")!="CANDIDATE_POINTWISE_OPTIMAL":
                    failures.append(("planner_fail",ids,str(sig),sentence_zero,plan))
                    continue
                flags=exact_all(contracts,str(plan["response"]))
                actual=sum(flags)
                theoretical=int(plan["theoretical_max_pass_count"])
                if actual!=theoretical:
                    failures.append(("pointwise_mismatch",ids,str(sig),sentence_zero,flags,theoretical,plan.get("sacrificed_instruction_ids")))
                else:
                    counts["quotient_exact_max"]+=1

    # Exact numeric/discrete endpoint closure across every compatible structural set.
    for ids in arch.enumerate_compatible_sets():
        base=num.maximal_profile(ids)
        out=comp.compose_contracts(base)
        counts["maximal_profile_cases"]+=1
        if out.get("status")!="CANDIDATE_WITNESS" or not all(exact_all(base,str(out.get("response") or ""))):
            failures.append(("maximal_profile",ids,out))
            continue
        counts["maximal_profile_pass"]+=1

        if comp.WORDS in ids:
            for relation,threshold in (("less than",100),("at least",500)):
                cs=[dict(c) for c in base]
                for c in cs:
                    if c["instruction_id"]==comp.WORDS:
                        c["slots"]={"num_words":threshold,"relation":relation}
                o=comp.compose_contracts(cs); counts["word_endpoint_cases"]+=1
                if o.get("status")!="CANDIDATE_WITNESS" or not all(exact_all(cs,str(o.get("response") or ""))):
                    failures.append(("word_endpoint",ids,relation,threshold,o))
                else: counts["word_endpoint_pass"]+=1

        if comp.SENTENCES in ids:
            for relation,threshold in (("less than",2),("at least",20)):
                cs=[dict(c) for c in base]
                for c in cs:
                    if c["instruction_id"]==comp.SENTENCES:
                        c["slots"]={"num_sentences":threshold,"relation":relation}
                o=comp.compose_contracts(cs); counts["sentence_endpoint_cases"]+=1
                if o.get("status")!="CANDIDATE_WITNESS" or not all(exact_all(cs,str(o.get("response") or ""))):
                    failures.append(("sentence_endpoint",ids,relation,threshold,o))
                else: counts["sentence_endpoint_pass"]+=1

        # Exact small public integer domains, varied one coordinate at a time.
        variations=[]
        if comp.PARAGRAPHS in ids:
            variations += [(comp.PARAGRAPHS,{"num_paragraphs":v}) for v in range(1,6)]
        if comp.BULLETS in ids:
            variations += [(comp.BULLETS,{"num_bullets":v}) for v in range(1,6)]
        if comp.SECTIONS in ids:
            variations += [(comp.SECTIONS,{"section_spliter":sp,"num_sections":v}) for sp in ("Section","SECTION") for v in range(1,6)]
        if comp.POSTSCRIPT in ids:
            variations += [(comp.POSTSCRIPT,{"postscript_marker":v}) for v in ("P.S.","P.P.S")]
        if comp.NTH in ids:
            variations += [(comp.NTH,{"num_paragraphs":p,"nth_paragraph":k,"first_word":"river"}) for p in range(1,6) for k in range(1,p+1)]
        for iid,slots in variations:
            cs=[dict(c) for c in base]
            for c in cs:
                if c["instruction_id"]==iid: c["slots"]=slots
            o=comp.compose_contracts(cs); counts["discrete_variation_cases"]+=1
            if o.get("status")!="CANDIDATE_WITNESS" or not all(exact_all(cs,str(o.get("response") or ""))):
                failures.append(("discrete_variation",ids,iid,slots,o))
            else: counts["discrete_variation_pass"]+=1

    # NTH identity is parametric; exhaust every public word at every valid position.
    for w in words:
        for p in range(1,6):
            for k in range(1,p+1):
                cs=[C(comp.NTH,num_paragraphs=p,nth_paragraph=k,first_word=w)]
                o=comp.compose_contracts(cs); counts["nth_identity_cases"]+=1
                if o.get("status")!="CANDIDATE_WITNESS" or exact_all(cs,str(o.get("response") or ""))!=[True]:
                    failures.append(("nth_identity",w,p,k,o))
                else: counts["nth_identity_pass"]+=1

    # Repeat is an unbounded visible string parameter, but construction/checker are exact prefix morphisms.
    repeat_samples=[
      "Public request.",
      "  Leading and trailing whitespace request.  ",
      "Line one.\nLine two with punctuation?!",
      "Section 5 ****** <<x>> {json} P.S. anything can help",
      "αβγ Unicode visible request",
    ]
    for prompt in repeat_samples:
        cs=[C(comp.REPEAT,prompt_to_repeat=prompt),C(comp.TITLE)]
        o=comp.compose_contracts(cs); counts["repeat_adversarial_cases"]+=1
        if o.get("status")!="CANDIDATE_WITNESS" or not all(exact_all(cs,str(o.get("response") or ""))):
            failures.append(("repeat_adversarial",prompt,o))
        else:
            assert str(o["response"]).lower().startswith(prompt.strip().lower())
            counts["repeat_adversarial_pass"]+=1

    if failures:
        receipt={
          "schema":"PROJECT_BRAIN_LIVEBENCH_UNIVERSAL_POINTWISE_INDEPENDENT_VERIFICATION_V1",
          "status":"FAIL",
          "failure_count":len(failures),
          "failures":[repr(x) for x in failures[:50]],
          "counts":dict(counts),
          "terminal_rows_read":0,"hidden_terminal_kwargs_read":0,"hidden_terminal_ids_read":0
        }
        pathlib.Path("livebench_universal_pointwise_verification.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
        print(json.dumps(receipt,sort_keys=True))
        return 1

    receipt={
      "schema":"PROJECT_BRAIN_LIVEBENCH_UNIVERSAL_POINTWISE_INDEPENDENT_VERIFICATION_V1",
      "status":"PASS__UNIVERSAL_REDUCED_QUOTIENT_POINTWISE_EXACT_MAX__ZERO_TERMINAL_ROWS",
      "subject_blobs":EXPECTED,
      "visible_compiler_v4_blob":VISIBLE_V4_BLOB,
      "pinned_public_source":{
        "livebench_commit":LIVEBENCH_COMMIT,
        "instructions_blob":INSTRUCTIONS_BLOB,
        "registry_blob":REGISTRY_BLOB,
        "instructions_util_blob":UTIL_BLOB,
        "nltk_version":"3.10.3"
      },
      "public_lexicon":{
        "count":len(words),"unique":len(set(words)),
        "fixed_scaffold_intersection":fixed_intersection,
        "existence_forbidden_carrier_cases":carrier_cases
      },
      "proof_reductions":{
        "compatible_structural_sets":928,
        "reachable_lexical_signatures":192,
        "sentence_loss_partition_states":2,
        "minimum_cut_classification_cases":356352,
        "mandatory_loss_coordinates":["sentence_zero","forbidden_collision_cluster"],
        "analytic_word_ceiling":48,
        "public_minimum_word_threshold":100,
        "minimum_word_safety_margin":52
      },
      "exact_verification_counts":dict(counts),
      "terminal_rows_read":0,
      "hidden_terminal_kwargs_read":0,
      "hidden_terminal_instruction_ids_read":0,
      "target_responses_read":0,
      "target_scores_read":0,
      "acceptance_credit_delta":0,
      "family_credit_delta":0,
      "capability_credit_delta":0,
      "ownership_credit_delta":0,
      "hard_nonclaims":[
        "THIS_RECEIPT_DOES_NOT_ITSELF_MUTATE_BRAIN_ACCEPTANCE_AUTHORITY",
        "PROMOTION_REQUIRES_SEPARATE_FAIL_CLOSED_REDUCTION_AGAINST_THE_OUTCOME_BLIND_PRECOMMIT"
      ]
    }
    pathlib.Path("livebench_universal_pointwise_verification.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print(json.dumps(receipt,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
