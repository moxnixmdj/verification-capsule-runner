#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import itertools
import json
import pathlib
import re
import subprocess
import sys
from collections import Counter

ARCH_BLOB="0dbef76a6189a3cdc21ce3dae97ef6921e333b34"
FEAS_BLOB="7477f5ea5bdeac3595ee2784a38d078fe2f385b0"
COMPOSER_BLOB="d73ec366b32252996258eae6d10d67d4d6a5e042"
PLANNER_BLOB="71e637c70edf1c582e28ea38b3b798965c803a06"
LIVEBENCH_COMMIT="8f8e5c381a16e3f24257776edd53471fe86f8091"
INSTRUCTIONS_BLOB="4997bab885a676d92545fd91a9a20b48d234a2b2"
REGISTRY_BLOB="903ed738398648c7cfac61d5ffa478c22f1f0891"
UTIL_BLOB="1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b"

ROOT=pathlib.Path(__file__).resolve().parent
SUBJECT=ROOT/"subject/livebench_composer_v2_20261005"
ARCH=SUBJECT/"canonical/runtime/livebench_legacy15_composition_archetypes_v1.py"
FEAS=SUBJECT/"canonical/runtime/livebench_legacy15_slot_feasibility_v1.py"
COMPOSER=SUBJECT/"canonical/runtime/livebench_legacy15_contract_composer_v2.py"
PLANNER=SUBJECT/"canonical/runtime/livebench_legacy15_pointwise_optimal_v1.py"
RECEIPT=pathlib.Path("livebench_punkt_context_closure_v1.json")

def run(cmd,**kw):
    return subprocess.run(cmd,check=True,text=True,**kw)

def hash_object(path):
    return run(["git","hash-object",str(path)],capture_output=True).stdout.strip()

def C(iid,**slots):
    return {"instruction_id":iid,"slots":slots}

