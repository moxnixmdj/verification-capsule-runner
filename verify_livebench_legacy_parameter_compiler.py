#!/usr/bin/env python3
from __future__ import annotations

import ast
import hashlib
import importlib
import json
import re
import sys
import tempfile
import urllib.request
from pathlib import Path

LIVEBENCH_COMMIT="8f8e5c381a16e3f24257776edd53471fe86f8091"
BASE_RAW=f"https://raw.githubusercontent.com/LiveBench/LiveBench/{LIVEBENCH_COMMIT}/livebench/if_runner/instruction_following_eval"
PINNED_BLOBS={
    "instructions.py":"4997bab885a676d92545fd91a9a20b48d234a2b2",
    "instructions_registry.py":"903ed738398648c7cfac61d5ffa478c22f1f0891",
    "instructions_util.py":"1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b",
}
BASE_REQUEST="Explain why deterministic verification matters"

STATIC = {
    "detectable_format:json_format":
        "Entire output should be wrapped in JSON format. You can use markdown ticks such as ```.",
    "detectable_format:title":
        "Your answer must contain a title, wrapped in double angular brackets, such as <<poem of joy>>.",
    "combination:two_responses":
        "Give two different responses. Responses and only responses should be separated by 6 asterisk symbols: ******.",
    "combination:repeat_prompt":
        "First repeat the request word for word without change, then give your answer (1. do not say any words or characters before repeating the request; 2. the request you need to repeat does not include this sentence)",
    "change_case:english_capital":
        "Your entire response should be in English, and in all capital letters.",
    "change_case:english_lowercase":
        "Your entire response should be in English, and in all lowercase letters. No capital letters are allowed.",
    "punctuation:no_comma":
        "In your entire response, refrain from the use of any commas.",
    "startend:quotation":
        'Wrap your entire response with double quotation marks.',
}

def fetch(url:str)->bytes:
    req=urllib.request.Request(url,headers={"User-Agent":"project-brain-legacy-parser-verifier"})
    with urllib.request.urlopen(req,timeout=30) as r:
        return r.read()

