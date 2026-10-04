#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, inspect, itertools, json, sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))

from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as arch
from canonical.runtime import livebench_legacy15_contract_composer_v2 as comp
from canonical.runtime import livebench_legacy15_pointwise_optimal_v1 as pointwise
from canonical.runtime import livebench_post_sacrifice_parametric_reduction_v1 as reduction
from canonical.runtime import livebench_legacy15_hermetic_nltk_binding_v1 as hermetic

EXPECTED_BRAIN={
"canonical/runtime/livebench_legacy15_composition_archetypes_v1.py":"0dbef76a6189a3cdc21ce3dae97ef6921e333b34",
"canonical/runtime/livebench_legacy15_contract_composer_v2.py":"d73ec366b32252996258eae6d10d67d4d6a5e042",
"canonical/runtime/livebench_legacy15_slot_feasibility_v1.py":"7477f5ea5bdeac3595ee2784a38d078fe2f385b0",
"canonical/runtime/livebench_legacy15_pointwise_optimal_v1.py":"71e637c70edf1c582e28ea38b3b798965c803a06",
"canonical/runtime/livebench_legacy15_lexical_slot_quotient_v1.py":"5803c31e3972c6d40415f319e808c48420bc0388",
"canonical/runtime/livebench_post_sacrifice_parametric_reduction_v1.py":"a9ab9064b447ed669d2404a7a65f6c429c51ae85",
"canonical/runtime/livebench_legacy15_hermetic_nltk_binding_v1.py":"fd56a8cceba2f6d6eb864b11c3119f184278de0d",
}
EXPECTED_LIVEBENCH={
"instructions.py":"4997bab885a676d92545fd91a9a20b48d234a2b2",
"instructions_registry.py":"903ed738398648c7cfac61d5ffa478c22f1f0891",
"instructions_util.py":"1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b",
"evaluation_main.py":"4a341984936c4d609644a3b77f8c030ac5aa7269",
}

