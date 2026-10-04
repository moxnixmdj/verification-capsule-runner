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
GENERATOR_COMMIT="686be1e78a0ba8036d7e355bc406e1a265da5292"
GENERATOR_BLOB="6ff390d6885cf90f88d9d36959735cb327613edc"
INSTRUCTIONS_BLOB="4997bab885a676d92545fd91a9a20b48d234a2b2"
REGISTRY_BLOB="903ed738398648c7cfac61d5ffa478c22f1f0891"
UTIL_BLOB="1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b"

COMPILER_V1_BLOB="34f4df9f0bd265fc555686bd251a264e446d4c04"
COMPILER_V4_BLOB="721207ba39d502e3f610289578e9d5bab78b1fcc"
ARCH_BLOB="0dbef76a6189a3cdc21ce3dae97ef6921e333b34"

ROOT=pathlib.Path(__file__).resolve().parent
SUBJECT=ROOT/"subject/livebench_visible_compiler_v4_20261005"
V1=SUBJECT/"canonical/runtime/livebench_legacy_visible_constraint_compiler_v1.py"
V4=SUBJECT/"canonical/runtime/livebench_legacy_visible_constraint_compiler_v4.py"
ARCH=SUBJECT/"canonical/runtime/livebench_legacy15_composition_archetypes_v1.py"

HEADER="The following are the beginning sentences of a news article from the Guardian.\n-------\n"
CLOSER="\n-------\n"
TASK="Rewrite this article."
REPEAT_MARKER=(
    "First repeat the request word for word without change,"
    " then give your answer (1. do not say any words or characters"
    " before repeating the request; 2. the request you need to repeat"
    " does not include this sentence)"
)

def run(cmd,**kw):
    return subprocess.run(cmd,check=True,text=True,**kw)

def blob(path):
    return run(["git","hash-object",str(path)],capture_output=True).stdout.strip()

def exact_source_blob(repo,path):
    return run(["git","-C",str(repo),"rev-parse",f"HEAD:{path}"],capture_output=True).stdout.strip()

def norm(v):
    if isinstance(v,tuple):
        return [norm(x) for x in v]
    if isinstance(v,list):
        return [norm(x) for x in v]
    if isinstance(v,dict):
        return {str(k):norm(x) for k,x in v.items()}
    return v