def blob_sha(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def load_pinned():
    td=tempfile.TemporaryDirectory()
    pkg=Path(td.name)/"instruction_following_eval"
    pkg.mkdir()
    (pkg/"__init__.py").write_text("",encoding="utf-8")
    observed={}
    for name,want in PINNED_BLOBS.items():
        data=fetch(f"{BASE_RAW}/{name}")
        got=blob_sha(data)
        assert got==want,(name,got,want)
        observed[name]=got
        (pkg/name).write_bytes(data)
    sys.path.insert(0,td.name)
    util=importlib.import_module("instruction_following_eval.instructions_util")
    instructions=importlib.import_module("instruction_following_eval.instructions")
    registry=importlib.import_module("instruction_following_eval.instructions_registry")
    return td,util,instructions,registry,observed

def _literal_list(s:str):
    v=ast.literal_eval(s)
    assert isinstance(v,(list,tuple,set))
    return list(v)

def parse_visible_constraints(prompt:str, language_name_to_code:dict[str,str]):
    found=[]

    def add(iid,args,start,end,text):
        found.append({"id":iid,"args":args,"span":(start,end),"text":text})

    patterns=[
      ("keywords:existence", r"Include keywords (\[[^\n]*?\]) in the response\.",
       lambda m:{"keywords":_literal_list(m.group(1))}),
      ("keywords:frequency", r"In your response, the word (.+?) should appear (less than|at least) (\d+) times\.",
       lambda m:{"keyword":m.group(1).strip(),"relation":m.group(2),"frequency":int(m.group(3))}),
      ("keywords:forbidden_words", r"Do not include keywords (\[[^\n]*?\]) in the response\.",
       lambda m:{"forbidden_words":_literal_list(m.group(1))}),
      ("keywords:letter_frequency", r"In your response, the letter ([A-Za-z]) should appear (less than|at least) (\d+) times\.",
       lambda m:{"letter":m.group(1).lower(),"let_relation":m.group(2),"let_frequency":int(m.group(3))}),
      ("language:response_language", r"Your ENTIRE response should be in (.+?) language, no other language is allowed\.",
       lambda m:{"language":language_name_to_code[m.group(1)]}),
      ("length_constraints:number_sentences", r"Your response should contain (less than|at least) (\d+) sentences\.",
       lambda m:{"relation":m.group(1),"num_sentences":int(m.group(2))}),
      ("length_constraints:number_paragraphs", r"There should be (\d+) paragraphs\. Paragraphs are separated with the markdown divider: \*\*\*",
       lambda m:{"num_paragraphs":int(m.group(1))}),
      ("length_constraints:number_words", r"Answer with (less than|at least) (\d+) words\.",
       lambda m:{"relation":m.group(1),"num_words":int(m.group(2))}),
      ("length_constraints:nth_paragraph_first_word",
       r"There should be (\d+) paragraphs\. Paragraphs and only paragraphs are separated with each other by two new lines as if it was '\\n\\n' in python\. Paragraph (\d+) must start with word (.+?)\.",
       lambda m:{"num_paragraphs":int(m.group(1)),"nth_paragraph":int(m.group(2)),"first_word":m.group(3).strip()}),
      ("detectable_content:number_placeholders",
       r"The response must contain at least (\d+) placeholders represented by square brackets, such as \[address\]\.",
       lambda m:{"num_placeholders":int(m.group(1))}),
      ("detectable_content:postscript",
       r"At the end of your response, please explicitly add a postscript starting with (P\.S\.|P\.P\.S\.?)",
       lambda m:{"postscript_marker":m.group(1)}),
      ("detectable_format:number_bullet_lists",
       r"Your answer must contain exactly (\d+) bullet points\. Use the markdown bullet points such as:\n\* This is point 1\. \n\* This is point 2",
       lambda m:{"num_bullets":int(m.group(1))}),
      ("detectable_format:constrained_response",
       r"Answer with one of the following options: \('My answer is yes\.', 'My answer is no\.', 'My answer is maybe\.'\)",
       lambda m:{}),
      ("detectable_format:number_highlighted_sections",
       r"Highlight at least (\d+) sections in your answer with markdown, i\.e\. \*highlighted section\*\.",
       lambda m:{"num_highlights":int(m.group(1))}),
      ("detectable_format:multiple_sections",
       r"Your response must have (\d+) sections\. Mark the beginning of each section with (SECTION|Section) X, such as:\n(?:SECTION|Section) 1\n\[content of section 1\]\n(?:SECTION|Section) 2\n\[content of section 2\]",
       lambda m:{"num_sections":int(m.group(1)),"section_spliter":m.group(2)}),
      ("startend:end_checker",
       r"Finish your response with this exact phrase (.+?)\. No other words should follow this phrase\.",
       lambda m:{"end_phrase":m.group(1).strip()}),
      ("change_case:capital_word_frequency",
       r"In your response, words with all capital letters should appear (less than|at least) (\d+) times\.",
       lambda m:{"capital_relation":m.group(1),"capital_frequency":int(m.group(2))}),
    ]
    for iid,pat,fn in patterns:
        for m in re.finditer(pat,prompt,re.DOTALL):
            add(iid,fn(m),m.start(),m.end(),m.group(0))

    for iid,text0 in STATIC.items():
        start=0
        while True:
            p=prompt.find(text0,start)
            if p<0: break
            add(iid,{},p,p+len(text0),text0)
            start=p+len(text0)

    # Remove overlapping duplicates conservatively.
    found.sort(key=lambda x:(x["span"][0],-(x["span"][1]-x["span"][0]),x["id"]))
    nonoverlap=[]
    for x in found:
        if any(not (x["span"][1] <= y["span"][0] or x["span"][0] >= y["span"][1]) for y in nonoverlap):
            continue
        nonoverlap.append(x)

    # Repeat-prompt's hidden parameter is the original request. Reconstruct it
    # only from visible text by deleting every recognized instruction sentence.
    repeat=[x for x in nonoverlap if x["id"]=="combination:repeat_prompt"]
    if repeat:
        chars=list(prompt)
        for x in sorted(nonoverlap,key=lambda z:z["span"][0],reverse=True):
            a,b=x["span"]
            del chars[a:b]
        base="".join(chars).strip()
        base=re.sub(r"[ \t]+\n","\n",base)
        base=re.sub(r"\n[ \t]+","\n",base)
        base=re.sub(r"[ \t]{2,}"," ",base).strip()
        for x in repeat:
            x["args"]={"prompt_to_repeat":base}

    return sorted(nonoverlap,key=lambda x:(x["span"][0],x["id"]))

def instantiate(registry,iid,args):
    obj=registry.INSTRUCTION_DICT[iid](iid)
    obj.build_description(**args)
    return obj

def canon_args(args):
    if args is None: return {}
    out={}
    for k,v in args.items():
        if isinstance(v,set): v=sorted(v)
        elif isinstance(v,tuple): v=list(v)
        out[k]=v
    return out

def main()->int:
    td,util,instructions,registry,blobs=load_pinned()
    try:
        reverse={name:code for code,name in util.LANGUAGE_CODES.items()}
        active=list(registry.INSTRUCTION_DICT.keys())
        assert len(active)==25,len(active)

        sample_args={
          "keywords:existence":{"keywords":["alpha","beta"]},
          "keywords:frequency":{"keyword":"alpha","frequency":3,"relation":"at least"},
          "keywords:forbidden_words":{"forbidden_words":["omega","zeta"]},
          "keywords:letter_frequency":{"letter":"q","let_frequency":4,"let_relation":"less than"},
          "language:response_language":{"language":"en"},
          "length_constraints:number_sentences":{"num_sentences":4,"relation":"at least"},
          "length_constraints:number_paragraphs":{"num_paragraphs":3},
          "length_constraints:number_words":{"num_words":17,"relation":"less than"},
          "length_constraints:nth_paragraph_first_word":{"num_paragraphs":3,"nth_paragraph":2,"first_word":"alpha"},
          "detectable_content:number_placeholders":{"num_placeholders":3},
          "detectable_content:postscript":{"postscript_marker":"P.S."},
          "detectable_format:number_bullet_lists":{"num_bullets":4},
          "detectable_format:constrained_response":{},
          "detectable_format:number_highlighted_sections":{"num_highlights":3},
          "detectable_format:multiple_sections":{"section_spliter":"SECTION","num_sections":3},
          "detectable_format:json_format":{},
          "detectable_format:title":{},
          "combination:two_responses":{},
          "combination:repeat_prompt":{"prompt_to_repeat":BASE_REQUEST},
          "startend:end_checker":{"end_phrase":"THE END"},
          "change_case:capital_word_frequency":{"capital_frequency":3,"capital_relation":"at least"},
          "change_case:english_capital":{},
          "change_case:english_lowercase":{},
          "punctuation:no_comma":{},
          "startend:quotation":{},
        }
        assert set(sample_args)==set(active)

        descriptions={}
        ground={}
        for iid in active:
            obj=registry.INSTRUCTION_DICT[iid](iid)
            desc=obj.build_description(**sample_args[iid])
            descriptions[iid]=desc
            ground[iid]=canon_args(obj.get_instruction_args())

        # Single-template reconstruction.
        singles=[]
        for iid in active:
            prompt=BASE_REQUEST+" "+descriptions[iid]
            got=parse_visible_constraints(prompt,reverse)
            assert len(got)==1,(iid,got,prompt)
            assert got[0]["id"]==iid,(iid,got)
            want=ground[iid]
            have=canon_args(got[0]["args"])
            assert have==want,(iid,have,want)
            singles.append(iid)

        # Pairwise coverage over every conflict-compatible grammar pair. This
        # proves composition of the recognizers, not witness satisfiability.
        conflicts={k:set(v) for k,v in registry.INSTRUCTION_CONFLICTS.items()}
        pairs=0
        repeat_pairs=0
        for i,a in enumerate(active):
            for b in active[i+1:]:
                if b in conflicts.get(a,set()) or a in conflicts.get(b,set()):
                    continue
                # Synthetic base has no comma so repeat+no_comma remains valid.
                prompt=BASE_REQUEST+" "+descriptions[a]+" "+descriptions[b]
                got=parse_visible_constraints(prompt,reverse)
                by={x["id"]:canon_args(x["args"]) for x in got}
                assert set(by)=={a,b},(a,b,by,prompt)
                assert by[a]==ground[a],(a,b,a,by[a],ground[a])
                assert by[b]==ground[b],(a,b,b,by[b],ground[b])
                if a=="combination:repeat_prompt" or b=="combination:repeat_prompt":
                    rid="combination:repeat_prompt"
                    assert by[rid]["prompt_to_repeat"]==BASE_REQUEST,(a,b,by[rid])
                    repeat_pairs+=1
                pairs+=1

        receipt={
          "schema":"PROJECT_BRAIN_LIVEBENCH_LEGACY_VISIBLE_PARAMETER_COMPILER_VERIFICATION_V1",
          "status":"PASS",
          "frozen_public_source":{"commit":LIVEBENCH_COMMIT,"git_blobs":blobs},
          "active_legacy_instruction_types":len(active),
          "single_template_reconstruction_passes":len(singles),
          "conflict_compatible_pair_reconstruction_passes":pairs,
          "repeat_prompt_pair_reconstruction_passes":repeat_pairs,
          "terminal_dataset_rows_read":0,
          "terminal_prompt_content_read":False,
          "hidden_kwargs_used_by_compiler":False,
          "proved":[
            "ALL_25_ACTIVE_LEGACY_BUILD_DESCRIPTION_FORMS_ARE_RECOGNIZED_ON_SYNTHETIC_PUBLIC_SOURCE_GENERATIONS",
            "VISIBLE_PARAMETERS_ARE_RECONSTRUCTED_EXACTLY_FOR_ALL_25_SINGLE_FORMS",
            "RECOGNIZERS_COMPOSE_ACROSS_EVERY_CONFLICT_COMPATIBLE_PAIR_IN_THE_PUBLIC_GRAMMAR",
            "REPEAT_PROMPT_HIDDEN_PREFIX_IS_RECONSTRUCTED_FROM_VISIBLE_PROMPT_BY_DELETING_RECOGNIZED_INSTRUCTION_DESCRIPTIONS",
          ],
          "hard_nonclaims":[
            "NO_RESPONSE_WITNESS_SYNTHESIS_PROVED_YET",
            "NO_TERMINAL_LIVEBENCH_SCORE_PROVED",
            "NO_ACCEPTANCE_OR_PROMOTION_CREDIT",
          ],
        }
        Path("livebench_legacy_parameter_compiler_receipt.json").write_text(
          json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print(json.dumps(receipt,sort_keys=True))
        return 0
    finally:
        td.cleanup()

if __name__=="__main__":
    raise SystemExit(main())
