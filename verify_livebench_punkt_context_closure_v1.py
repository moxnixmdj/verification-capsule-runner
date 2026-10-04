#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import itertools
import json
import pathlib
import subprocess
import sys
from collections import Counter

LIVEBENCH_COMMIT="8f8e5c381a16e3f24257776edd53471fe86f8091"
INSTRUCTIONS_BLOB="4997bab885a676d92545fd91a9a20b48d234a2b2"
REGISTRY_BLOB="903ed738398648c7cfac61d5ffa478c22f1f0891"
UTIL_BLOB="1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b"
NLTK_DATA_COMMIT="550b6625bcef1f2abff2ff770a5a0d272c9c6b2a"

ARCH_BLOB="0dbef76a6189a3cdc21ce3dae97ef6921e333b34"
COMPOSER_BLOB="d73ec366b32252996258eae6d10d67d4d6a5e042"
PLANNER_BLOB="71e637c70edf1c582e28ea38b3b798965c803a06"
FEAS_BLOB="7477f5ea5bdeac3595ee2784a38d078fe2f385b0"
LEX_BLOB="5803c31e3972c6d40415f319e808c48420bc0388"
REDUCTION_BLOB="a9ab9064b447ed669d2404a7a65f6c429c51ae85"

ROOT=pathlib.Path(__file__).resolve().parent
SUBJECT=ROOT/"subject/livebench_composer_v2_20261005"
RUNTIME=SUBJECT/"canonical/runtime"

def run(cmd,**kw):
    return subprocess.run(cmd,check=True,text=True,**kw)

def blob(path):
    return run(["git","hash-object",str(path)],capture_output=True).stdout.strip()

def exact_source_blob(repo,path):
    return run(["git","-C",str(repo),"rev-parse",f"HEAD:{path}"],capture_output=True).stdout.strip()

def C(iid,**slots):
    return {"instruction_id":iid,"slots":slots}

def product_options(ids, options):
    keys=list(ids)
    pools=[options[k] for k in keys]
    for vals in itertools.product(*pools):
        yield [C(k,**v) for k,v in zip(keys,vals)]