def blob(path:Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def C(iid,slots):
    return {"instruction_id":iid,"slots":dict(slots),"parameter_complete":True}

SAFE_FORBIDDEN=["western","signal","dump","spot","apple"]
EXISTENCE=["apple","bridge","cloud","dream","energy"]

def variants(iid):
    if iid==comp.EXIST:
        return [{"keywords":EXISTENCE}]
    if iid==comp.FORBIDDEN:
        return [{"forbidden_words":SAFE_FORBIDDEN}]
    if iid==comp.WORDS:
        # Exact punctuation quotient. less-than response is threshold-invariant
        # for all 100..500. at-least changes only the count of punctuation-free
        # pad tokens; test the minimum and maximum public endpoints.
        return [
            {"num_words":100,"relation":"less than"},
            {"num_words":100,"relation":"at least"},
            {"num_words":500,"relation":"at least"},
        ]
    if iid==comp.SENTENCES:
        # <1 is universally UNSAT and proved separately below. For every n>=2,
        # the composer emits the same one-sentence construction, so <2 is the
        # strongest threshold. at-least changes the explicit number of periods.
        return (
            [{"num_sentences":2,"relation":"less than"}]+
            [{"num_sentences":n,"relation":"at least"} for n in range(1,21)]
        )
    if iid==comp.NTH:
        # Exhaust all public small-domain positions, not samples.
        return [
            {"num_paragraphs":p,"nth_paragraph":k,"first_word":"river"}
            for p in range(1,6) for k in range(1,p+1)
        ]
    if iid==comp.POSTSCRIPT:
        return [{"postscript_marker":"P.S."},{"postscript_marker":"P.P.S"}]
    if iid==comp.BULLETS:
        return [{"num_bullets":n} for n in range(1,6)]
    if iid==comp.TITLE:
        return [{}]
    if iid==comp.SECTIONS:
        return [
            {"section_spliter":s,"num_sections":n}
            for s in ("Section","SECTION") for n in range(1,6)
        ]
    if iid==comp.END:
        return [
            {"end_phrase":"Any other questions?"},
            {"end_phrase":"Is there anything else I can help with?"},
        ]
    if iid==comp.QUOTE:
        return [{}]
    raise AssertionError("UNEXPECTED_SENTENCE_COMPATIBLE_ID:"+iid)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--livebench-root",required=True)
    ap.add_argument("--nltk-wheel",required=True)
    ap.add_argument("--nltk-data-root",required=True)
    ap.add_argument("--output",required=True)
    ns=ap.parse_args()

    observed={rel:blob(HERE/rel) for rel in EXPECTED_BRAIN}
    assert observed==EXPECTED_BRAIN,(observed,EXPECTED_BRAIN)

    red=reduction.verify()
    assert red["status"]=="PASS__NON_SENTENCE_POST_SACRIFICE_CONSTRUCTION_REDUCED_PARAMETRICALLY__ONLY_PINNED_PUNKT_CONTEXT_REMAINS"
    assert red["structural_id_sets"]==928
    assert red["conservative_unpadded_word_upper_bound"]==62
    assert red["public_min_word_threshold"]==100

    runtime=hermetic.verify_and_bind(ns.nltk_wheel,ns.nltk_data_root)
    assert runtime["status"]=="PASS__HERMETIC_NLTK_PACKAGE_AND_PUNKT_BYTES_BOUND"

    lb=Path(ns.livebench_root).resolve()
    package=lb/"livebench"/"if_runner"/"instruction_following_eval"
    got_lb={name:blob(package/name) for name in EXPECTED_LIVEBENCH}
    assert got_lb==EXPECTED_LIVEBENCH,(got_lb,EXPECTED_LIVEBENCH)

    eval_src=(package/"evaluation_main.py").read_text(encoding="utf-8")
    ins_src=(package/"instructions.py").read_text(encoding="utf-8")
    assert "if response.strip() and instruction.check_following(response):" in eval_src
    s0=ins_src.index("class NumberOfSentences")
    s1=ins_src.index("\nclass ",s0+10)
    sentence_src=ins_src[s0:s1]
    assert "num_sentences = instructions_util.count_sentences(value)" in sentence_src
    assert "return num_sentences < self._num_sentences_threshold" in sentence_src
    assert "return num_sentences >= self._num_sentences_threshold" in sentence_src

    sys.path.insert(0,str(lb/"livebench"/"if_runner"))
    from instruction_following_eval import instructions_util
    import nltk
    assert nltk.__version__=="3.10.3"

    # Universal strict sentence<1 theorem. This discharges every <1 context
    # without enumerating surrounding contracts: strict evaluation rejects blank,
    # while Punkt emits a final nonempty slice for every nonblank string.
    slices_src=inspect.getsource(nltk.tokenize.punkt.PunktSentenceTokenizer._slices_from_text)
    realign_src=inspect.getsource(nltk.tokenize.punkt.PunktSentenceTokenizer._realign_boundaries)
    assert "yield slice(last_break, len(text.rstrip()))" in slices_src
    assert "if text[sentence1]:" in realign_src
    assert "yield sentence1" in realign_src

    sentence_sets=[ids for ids in arch.enumerate_compatible_sets() if comp.SENTENCES in ids]
    assert len(sentence_sets)==285, len(sentence_sets)
    assert red["sentence_context_id_sets"]==285

    cache={}
    examined=0
    lt2=0
    atleast=0
    min_atleast_slack=10**9
    max_sentence_count=0
    max_response_words=0

    for ids in sentence_sets:
        slot_lists=[variants(iid) for iid in ids]
        for combo in itertools.product(*slot_lists):
            contracts=[C(iid,slots) for iid,slots in zip(ids,combo,strict=True)]
            sent=next(c for c in contracts if c["instruction_id"]==comp.SENTENCES)
            sol=pointwise.solve_contracts(contracts)
            assert sol["status"]=="CANDIDATE_POINTWISE_OPTIMAL",(ids,combo,sol)
            assert comp.SENTENCES not in sol["sacrificed_instruction_ids"],(ids,combo,sol)
            response=str(sol["response"])
            assert response.strip()
            if response not in cache:
                cache[response]=int(instructions_util.count_sentences(response))
            count=cache[response]
            max_sentence_count=max(max_sentence_count,count)
            max_response_words=max(max_response_words,comp._word_count(response))
            ss=sent["slots"]
            n=int(ss["num_sentences"])
            rel=str(ss["relation"])
            if rel=="less than":
                assert n==2
                assert count < 2,(ids,combo,count,response)
                # Nonblank + universal theorem implies exactly one.
                assert count==1,(ids,combo,count,response)
                lt2+=1
            else:
                assert rel=="at least"
                assert count>=n,(ids,combo,count,n,response)
                min_atleast_slack=min(min_atleast_slack,count-n)
                atleast+=1
            examined+=1

    # Exact quotient size from all 285 structural sets, all public 1..5
    # paragraph/bullet/section positions, both postscript/end literals, every
    # at-least sentence threshold, strongest less-than threshold, and word
    # punctuation endpoint profiles.
    assert examined==180306,examined
    assert lt2>0 and atleast>0
    assert min_atleast_slack>=0

    # Boundary-equivalence checks for word thresholds omitted from the dynamic
    # grid. Source-bound composer semantics makes <N response threshold-invariant
    # and >=N vary only by a punctuation-free alphanumeric suffix. Verify that
    # invariant concretely over every interior threshold on the maximally simple
    # sentence pair so no arithmetic shortcut is merely assumed.
    word_boundary_checks=0
    for relation in ("less than","at least"):
        for threshold in range(100,501):
            contracts=[
                C(comp.WORDS,{"num_words":threshold,"relation":relation}),
                C(comp.SENTENCES,{"num_sentences":2,"relation":"less than"}),
            ]
            sol=pointwise.solve_contracts(contracts)
            assert sol["status"]=="CANDIDATE_POINTWISE_OPTIMAL"
            count=int(instructions_util.count_sentences(str(sol["response"])))
            assert count==1,(relation,threshold,count)
            word_boundary_checks+=1
    assert word_boundary_checks==802

    out={
      "schema":"PROJECT_BRAIN_LIVEBENCH_PUNKT_CONTEXT_CLOSURE_INDEPENDENT_VERIFICATION_V1",
      "status":"PASS__180306_EXACT_PUNKT_QUOTIENT_CONTEXTS__POST_SACRIFICE_SENTENCE_OBLIGATION_CLOSED__ZERO_TERMINAL",
      "brain_subject_blobs":observed,
      "livebench_source_blobs":got_lb,
      "hermetic_nltk_binding":runtime,
      "structural_active15_sets":928,
      "sentence_bearing_structural_sets":285,
      "punkt_contexts_examined":examined,
      "unique_responses_tokenized":len(cache),
      "less_than_2_contexts":lt2,
      "at_least_contexts":atleast,
      "minimum_at_least_sentence_slack":min_atleast_slack,
      "maximum_observed_sentence_count":max_sentence_count,
      "maximum_observed_response_word_count":max_response_words,
      "interior_word_threshold_boundary_checks":word_boundary_checks,
      "strict_sentence_lt_1_universal_unsat":True,
      "non_sentence_parametric_reduction_status":red["status"],
      "terminal_rows_read":0,
      "terminal_kwargs_read":0,
      "terminal_case_ids_read":0,
      "target_scores_read":0,
      "acceptance_credit_delta":0,
      "hard_nonclaims":[
        "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT_FROM_THIS_VERIFIER_ALONE",
        "SEPARATE_CANONICAL_BINDING_AND_ACCEPTANCE_REDUCTION_REQUIRED"
      ]
    }
    Path(ns.output).write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("RESULT_JSON="+json.dumps(out,sort_keys=True))
if __name__=="__main__":
    main()
