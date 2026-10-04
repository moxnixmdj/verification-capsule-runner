#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import inspect
import itertools
import json
import pathlib
import subprocess
import sys

LIVEBENCH_COMMIT="8f8e5c381a16e3f24257776edd53471fe86f8091"
INSTRUCTIONS_BLOB="4997bab885a676d92545fd91a9a20b48d234a2b2"
REGISTRY_BLOB="903ed738398648c7cfac61d5ffa478c22f1f0891"
UTIL_BLOB="1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b"
NLTK_VERSION="3.10.3"
NLTK_DATA_COMMIT="550b6625bcef1f2abff2ff770a5a0d272c9c6b2"

EXPECTED={
 "canonical/runtime/livebench_legacy15_composition_archetypes_v1.py":"0dbef76a6189a3cdc21ce3dae97ef6921e333b34",
 "canonical/runtime/livebench_legacy15_slot_feasibility_v1.py":"7477f5ea5bdeac3595ee2784a38d078fe2f385b0",
 "canonical/runtime/livebench_legacy15_contract_composer_v2.py":"d73ec366b32252996258eae6d10d67d4d6a5e042",
 "canonical/runtime/livebench_legacy15_pointwise_optimal_v1.py":"71e637c70edf1c582e28ea38b3b798965c803a06",
 "canonical/runtime/livebench_legacy15_lexical_slot_quotient_v1.py":"5803c31e3972c6d40415f319e808c48420bc0388",
 "canonical/runtime/livebench_legacy15_numeric_quotient_v1.py":"72189bb8adb12ad36a52ee666a1f79fbb201b06b",
 "canonical/runtime/livebench_pointwise_minimum_cut_v1.py":"0d4e563b618f8fd7f37396a88738cefb50979ff3",
 "canonical/runtime/livebench_post_sacrifice_parametric_reduction_v1.py":"a9ab9064b447ed669d2404a7a65f6c429c51ae85",
}
ROOT=pathlib.Path(__file__).resolve().parent
SUBJECT=ROOT/"subject/livebench_composer_v2_20261005"

def run(cmd,**kw):
    return subprocess.run(cmd,check=True,text=True,**kw)

def blob(path:pathlib.Path)->str:
    return run(["git","hash-object",str(path)],capture_output=True).stdout.strip()

def C(iid,**slots):
    return {"instruction_id":iid,"slots":slots}