def main():
    assert hash_object(ARCH)==ARCH_BLOB
    assert hash_object(FEAS)==FEAS_BLOB
    assert hash_object(COMPOSER)==COMPOSER_BLOB
    assert hash_object(PLANNER)==PLANNER_BLOB

    live=pathlib.Path("/tmp/LiveBench")
    assert run(["git","-C",str(live),"rev-parse","HEAD"],capture_output=True).stdout.strip()==LIVEBENCH_COMMIT
    for rel,expected in {
        "livebench/if_runner/instruction_following_eval/instructions.py":INSTRUCTIONS_BLOB,
        "livebench/if_runner/instruction_following_eval/instructions_registry.py":REGISTRY_BLOB,
        "livebench/if_runner/instruction_following_eval/instructions_util.py":UTIL_BLOB,
    }.items():
        got=run(["git","-C",str(live),"rev-parse",f"HEAD:{rel}"],capture_output=True).stdout.strip()
        assert got==expected,(rel,got,expected)

    sys.path.insert(0,str(SUBJECT))
    sys.path.insert(0,str(live/"livebench/if_runner"))
    from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as arch
    from canonical.runtime import livebench_legacy15_contract_composer_v2 as comp
    from canonical.runtime import livebench_legacy15_pointwise_optimal_v1 as opt
    from instruction_following_eval import instructions_registry,instructions_util

    words=list(instructions_util.WORD_LIST)
    assert len(words)==1525 and len(set(words))==1525
    assert all(re.fullmatch(r"[A-Za-z]+",w) for w in words)
    lower={w.lower() for w in words}

    # Independently recheck the lexical premise needed by the parametric proof.
    end_phrases=("Any other questions?","Is there anything else I can help with?")
    end_intersection=sorted(lower & set(re.findall(r"[A-Za-z]+"," ".join(end_phrases).lower())))
    assert end_intersection==["anything","can","help","other"],end_intersection
    # Postscript syntax contributes P/S tokens, but neither is generator-admitted
    # as a forbidden word. Section is admitted but the composer left-shields it.
    assert "p" not in lower and "s" not in lower
    assert "section" in lower

    def fillers(exclude=(),n=5):
        ex={str(x).lower() for x in exclude}
        out=[]
        for w in words:
            if w.lower() not in ex:
                out.append(w); ex.add(w.lower())
            if len(out)==n: return out
        raise AssertionError("FILLER_EXHAUSTED")

    safe_first=fillers({"section","other","anything","can","help","p","s"},1)[0]
    required=fillers({"section","other","anything","can","help","p","s",safe_first},5)
    forbidden=fillers(set(required)|{"section","other","anything","can","help","p","s",safe_first},5)

    def exact_follow(c,response):
        iid=c["instruction_id"]
        checker=instructions_registry.INSTRUCTION_DICT[iid](iid)
        checker.build_description(**dict(c.get("slots") or {}))
        return bool(str(response).strip()) and bool(checker.check_following(str(response)))

    def exact_all(contracts,response):
        return [exact_follow(c,response) for c in contracts]

    # Base non-sentence values. Profile generation below varies every parameter
    # that can alter punctuation, paragraph placement, or the amount of
    # punctuation-free text surrounding a sentence terminator.
    def base_slots(iid):
        if iid==comp.EXIST: return {"keywords":list(required)}
        if iid==comp.FORBIDDEN: return {"forbidden_words":list(forbidden)}
        if iid==comp.WORDS: return {"num_words":100,"relation":"less than"}
        if iid==comp.SENTENCES: return {"num_sentences":2,"relation":"less than"}
        if iid==comp.NTH: return {"num_paragraphs":1,"nth_paragraph":1,"first_word":safe_first}
        if iid==comp.POSTSCRIPT: return {"postscript_marker":"P.P.S"}
        if iid==comp.BULLETS: return {"num_bullets":1}
        if iid==comp.TITLE: return {}
        if iid==comp.SECTIONS: return {"section_spliter":"Section","num_sections":1}
        if iid==comp.END: return {"end_phrase":end_phrases[0]}
        if iid==comp.QUOTE: return {}
        if iid==comp.PARAGRAPHS: return {"num_paragraphs":1}
        if iid==comp.JSON_ID: return {}
        if iid==comp.REPEAT: return {"prompt_to_repeat":"Public visible request without sentence punctuation"}
        if iid==comp.TWO: return {}
        raise AssertionError(iid)

    def contracts_for(ids, overrides, sentence_n, sentence_rel):
        out=[]
        for iid in ids:
            slots=base_slots(iid)
            slots.update(overrides.get(iid,{ }))
            if iid==comp.SENTENCES:
                slots={"num_sentences":sentence_n,"relation":sentence_rel}
            out.append(C(iid,**slots))
        return out

    def context_profiles(ids):
        ids=set(ids)
        dims=[]
        # Cross every punctuation-bearing tail and NTH paragraph placement.
        if comp.NTH in ids:
            nth=[{"num_paragraphs":p,"nth_paragraph":k,"first_word":safe_first}
                 for p in range(1,6) for k in range(1,p+1)]
        else:
            nth=[None]
        posts=[{"postscript_marker":x} for x in ("P.S.","P.P.S")] if comp.POSTSCRIPT in ids else [None]
        ends=[{"end_phrase":x} for x in end_phrases] if comp.END in ids else [None]
        # Word padding is punctuation-free. Test no-padding and the longest
        # admitted padding context to bind both sides of the parametric lemma.
        words_dim=[
            {"num_words":100,"relation":"less than"},
            {"num_words":100,"relation":"at least"},
            {"num_words":500,"relation":"at least"},
        ] if comp.WORDS in ids else [None]

        for n,p,e,w in itertools.product(nth,posts,ends,words_dim):
            ov={}
            if n is not None: ov[comp.NTH]=n
            if p is not None: ov[comp.POSTSCRIPT]=p
            if e is not None: ov[comp.END]=e
            if w is not None: ov[comp.WORDS]=w
            dims.append(ov)

        # Exact small domains that can add punctuation-free lines/newlines.
        if comp.BULLETS in ids:
            for b in range(1,6):
                dims.append({comp.BULLETS:{"num_bullets":b}})
        if comp.SECTIONS in ids:
            for splitter in ("Section","SECTION"):
                for s in range(1,6):
                    dims.append({comp.SECTIONS:{"section_spliter":splitter,"num_sections":s}})

        # Deduplicate profiles canonically.
        seen=set(); out=[]
        for ov in dims or [{}]:
            key=json.dumps(ov,sort_keys=True)
            if key not in seen:
                seen.add(key); out.append(ov)
        return out

    counts=Counter()
    failures=[]
    sentence_sets=[ids for ids in arch.enumerate_compatible_sets() if comp.SENTENCES in ids]
    assert len(sentence_sets)==227,len(sentence_sets)

    for set_index,ids in enumerate(sentence_sets):
        profiles=context_profiles(ids)
        counts["context_profiles"]+=len(profiles)
        for profile_index,ov in enumerate(profiles):
            for relation in ("less than","at least"):
                for n in range(1,21):
                    contracts=contracts_for(ids,ov,n,relation)
                    plan=opt.solve_contracts(contracts)
                    counts["cases"]+=1
                    if plan.get("status")!="CANDIDATE_POINTWISE_OPTIMAL":
                        failures.append({"set":set_index,"profile":profile_index,"n":n,"relation":relation,"kind":"planner_fail","plan":plan})
                        if len(failures)>=50: break
                        continue
                    response=str(plan["response"])
                    flags=exact_all(contracts,response)
                    exact_pass=sum(flags)
                    theoretical=int(plan["theoretical_max_pass_count"])
                    if exact_pass!=theoretical:
                        failures.append({
                            "set":set_index,"ids":list(ids),"profile":profile_index,"override":ov,
                            "n":n,"relation":relation,"kind":"exact_max_mismatch",
                            "flags":flags,"exact_pass":exact_pass,"theoretical":theoretical,
                            "sacrificed":plan.get("sacrificed_instruction_ids"),"response":response,
                        })
                    sent_index=list(ids).index(comp.SENTENCES)
                    sentence_pass=bool(flags[sent_index])
                    if relation=="less than" and n==1:
                        if sentence_pass or comp.SENTENCES not in set(plan.get("sacrificed_instruction_ids") or []):
                            failures.append({"set":set_index,"profile":profile_index,"n":n,"relation":relation,"kind":"lt1_not_exactly_sacrificed","flags":flags,"plan":plan})
                        else:
                            counts["lt1_exact_unsat"]+=1
                    else:
                        if not sentence_pass:
                            failures.append({"set":set_index,"profile":profile_index,"n":n,"relation":relation,"kind":"sentence_context_fail","flags":flags,"response":response,"override":ov})
                        else:
                            counts["sentence_context_pass"]+=1
                    if relation=="at least" and n==20:
                        counts["atleast20_contexts"]+=1
                    if relation=="less than" and n==2:
                        counts["lt2_contexts"]+=1
                    if len(failures)>=50: break
                if len(failures)>=50: break
            if len(failures)>=50: break
        if len(failures)>=50: break

    receipt={
        "schema":"PROJECT_BRAIN_LIVEBENCH_PUNKT_CONTEXT_CLOSURE_INDEPENDENT_VERIFICATION_V1",
        "status":"FAIL" if failures else "PASS__ALL_SENTENCE_COMPATIBLE_STRUCTURAL_SETS__PINNED_PUNKT_CONTEXTS_EXACT_POINTWISE_MATCH",
        "subject_blobs":{"archetypes":ARCH_BLOB,"slot_feasibility":FEAS_BLOB,"composer":COMPOSER_BLOB,"pointwise_planner":PLANNER_BLOB},
        "pinned_livebench":{"commit":LIVEBENCH_COMMIT,"instructions_blob":INSTRUCTIONS_BLOB,"registry_blob":REGISTRY_BLOB,"instructions_util_blob":UTIL_BLOB,"nltk_version":"3.10.3"},
        "coverage":{"sentence_compatible_structural_sets":len(sentence_sets),**dict(counts)},
        "lexical_crosscheck":{"word_count":len(words),"end_phrase_word_list_intersection":end_intersection,"postscript_single_letter_tokens_absent_from_word_list":True,"section_word_is_generator_admitted_and_existing_composer_shield_is_exercised_elsewhere":True},
        "meaning":[
            "EVERY_CONFLICT_COMPATIBLE_ACTIVE15_ID_SET_CONTAINING_NUMBER_SENTENCES_WAS_EXERCISED",
            "ALL_40_PUBLIC_SENTENCE_THRESHOLD_RELATION_STATES_WERE_EXERCISED_PER_CONTEXT",
            "ALL_NTH_PARAGRAPH_POSITIONS_AND_BOTH_POSTSCRIPT_AND_END_PHRASE_TAILS_WERE_CROSSED_WHEN_PRESENT",
            "NO_PADDING_AND_MAXIMUM_500_WORD_PADDING_CONTEXTS_WERE_EXERCISED",
            "STRICT_LESS_THAN_ONE_IS_CONFIRMED_INTRINSICALLY_UNPASSABLE_UNDER_STRICT_NONEMPTY_EVALUATION",
        ],
        "failures":failures,
        "terminal_rows_read":0,"terminal_kwargs_read":0,"terminal_instruction_id_lists_read":0,"target_scores_read":0,
        "acceptance_credit_delta":0,"family_credit_delta":0,"capability_credit_delta":0,"ownership_credit_delta":0,
        "hard_nonclaims":[
            "THIS_RECEIPT_ONLY_CLOSES_THE_PINNED_PUNKT_ENVIRONMENT_SENSITIVE_REMAINDER",
            "LIVEBENCH_ACCEPTANCE_REQUIRES_SEPARATE_COMPOSITION_WITH_THE_EXISTING_NON_SENTENCE_PARAMETRIC_REDUCTION_POINTWISE_ENVELOPE_AND_SCOPE_BINDINGS",
        ],
    }
    RECEIPT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(receipt,sort_keys=True))
    if failures:
        raise SystemExit("PUNKT_CONTEXT_FAILURES:"+str(len(failures)))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