def main():
    pins={
      "livebench_legacy15_composition_archetypes_v1.py":ARCH_BLOB,
      "livebench_legacy15_contract_composer_v2.py":COMPOSER_BLOB,
      "livebench_legacy15_pointwise_optimal_v1.py":PLANNER_BLOB,
      "livebench_legacy15_slot_feasibility_v1.py":FEAS_BLOB,
      "livebench_legacy15_lexical_slot_quotient_v1.py":LEX_BLOB,
      "livebench_post_sacrifice_parametric_reduction_v1.py":REDUCTION_BLOB,
    }
    for name,expected in pins.items():
        got=blob(RUNTIME/name)
        assert got==expected,(name,expected,got)

    live=pathlib.Path("/tmp/LiveBench")
    assert run(["git","-C",str(live),"rev-parse","HEAD"],capture_output=True).stdout.strip()==LIVEBENCH_COMMIT
    assert exact_source_blob(live,"livebench/if_runner/instruction_following_eval/instructions.py")==INSTRUCTIONS_BLOB
    assert exact_source_blob(live,"livebench/if_runner/instruction_following_eval/instructions_registry.py")==REGISTRY_BLOB
    assert exact_source_blob(live,"livebench/if_runner/instruction_following_eval/instructions_util.py")==UTIL_BLOB

    sys.path.insert(0,str(SUBJECT))
    sys.path.insert(0,str(live/"livebench/if_runner"))
    from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as arch
    from canonical.runtime import livebench_legacy15_contract_composer_v2 as comp
    from canonical.runtime import livebench_post_sacrifice_parametric_reduction_v1 as reduction
    from instruction_following_eval import instructions_registry,instructions_util

    red=reduction.verify()
    assert red["status"]=="PASS__NON_SENTENCE_POST_SACRIFICE_CONSTRUCTION_REDUCED_PARAMETRICALLY__ONLY_PINNED_PUNKT_CONTEXT_REMAINS"
    assert red["sentence_context_id_sets"]==285
    assert red["conservative_unpadded_word_upper_bound"]==62
    assert red["public_min_word_threshold"]==100
    assert red["acceptance_credit"] is False

    words=list(instructions_util.WORD_LIST)
    assert len(words)==1525 and len(set(words))==1525
    assert all(w.isascii() and w.isalpha() for w in words)

    special={"other","anything","can","help","section"}
    safe=[w for w in words if w.lower() not in special]
    assert len(safe)>=20
    exist_words=safe[:5]
    nth_word=safe[5]
    forbid_words=[w for w in safe[6:] if w!=nth_word][:5]
    assert len(forbid_words)==5

    sentence_states=[
      *[{"num_sentences":n,"relation":"less than"} for n in range(2,21)],
      *[{"num_sentences":n,"relation":"at least"} for n in range(1,21)],
    ]
    nth_states=[
      {"num_paragraphs":p,"nth_paragraph":k,"first_word":nth_word}
      for p in range(1,6) for k in range(1,p+1)
    ]
    options={
      comp.EXIST:[{"keywords":exist_words}],
      comp.FORBIDDEN:[{"forbidden_words":forbid_words}],
      comp.WORDS:[
        {"num_words":100,"relation":"less than"},
        {"num_words":100,"relation":"at least"},
        {"num_words":500,"relation":"at least"},
      ],
      comp.SENTENCES:sentence_states,
      comp.NTH:nth_states,
      comp.POSTSCRIPT:[
        {"postscript_marker":"P.S."},
        {"postscript_marker":"P.P.S"},
      ],
      comp.BULLETS:[{"num_bullets":n} for n in range(1,6)],
      comp.TITLE:[{}],
      comp.SECTIONS:[
        {"section_spliter":s,"num_sections":n}
        for s in ("Section","SECTION") for n in range(1,6)
      ],
      comp.END:[
        {"end_phrase":"Any other questions?"},
        {"end_phrase":"Is there anything else I can help with?"},
      ],
      comp.QUOTE:[{}],
    }

    forbidden_with_sentence={comp.PARAGRAPHS,comp.JSON_ID,comp.REPEAT,comp.TWO}
    sentence_sets=[
      ids for ids in arch.enumerate_compatible_sets()
      if comp.SENTENCES in ids
    ]
    assert len(sentence_sets)==285
    assert all(not (set(ids)&forbidden_with_sentence) for ids in sentence_sets)

    counts=Counter()
    failures=[]
    observed_counts=Counter()

    def exact_sentence_check(contracts,label):
        counts["primary_cases"]+=1
        out=comp.compose_contracts(contracts)
        if out.get("status")!="CANDIDATE_WITNESS":
            failures.append({"label":label,"kind":"compose","out":out})
            return
        response=str(out["response"])
        sm={c["instruction_id"]:c["slots"] for c in contracts}
        s=sm[comp.SENTENCES]
        checker=instructions_registry.INSTRUCTION_DICT[comp.SENTENCES](comp.SENTENCES)
        checker.build_description(**s)
        actual=instructions_util.count_sentences(response)
        observed_counts[actual]+=1
        if not checker.check_following(response):
            failures.append({
              "label":label,"kind":"sentence_checker",
              "sentence_slots":s,"actual":actual,"response":response
            })
            return
        if comp.WORDS in sm and sm[comp.WORDS]["relation"]=="less than":
            wc=instructions_util.count_words(response)
            if wc>=100:
                failures.append({"label":label,"kind":"word_lt_basis","wc":wc})
                return
        counts["primary_pass"]+=1

    for si,ids in enumerate(sentence_sets):
        if any(iid not in options for iid in ids):
            raise AssertionError(("MISSING_OPTION_DOMAIN",ids))
        for ci,contracts in enumerate(product_options(ids,options)):
            exact_sentence_check(contracts,f"primary:{si}:{ci}")

    assert counts["primary_cases"]==334854,counts
    assert counts["primary_pass"]==counts["primary_cases"],len(failures)

    # Full omitted word-threshold discharge. The reduction already proves that
    # word padding is the only response mutation as N varies. Here we exhaust
    # N=100..500 against every reachable punctuation-sensitive tail family
    # combination. Prefix-only families (exist/title/sections/bullets) cannot
    # introduce punctuation after the explicit sentence material and were
    # already covered in the 334,854 exact composer cases above.
    tail_families=[comp.NTH,comp.POSTSCRIPT,comp.END,comp.QUOTE]
    tail_sets=[]
    for r in range(0,4):
        for subset in itertools.combinations(tail_families,r):
            ids=(comp.WORDS,comp.SENTENCES,*subset)
            if len(ids)<=5 and arch.compatible(ids):
                tail_sets.append(ids)
    # Include all 3-of-4 subsets; all 4 would exceed the public five-ID maximum.
    assert len(tail_sets)==15

    pad_sentence_states=[
      {"num_sentences":1,"relation":"at least"},
      {"num_sentences":20,"relation":"at least"},
      {"num_sentences":2,"relation":"less than"},
    ]
    pad_options=dict(options)
    pad_options[comp.SENTENCES]=pad_sentence_states
    pad_options[comp.WORDS]=[
      {"num_words":n,"relation":"at least"} for n in range(100,501)
    ]

    pad_fail=[]
    for si,ids in enumerate(tail_sets):
        for ci,contracts in enumerate(product_options(ids,pad_options)):
            counts["padding_sweep_cases"]+=1
            out=comp.compose_contracts(contracts)
            if out.get("status")!="CANDIDATE_WITNESS":
                pad_fail.append({"label":f"pad:{si}:{ci}","kind":"compose","out":out})
                continue
            sm={c["instruction_id"]:c["slots"] for c in contracts}
            response=str(out["response"])
            s=sm[comp.SENTENCES]
            checker=instructions_registry.INSTRUCTION_DICT[comp.SENTENCES](comp.SENTENCES)
            checker.build_description(**s)
            if not checker.check_following(response):
                pad_fail.append({
                  "label":f"pad:{si}:{ci}","kind":"checker",
                  "sentence_slots":s,
                  "word_slots":sm[comp.WORDS],
                  "actual":instructions_util.count_sentences(response),
                  "response":response,
                })
            else:
                counts["padding_sweep_pass"]+=1

    failures.extend(pad_fail)
    assert counts["padding_sweep_pass"]==counts["padding_sweep_cases"],len(pad_fail)

    # Explicitly prove the sacrificed sentence-zero coordinate remains
    # impossible under the exact strict nonempty evaluator premise: every
    # nonempty composer witness in the production Punkt runtime yields >=1.
    zero_checker=instructions_registry.INSTRUCTION_DICT[comp.SENTENCES](comp.SENTENCES)
    zero_checker.build_description(num_sentences=1,relation="less than")
    for sample in ("9000001","9000001.","P.S.+","P.P.S","Any other questions?"):
        assert sample.strip()
        c=instructions_util.count_sentences(sample)
        assert c>=1,(sample,c)
        assert zero_checker.check_following(sample) is False
        counts["sentence_zero_basis_cases"]+=1

    receipt={
      "schema":"PROJECT_BRAIN_LIVEBENCH_PUNKT_CONTEXT_CLOSURE_V1",
      "status":(
        "PASS__EXACT_PINNED_PUNKT_CONTEXT_CLOSURE__"
        "334854_STRUCTURAL_PARAMETER_CASES_PLUS_FULL_100_500_PADDING_SWEEP__"
        "ZERO_TERMINAL_ROWS"
      ),
      "subject_blobs":{
        "archetypes":ARCH_BLOB,
        "composer_v2":COMPOSER_BLOB,
        "pointwise_planner":PLANNER_BLOB,
        "slot_feasibility":FEAS_BLOB,
        "lexical_quotient":LEX_BLOB,
        "post_sacrifice_parametric_reduction":REDUCTION_BLOB,
      },
      "pinned_runtime":{
        "livebench_commit":LIVEBENCH_COMMIT,
        "instructions_blob":INSTRUCTIONS_BLOB,
        "registry_blob":REGISTRY_BLOB,
        "instructions_util_blob":UTIL_BLOB,
        "nltk_version":"3.10.3",
        "nltk_data_commit":NLTK_DATA_COMMIT,
      },
      "reduction_status":red["status"],
      "sentence_bearing_structural_id_sets":len(sentence_sets),
      "public_sentence_states_excluding_sacrificed_lt1":len(sentence_states),
      "primary_exact_composer_checker_cases":counts["primary_cases"],
      "primary_exact_composer_checker_pass":counts["primary_pass"],
      "full_word_padding_sweep_cases":counts["padding_sweep_cases"],
      "full_word_padding_sweep_pass":counts["padding_sweep_pass"],
      "sentence_zero_basis_cases":counts["sentence_zero_basis_cases"],
      "observed_sentence_count_histogram":dict(sorted(observed_counts.items())),
      "terminal_rows_read":0,
      "terminal_kwargs_read":0,
      "terminal_instruction_ids_read":0,
      "terminal_frequencies_read":0,
      "target_scores_read":0,
      "acceptance_credit_delta":0,
      "capability_credit_delta":0,
      "ownership_credit_delta":0,
      "theorem_supported":(
        "WHEN_COMBINED_WITH_THE_EXACT_BOUND_POST_SACRIFICE_PARAMETRIC_REDUCTION__"
        "THE_PINNED_PUNKT_RUNTIME_ADDS_NO_REMAINING_GENERATOR_ADMITTED_"
        "POST_SACRIFICE_CONSTRUCTION_COUNTEREXAMPLE_CLASS"
      ),
      "hard_nonclaims":[
        "THIS_RECEIPT_ALONE_DOES_NOT_PROMOTE_LIVEBENCH_ACCEPTANCE",
        "PROMOTION_REQUIRES_BINDING_THIS_INDEPENDENT_RECEIPT_TO_THE_CURRENT_BRAIN_SUBJECT_BYTES",
        "NO_TERMINAL_ACTIVE_ROW_WAS_READ_OR_EXECUTED"
      ]
    }
    pathlib.Path("livebench_punkt_context_closure_v1.json").write_text(
      json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8"
    )
    print(json.dumps(receipt,sort_keys=True))
    if failures:
        print(json.dumps({"failures":failures[:20]},indent=2,sort_keys=True))
        return 1
    return 0

if __name__=="__main__":
    raise SystemExit(main())