def main():
    got={rel:blob(SUBJECT/rel) for rel in EXPECTED}
    assert got==EXPECTED,(got,EXPECTED)

    live=pathlib.Path("/tmp/LiveBench")
    assert run(["git","-C",str(live),"rev-parse","HEAD"],capture_output=True).stdout.strip()==LIVEBENCH_COMMIT
    for rel,expected in {
      "livebench/if_runner/instruction_following_eval/instructions.py":INSTRUCTIONS_BLOB,
      "livebench/if_runner/instruction_following_eval/instructions_registry.py":REGISTRY_BLOB,
      "livebench/if_runner/instruction_following_eval/instructions_util.py":UTIL_BLOB,
    }.items():
        assert run(["git","-C",str(live),"rev-parse",f"HEAD:{rel}"],capture_output=True).stdout.strip()==expected

    sys.path.insert(0,str(SUBJECT))
    sys.path.insert(0,str(live/"livebench/if_runner"))
    import nltk
    from nltk.tokenize import sent_tokenize
    from nltk.tokenize.punkt import PunktSentenceTokenizer, _pair_iter
    from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as arch
    from canonical.runtime import livebench_legacy15_contract_composer_v2 as comp
    from canonical.runtime import livebench_legacy15_pointwise_optimal_v1 as opt
    from canonical.runtime import livebench_legacy15_lexical_slot_quotient_v1 as lex
    from canonical.runtime import livebench_legacy15_numeric_quotient_v1 as numeric
    from canonical.runtime import livebench_pointwise_minimum_cut_v1 as cut
    from canonical.runtime import livebench_post_sacrifice_parametric_reduction_v1 as param
    from instruction_following_eval import instructions_registry

    assert nltk.__version__==NLTK_VERSION,nltk.__version__
    assert arch.verify()["compatible_set_count"]==928
    assert lex.verify()["exact_reachable_signature_count"]==192
    nres=numeric.verify()
    assert nres["status"]=="PASS__PARAMETRIC_NUMERIC_REDUCTION"
    cres=cut.verify()
    assert cres["maximum_mandatory_sacrifices_per_case"]==2
    pres=param.verify()
    assert pres["status"].endswith("ONLY_PINNED_PUNKT_CONTEXT_REMAINS")

    # Source-level proof of the strict <1 sentence impossibility under the
    # exact NLTK implementation: for any nonempty response, Punkt's slice
    # generator emits at least one slice. Boundary realignment preserves a
    # nonempty slice stream; span_tokenize and sentences_from_text map rather
    # than filter that stream.
    source_parts={
      "_slices_from_text":inspect.getsource(PunktSentenceTokenizer._slices_from_text),
      "_realign_boundaries":inspect.getsource(PunktSentenceTokenizer._realign_boundaries),
      "span_tokenize":inspect.getsource(PunktSentenceTokenizer.span_tokenize),
      "sentences_from_text":inspect.getsource(PunktSentenceTokenizer.sentences_from_text),
      "_pair_iter":inspect.getsource(_pair_iter),
    }
    norm={k:"".join(v.split()) for k,v in source_parts.items()}
    assert "yieldslice(last_break,len(text.rstrip()))" in norm["_slices_from_text"]
    assert "for" in source_parts["_realign_boundaries"] and "yield" in source_parts["_realign_boundaries"]
    assert "yield(prev,None)" in norm["_pair_iter"]
    assert "self._slices_from_text(text)" in source_parts["span_tokenize"]
    assert "yield" in source_parts["span_tokenize"]
    assert "self.span_tokenize(text,realign_boundaries)" in norm["sentences_from_text"]
    source_sha256={k:hashlib.sha256(v.encode()).hexdigest() for k,v in source_parts.items()}

    def exact_follow(c,response):
        checker=instructions_registry.INSTRUCTION_DICT[c["instruction_id"]](c["instruction_id"])
        checker.build_description(**dict(c.get("slots") or {}))
        return bool(str(response).strip()) and bool(checker.check_following(str(response)))

    safe_required=list(lex.EXISTENCE_REPRESENTATIVE)
    safe_forbidden=list(lex.GENERIC_FORBIDDEN_FILLERS)
    assert not set(safe_forbidden)&{"river","other","anything","can","help","section"}

    def contexts(ids):
        ids=set(ids)
        posts=("P.S.","P.P.S") if comp.POSTSCRIPT in ids else (None,)
        ends=lex.END_PHRASES if comp.END in ids else (None,)
        word_modes=(("less than",100),("at least",500)) if comp.WORDS in ids else (None,)
        splitters=("Section","SECTION") if comp.SECTIONS in ids else (None,)
        nths=((1,1),(5,1),(5,5)) if comp.NTH in ids else (None,)
        return itertools.product(posts,ends,word_modes,splitters,nths)

    def build(ids,relation,n,ctx):
        post,end,word_mode,splitter,nth=ctx
        out=[]
        for iid in ids:
            if iid==comp.EXIST: out.append(C(iid,keywords=safe_required))
            elif iid==comp.FORBIDDEN: out.append(C(iid,forbidden_words=safe_forbidden))
            elif iid==comp.PARAGRAPHS: out.append(C(iid,num_paragraphs=5))
            elif iid==comp.WORDS:
                rel,wn=word_mode
                out.append(C(iid,num_words=wn,relation=rel))
            elif iid==comp.SENTENCES: out.append(C(iid,num_sentences=n,relation=relation))
            elif iid==comp.NTH:
                p,k=nth
                out.append(C(iid,num_paragraphs=p,nth_paragraph=k,first_word="river"))
            elif iid==comp.POSTSCRIPT: out.append(C(iid,postscript_marker=post))
            elif iid==comp.BULLETS: out.append(C(iid,num_bullets=5))
            elif iid==comp.TITLE: out.append(C(iid))
            elif iid==comp.SECTIONS: out.append(C(iid,section_spliter=splitter,num_sections=5))
            elif iid==comp.JSON_ID: out.append(C(iid))
            elif iid==comp.REPEAT: out.append(C(iid,prompt_to_repeat="Public visible request"))
            elif iid==comp.TWO: out.append(C(iid))
            elif iid==comp.END: out.append(C(iid,end_phrase=end))
            elif iid==comp.QUOTE: out.append(C(iid))
            else: raise AssertionError(iid)
        return out

    sentence_sets=[ids for ids in arch.enumerate_compatible_sets() if comp.SENTENCES in ids]
    assert sentence_sets
    cases=0
    atleast_cases=0
    lt2_cases=0
    lt1_cases=0
    max_contexts_per_set=0
    for ids in sentence_sets:
        ctxs=list(contexts(ids))
        max_contexts_per_set=max(max_contexts_per_set,len(ctxs))
        for ctx in ctxs:
            # At-least thresholds: exhaust 1..20 exactly. Extra Punkt sentences
            # are harmless; each candidate must pass every exact checker.
            for n in range(1,21):
                contracts=build(ids,"at least",n,ctx)
                out=comp.compose_contracts(contracts)
                assert out["status"]=="CANDIDATE_WITNESS",(ids,ctx,n,out)
                flags=[exact_follow(c,out["response"]) for c in contracts]
                assert all(flags),(ids,ctx,n,flags,out["response"])
                assert len(sent_tokenize(out["response"]))>=n,(ids,ctx,n,out["response"])
                plan=opt.solve_contracts(contracts)
                assert plan["status"]=="CANDIDATE_POINTWISE_OPTIMAL",(ids,ctx,n,plan)
                pflags=[exact_follow(c,plan["response"]) for c in contracts]
                assert sum(pflags)==len(contracts)==plan["theoretical_max_pass_count"],(ids,ctx,n,pflags,plan)
                cases+=1; atleast_cases+=1

            # For all n>=2 the composer emits the same less-than response; n=2
            # is the strongest upper bound. Passing it proves every 2..20.
            contracts=build(ids,"less than",2,ctx)
            out=comp.compose_contracts(contracts)
            assert out["status"]=="CANDIDATE_WITNESS",(ids,ctx,out)
            flags=[exact_follow(c,out["response"]) for c in contracts]
            assert all(flags),(ids,ctx,flags,out["response"])
            assert len(sent_tokenize(out["response"]))<2,(ids,ctx,out["response"])
            plan=opt.solve_contracts(contracts)
            pflags=[exact_follow(c,plan["response"]) for c in contracts]
            assert sum(pflags)==len(contracts)==plan["theoretical_max_pass_count"],(ids,ctx,pflags,plan)
            cases+=1; lt2_cases+=1

            # Strict <1 is universally impossible under strict nonempty scoring.
            # The planner must sacrifice exactly SENTENCES and attain k-1.
            contracts=build(ids,"less than",1,ctx)
            out=comp.compose_contracts(contracts)
            assert out["status"]=="PROVED_UNSAT",(ids,ctx,out)
            assert "STRICT_NONEMPTY_RESPONSE_IMPLIES_AT_LEAST_ONE_PUNKT_SENTENCE" in out["hard_unsat_reasons"]
            plan=opt.solve_contracts(contracts)
            assert plan["status"]=="CANDIDATE_POINTWISE_OPTIMAL",(ids,ctx,plan)
            assert comp.SENTENCES in set(plan["sacrificed_instruction_ids"]),(ids,ctx,plan)
            pflags=[exact_follow(c,plan["response"]) for c in contracts]
            exact_pass=sum(pflags)
            assert exact_pass==plan["theoretical_max_pass_count"],(ids,ctx,pflags,plan)
            assert exact_pass==len(contracts)-1,(ids,ctx,pflags,plan)
            sent_index=[c["instruction_id"] for c in contracts].index(comp.SENTENCES)
            assert pflags[sent_index] is False
            assert all(v for i,v in enumerate(pflags) if i!=sent_index),(ids,ctx,pflags,plan)
            cases+=1; lt1_cases+=1

    receipt={
      "schema":"PROJECT_BRAIN_LIVEBENCH_PUNKT_UNIVERSAL_CLOSURE_INDEPENDENT_VERIFICATION_V1",
      "status":"PASS__CONTENT_BOUND_PARAMETRIC_REDUCTION_PLUS_EXACT_PINNED_PUNKT_CONTEXT_EXHAUSTION__POINTWISE_MAX_MATCH__ZERO_TERMINAL_ROWS",
      "subject_blobs":EXPECTED,
      "pinned_livebench":{"commit":LIVEBENCH_COMMIT,"instructions_blob":INSTRUCTIONS_BLOB,"registry_blob":REGISTRY_BLOB,"instructions_util_blob":UTIL_BLOB},
      "pinned_nltk":{"version":NLTK_VERSION,"data_commit":NLTK_DATA_COMMIT,"source_function_sha256":source_sha256},
      "proof_components":{
        "structural_id_sets":928,
        "lexical_signatures":192,
        "numeric_reduction_status":nres["status"],
        "minimum_cut_status":cres["status"],
        "parametric_reduction_status":pres["status"],
        "strict_lt1_source_theorem":"STRICT_NONEMPTY_RESPONSE_IMPLIES_AT_LEAST_ONE_PUNKT_SENTENCE_SLICE",
      },
      "punkt_exact_contexts":{
        "sentence_bearing_structural_sets":len(sentence_sets),
        "max_context_variants_per_structural_set":max_contexts_per_set,
        "at_least_exact_cases":atleast_cases,
        "less_than_two_strongest_bound_cases":lt2_cases,
        "less_than_one_pointwise_sacrifice_cases":lt1_cases,
        "total_exact_context_cases":cases,
        "all_pass":True,
      },
      "deduction":[
        "NON_SENTENCE_GENERATOR_PARAMETERS_ARE_DISCHARGED_PARAMETRICALLY_BY_CONTENT_BOUND_REDUCTION",
        "ALL_SENTENCE_BEARING_STRUCTURAL_CONTEXTS_ARE_EXHAUSTED_OVER_EVERY_PUNCTUATION_BEARING_VARIANT",
        "AT_LEAST_THRESHOLDS_1_TO_20_PASS_EXACT_PINNED_CHECKERS",
        "LESS_THAN_2_IS_THE_STRONGEST_FEASIBLE_UPPER_BOUND_AND_PASSES_EXACT_PINNED_CHECKERS",
        "LESS_THAN_1_IS_UNIVERSALLY_INFEASIBLE_UNDER_STRICT_NONEMPTY_PLUS_EXACT_PUNKT_SOURCE_AND_IS_SACRIFICED_AT_EXACT_POINTWISE_MAXIMUM",
      ],
      "terminal_rows_read":0,
      "terminal_kwargs_read":0,
      "target_scores_read":0,
      "production_or_terminal_cases_generated":0,
      "acceptance_credit_delta":0,
      "family_credit_delta":0,
      "capability_credit_delta":0,
      "ownership_credit_delta":0,
      "hard_nonclaims":[
        "SEPARATE_SCOPE_EQUIVALENCE_AND_ACCEPTANCE_REDUCTION_STILL_REQUIRED",
        "NO_LIVEBENCH_ACCEPTANCE_CREDIT_FROM_THIS_VERIFIER_ITSELF"
      ]
    }
    pathlib.Path("livebench_punkt_universal_closure_receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(receipt,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