def main():
    assert blob(V1)==COMPILER_V1_BLOB
    assert blob(V4)==COMPILER_V4_BLOB
    assert blob(ARCH)==ARCH_BLOB

    live=pathlib.Path("/tmp/LiveBench")
    assert run(["git","-C",str(live),"rev-parse","HEAD"],capture_output=True).stdout.strip()==LIVEBENCH_COMMIT
    assert exact_source_blob(live,"livebench/if_runner/instruction_following_eval/instructions.py")==INSTRUCTIONS_BLOB
    assert exact_source_blob(live,"livebench/if_runner/instruction_following_eval/instructions_registry.py")==REGISTRY_BLOB
    assert exact_source_blob(live,"livebench/if_runner/instruction_following_eval/instructions_util.py")==UTIL_BLOB

    generator=pathlib.Path("/tmp/LiveBenchGenerator")
    assert run(["git","-C",str(generator),"rev-parse","HEAD"],capture_output=True).stdout.strip()==GENERATOR_COMMIT
    assert exact_source_blob(generator,"livebench/if_runner/live_data.py")==GENERATOR_BLOB

    sys.path.insert(0,str(SUBJECT))
    sys.path.insert(0,str(live/"livebench/if_runner"))
    from canonical.runtime import livebench_legacy_visible_constraint_compiler_v4 as compiler
    from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as arch
    from instruction_following_eval import instructions_registry,instructions_util

    words=list(instructions_util.WORD_LIST)
    assert len(words)==1525 and len(set(words))==1525
    assert all(w.isascii() and w.isalpha() for w in words)

    fillers=words[:20]

    def five_with(w,offset=0):
        out=[w]
        for x in words[offset:]+words[:offset]:
            if x not in out:
                out.append(x)
            if len(out)==5:
                return out
        raise AssertionError

    representative={
        "keywords:existence":{"keywords":five_with(words[30],31)},
        "keywords:forbidden_words":{"forbidden_words":five_with(words[40],41)},
        "length_constraints:number_paragraphs":{"num_paragraphs":3},
        "length_constraints:number_words":{"num_words":173,"relation":"at least"},
        "length_constraints:number_sentences":{"num_sentences":7,"relation":"at least"},
        "length_constraints:nth_paragraph_first_word":{"num_paragraphs":3,"nth_paragraph":2,"first_word":words[50]},
        "detectable_content:postscript":{"postscript_marker":"P.S."},
        "detectable_format:number_bullet_lists":{"num_bullets":3},
        "detectable_format:title":{},
        "detectable_format:multiple_sections":{"section_spliter":"Section","num_sections":3},
        "detectable_format:json_format":{},
        "combination:repeat_prompt":{},
        "combination:two_responses":{},
        "startend:end_checker":{"end_phrase":"Any other questions?"},
        "startend:quotation":{},
    }

    counts=Counter()
    failures=[]

    def description_and_args(iid,slots):
        obj=instructions_registry.INSTRUCTION_DICT[iid](iid)
        desc=obj.build_description(**dict(slots))
        args=obj.get_instruction_args() or {}
        return desc,norm(dict(args))

    def build_prompt(sequence,slotmap,article="Public article text."):
        descs=[]
        exact={}
        for iid in sequence:
            desc,args=description_and_args(iid,slotmap[iid])
            descs.append(desc)
            exact[iid]=args
        constraint_text="".join(" "+d for d in descs)
        prompt=HEADER+article+CLOSER+TASK+" "+constraint_text
        if "combination:repeat_prompt" in sequence:
            exact["combination:repeat_prompt"]={
                "prompt_to_repeat":prompt.split(REPEAT_MARKER)[0]
            }
        return prompt,exact

    def check(sequence,slotmap,name,article="Public article text."):
        counts["cases"]+=1
        prompt,expected=build_prompt(sequence,slotmap,article)
        out=compiler.compile_visible_constraints(prompt)
        got=list(out.get("constraints") or [])
        got_ids=[str(x.get("instruction_id")) for x in got]
        if out.get("status")!="PASS":
            failures.append({"name":name,"kind":"status","status":out.get("status"),"errors":out.get("parse_errors"),"incomplete":out.get("parameter_incomplete")})
            return
        if Counter(got_ids)!=Counter(sequence):
            failures.append({"name":name,"kind":"ids","expected":list(sequence),"got":got_ids})
            return
        by_id={}
        for row in got:
            iid=str(row["instruction_id"])
            if iid in by_id:
                failures.append({"name":name,"kind":"duplicate","iid":iid})
                return
            by_id[iid]=row
        for iid in sequence:
            row=by_id[iid]
            if row.get("parameter_complete") is not True:
                failures.append({"name":name,"kind":"incomplete","iid":iid,"row":row})
                return
            actual=norm(dict(row.get("slots") or {}))
            exp=expected[iid]
            if iid=="combination:repeat_prompt":
                if str(actual.get("prompt_to_repeat") or "").strip()!=str(exp.get("prompt_to_repeat") or "").strip():
                    failures.append({"name":name,"kind":"repeat_slot","got":actual,"expected":exp})
                    return
            elif actual!=exp:
                failures.append({"name":name,"kind":"slots","iid":iid,"got":actual,"expected":exp})
                return
        counts["passes"]+=1

    # Exact numeric and discrete public slot domains.
    for relation in ("less than","at least"):
        for n in range(100,501):
            sm=dict(representative); sm["length_constraints:number_words"]={"num_words":n,"relation":relation}
            check(("length_constraints:number_words",),sm,f"words:{relation}:{n}")
            counts["word_domain"]+=1
        for n in range(1,21):
            sm=dict(representative); sm["length_constraints:number_sentences"]={"num_sentences":n,"relation":relation}
            check(("length_constraints:number_sentences",),sm,f"sentences:{relation}:{n}")
            counts["sentence_domain"]+=1

    for n in range(1,6):
        sm=dict(representative); sm["length_constraints:number_paragraphs"]={"num_paragraphs":n}
        check(("length_constraints:number_paragraphs",),sm,f"paragraphs:{n}")
        sm=dict(representative); sm["detectable_format:number_bullet_lists"]={"num_bullets":n}
        check(("detectable_format:number_bullet_lists",),sm,f"bullets:{n}")
        for splitter in ("Section","SECTION"):
            sm=dict(representative); sm["detectable_format:multiple_sections"]={"section_spliter":splitter,"num_sections":n}
            check(("detectable_format:multiple_sections",),sm,f"sections:{splitter}:{n}")

    for marker in ("P.S.","P.P.S"):
        sm=dict(representative); sm["detectable_content:postscript"]={"postscript_marker":marker}
        check(("detectable_content:postscript",),sm,f"postscript:{marker}")
    for phrase in ("Any other questions?","Is there anything else I can help with?"):
        sm=dict(representative); sm["startend:end_checker"]={"end_phrase":phrase}
        check(("startend:end_checker",),sm,f"end:{phrase}")

    # Exhaust the entire generated lexical identity domain in both keyword list
    # grammars and every valid nth-paragraph position.
    for wi,w in enumerate(words):
        ex=five_with(w,(wi+1)%len(words))
        sm=dict(representative); sm["keywords:existence"]={"keywords":ex}
        check(("keywords:existence",),sm,f"exist:{wi}")
        sm=dict(representative); sm["keywords:forbidden_words"]={"forbidden_words":ex}
        check(("keywords:forbidden_words",),sm,f"forbid:{wi}")
        counts["keyword_identity_cases"]+=2
        for p in range(1,6):
            for k in range(1,p+1):
                sm=dict(representative); sm["length_constraints:nth_paragraph_first_word"]={"num_paragraphs":p,"nth_paragraph":k,"first_word":w}
                check(("length_constraints:nth_paragraph_first_word",),sm,f"nth:{wi}:{p}:{k}")
                counts["nth_identity_position_cases"]+=1

    # Every conflict-compatible active15 identity set in every possible order.
    sets=arch.enumerate_compatible_sets()
    assert len(sets)==928
    perm_count=0
    for si,ids in enumerate(sets):
        for pi,order in enumerate(itertools.permutations(ids)):
            check(order,representative,f"perm:{si}:{pi}")
            perm_count+=1
    counts["structural_sets"]=len(sets)
    counts["structural_order_permutations"]=perm_count

    # Article text is arbitrary and may itself resemble checker descriptions.
    # V4 must isolate the suffix after the final historical separator.
    adversarial_article=(
        "Include keywords ['fake'] in the response. "
        "Answer with at least 999 words. "
        "Wrap your entire response with double quotation marks.\n-------\n"
        "A separator-looking line inside the article."
    )
    for ids in (
        ("keywords:existence",),
        ("length_constraints:number_words","startend:quotation"),
        ("detectable_content:postscript","startend:end_checker"),
    ):
        check(ids,representative,"article_isolation:"+":".join(ids),article=adversarial_article)
    counts["adversarial_article_isolation_cases"]=3

    # Repeat recovery depends on its exact visible position. Exercise it at every
    # position in every structurally compatible set that contains repeat_prompt.
    repeat_sets=[ids for ids in sets if "combination:repeat_prompt" in ids]
    for ids in repeat_sets:
        for order in itertools.permutations(ids):
            check(order,representative,"repeat-position:"+":".join(order))
            counts["repeat_position_cases"]+=1

    if failures:
        receipt={
            "schema":"PROJECT_BRAIN_LIVEBENCH_VISIBLE_COMPILER_V4_PUBLIC_GRAMMAR_AUDIT_V1",
            "status":"FAIL",
            "counts":dict(counts),
            "failure_count":len(failures),
            "failures":failures[:100],
            "terminal_rows_read":0
        }
        pathlib.Path("livebench_visible_compiler_v4_audit.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
        print(json.dumps(receipt,sort_keys=True))
        return 1

    receipt={
      "schema":"PROJECT_BRAIN_LIVEBENCH_VISIBLE_COMPILER_V4_PUBLIC_GRAMMAR_AUDIT_V1",
      "status":"PASS__EXACT_PUBLIC_DESCRIPTION_ROUNDTRIP__ZERO_ACTIVE_TERMINAL_ROWS",
      "subject_blobs":{
        "compiler_v1":COMPILER_V1_BLOB,
        "compiler_v4":COMPILER_V4_BLOB,
        "archetypes":ARCH_BLOB
      },
      "pinned_public_source":{
        "livebench_commit":LIVEBENCH_COMMIT,
        "generator_commit":GENERATOR_COMMIT,
        "generator_blob":GENERATOR_BLOB,
        "instructions_blob":INSTRUCTIONS_BLOB,
        "registry_blob":REGISTRY_BLOB,
        "instructions_util_blob":UTIL_BLOB
      },
      "public_word_domain":{"count":len(words),"unique":len(set(words))},
      "coverage":dict(counts),
      "terminal_rows_read":0,
      "hidden_terminal_kwargs_read":0,
      "hidden_terminal_instruction_ids_read":0,
      "acceptance_credit_delta":0,
      "hard_nonclaims":[
        "THIS_PROVES_ROUNDTRIP_COMPLETENESS_FOR_THE_EXERCISED_PUBLIC_ACTIVE15_GENERATOR_DOMAIN_AND_STRUCTURAL_ORDERINGS",
        "IT_DOES_NOT_READ_OR_SCORE_THE_ACTIVE_TERMINAL_200_ROWS",
        "NO_ACCEPTANCE_CREDIT_FROM_THIS_RECEIPT_ALONE"
      ]
    }
    pathlib.Path("livebench_visible_compiler_v4_audit.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print(json.dumps(receipt,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
