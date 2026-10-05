#!/usr/bin/env python3
from __future__ import annotations

import ast, hashlib, importlib, json, re, sys, urllib.request
from pathlib import Path

COMMIT="8f8e5c381a16e3f24257776edd53471fe86f8091"
BASE=f"https://raw.githubusercontent.com/LiveBench/LiveBench/{COMMIT}/livebench/if_runner/instruction_following_eval"
PINS={
 "instructions.py":"4997bab885a676d92545fd91a9a20b48d234a2b2",
 "instructions_util.py":"1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b",
 "instructions_registry.py":"903ed738398648c7cfac61d5ffa478c22f1f0891",
}

def fetch(name):
    req=urllib.request.Request(f"{BASE}/{name}",headers={"User-Agent":"brain-verifier"})
    return urllib.request.urlopen(req,timeout=60).read()

def blob_sha(data):
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def list_literal(s):
    v=ast.literal_eval(s)
    assert isinstance(v,list)
    return [str(x) for x in v]

LANG_SAMPLE={
 "English":"this is a simple english sentence about ordinary daily life and useful information",
 "Finnish":"tämä on yksinkertainen suomenkielinen lause tavallisesta jokapäiväisestä elämästä ja hyödyllisestä tiedosta",
}

def solve(prompt: str) -> str:
    p=str(prompt)

    m=re.search(r"Include keywords (\[[^\n]+?\]) in the response\.",p,re.I)
    if m:
        return " ".join(list_literal(m.group(1)))

    m=re.search(r"In your response, the word (.+?) should appear (less than|at least) (\d+) times\.",p,re.I)
    if m:
        kw,rel,n=m.group(1),m.group(2).lower(),int(m.group(3))
        return (" ".join([kw]*n)) if rel=="at least" else "zzzzzz"

    m=re.search(r"Do not include keywords (\[[^\n]+?\]) in the response\.",p,re.I)
    if m:
        forbidden={x.lower() for x in list_literal(m.group(1))}
        cand="zzzzzz"
        if cand in forbidden: cand="yyyyyy"
        return cand

    m=re.search(r"In your response, the letter ([A-Za-z]) should appear (less than|at least) (\d+) times\.",p,re.I)
    if m:
        ch,rel,n=m.group(1),m.group(2).lower(),int(m.group(3))
        return (ch*n) if rel=="at least" else "12345"

    m=re.search(r"Your ENTIRE response should be in ([A-Za-z]+) language, no other language is allowed\.",p,re.I)
    if m:
        name=m.group(1).title()
        if name not in LANG_SAMPLE:
            raise ValueError("UNSUPPORTED_LANGUAGE_SAMPLE:"+name)
        return LANG_SAMPLE[name]

    m=re.search(r"Your response should contain (less than|at least) (\d+) sentences\.",p,re.I)
    if m:
        rel,n=m.group(1).lower(),int(m.group(2))
        if rel=="at least":
            return " ".join(f"Item {i} is complete." for i in range(1,n+1))
        if n<=1: raise ValueError("UNSAT_LESS_THAN_ONE_SENTENCE")
        return "one compact sentence"

    m=re.search(r"There should be (\d+) paragraphs\. Paragraphs are separated with the markdown divider: \*\*\*",p,re.I)
    if m:
        n=int(m.group(1))
        return "***".join(f"paragraph{i}" for i in range(1,n+1))

    m=re.search(r"Answer with (less than|at least) (\d+) words\.",p,re.I)
    if m:
        rel,n=m.group(1).lower(),int(m.group(2))
        if rel=="at least": return " ".join(f"w{i}" for i in range(n))
        if n<=1: raise ValueError("UNSAT_LESS_THAN_ONE_WORD")
        return "word"

    m=re.search(
      r"There should be (\d+) paragraphs\. Paragraphs and only paragraphs are separated with each other by two new lines as if it was '\\n\\n' in python\. Paragraph (\d+) must start with word ([^\s.]+)\.",
      p,re.I)
    if m:
        n,k,first=int(m.group(1)),int(m.group(2)),m.group(3)
        parts=[f"paragraph{i} content" for i in range(1,n+1)]
        parts[k-1]=f"{first} content"
        return "\n\n".join(parts)

    m=re.search(r"The response must contain at least (\d+) placeholders represented by square brackets, such as \[address\]\.",p,re.I)
    if m:
        return " ".join(f"[slot{i}]" for i in range(1,int(m.group(1))+1))

    m=re.search(r"At the end of your response, please explicitly add a postscript starting with (.+)$",p,re.I)
    if m:
        return m.group(1).strip()+" content"

    m=re.search(r"Your answer must contain exactly (\d+) bullet points\.",p,re.I)
    if m:
        return "\n".join(f"* item{i}" for i in range(1,int(m.group(1))+1))

    if "Answer with one of the following options:" in p and "My answer is yes." in p:
        return "My answer is yes."

    m=re.search(r"Highlight at least (\d+) sections in your answer with markdown",p,re.I)
    if m:
        return " ".join(f"*highlight{i}*" for i in range(1,int(m.group(1))+1))

    m=re.search(r"Your response must have (\d+) sections\. Mark the beginning of each section with (Section|SECTION) X",p,re.I)
    if m:
        n,splitter=int(m.group(1)),m.group(2)
        return "\n".join(f"{splitter} {i}\ncontent{i}" for i in range(1,n+1))

    if "Entire output should be wrapped in JSON format." in p:
        return "{}"

    if "Your answer must contain a title, wrapped in double angular brackets" in p:
        return "<<title>>"

    if "Give two different responses." in p and "******" in p:
        return "first******second"

    marker="First repeat the request word for word without change, then give your answer"
    pos=p.lower().find(marker.lower())
    if pos>=0:
        base=p[:pos].rstrip()
        if not base: raise ValueError("REPEAT_BASE_NOT_VISIBLE")
        return base

    m=re.search(r"Finish your response with this exact phrase (.+?)\. No other words should follow this phrase\.",p,re.I|re.S)
    if m:
        return m.group(1).strip()

    m=re.search(r"In your response, words with all capital letters should appear (less than|at least) (\d+) times\.",p,re.I)
    if m:
        rel,n=m.group(1).lower(),int(m.group(2))
        return (" ".join(f"WORD{i}" for i in range(n))) if rel=="at least" else "lowercase words only"

    if "Your entire response should be in English, and in all capital letters." in p:
        return "THIS IS A SIMPLE ENGLISH SENTENCE ABOUT ORDINARY DAILY LIFE"

    if "Your entire response should be in English, and in all lowercase letters." in p:
        return "this is a simple english sentence about ordinary daily life"

    if "refrain from the use of any commas" in p:
        return "plain text"

    if "Wrap your entire response with double quotation marks." in p:
        return '"plain text"'

    raise ValueError("NO_SINGLE_CHECKER_ROUTE")

def main():
    root=Path("vendor_legacy_single")
    pkg=root/"instruction_following_eval"
    pkg.mkdir(parents=True,exist_ok=True)
    (pkg/"__init__.py").write_text("")
    for name,sha in PINS.items():
        data=fetch(name)
        assert blob_sha(data)==sha
        (pkg/name).write_bytes(data)
    sys.path.insert(0,str(root.resolve()))
    util=importlib.import_module("instruction_following_eval.instructions_util")
    reg=importlib.import_module("instruction_following_eval.instructions_registry")
    import nltk
    nltk.download("punkt",quiet=True)
    nltk.download("punkt_tab",quiet=True)

    cases={
      "keywords:existence":{"keywords":["nebula","zircon"]},
      "keywords:frequency":{"keyword":"quasar","frequency":3,"relation":"at least"},
      "keywords:forbidden_words":{"forbidden_words":["cobalt","mango"]},
      "keywords:letter_frequency":{"letter":"q","let_frequency":7,"let_relation":"at least"},
      "language:response_language":{"language":"en"},
      "length_constraints:number_sentences":{"num_sentences":4,"relation":"at least"},
      "length_constraints:number_paragraphs":{"num_paragraphs":4},
      "length_constraints:number_words":{"num_words":137,"relation":"at least"},
      "length_constraints:nth_paragraph_first_word":{"num_paragraphs":4,"nth_paragraph":3,"first_word":"zephyr"},
      "detectable_content:number_placeholders":{"num_placeholders":3},
      "detectable_content:postscript":{"postscript_marker":"P.S."},
      "detectable_format:number_bullet_lists":{"num_bullets":4},
      "detectable_format:constrained_response":{},
      "detectable_format:number_highlighted_sections":{"num_highlights":3},
      "detectable_format:multiple_sections":{"section_spliter":"SECTION","num_sections":4},
      "detectable_format:json_format":{},
      "detectable_format:title":{},
      "combination:two_responses":{},
      "combination:repeat_prompt":{"prompt_to_repeat":"Explain a deterministic system clearly."},
      "startend:end_checker":{"end_phrase":"Any other questions?"},
      "change_case:capital_word_frequency":{"capital_frequency":7,"capital_relation":"at least"},
      "change_case:english_capital":{},
      "change_case:english_lowercase":{},
      "punctuation:no_comma":{},
      "startend:quotation":{},
    }
    assert set(cases)==set(reg.INSTRUCTION_DICT)
    results=[]
    for iid,kwargs in cases.items():
        obj=reg.INSTRUCTION_DICT[iid](iid)
        desc=obj.build_description(**kwargs)
        prompt=desc
        if iid=="combination:repeat_prompt":
            prompt=kwargs["prompt_to_repeat"]+"\n"+desc
        response=solve(prompt)
        ok=bool(response.strip()) and bool(obj.check_following(response))
        assert ok,(iid,prompt,response,obj.get_instruction_args())
        results.append({"instruction_id":iid,"pass":ok,"response_preview":response[:80]})

    # Exercise both comparison branches where they exist.
    variants=[
      ("keywords:frequency",{"keyword":"quasar","frequency":3,"relation":"less than"}),
      ("keywords:letter_frequency",{"letter":"q","let_frequency":7,"let_relation":"less than"}),
      ("length_constraints:number_sentences",{"num_sentences":4,"relation":"less than"}),
      ("length_constraints:number_words",{"num_words":137,"relation":"less than"}),
      ("change_case:capital_word_frequency",{"capital_frequency":7,"capital_relation":"less than"}),
      ("language:response_language",{"language":"fi"}),
    ]
    for iid,kwargs in variants:
        obj=reg.INSTRUCTION_DICT[iid](iid)
        desc=obj.build_description(**kwargs)
        response=solve(desc)
        assert response.strip() and obj.check_following(response),(iid,kwargs,desc,response)

    receipt={
      "schema":"PROJECT_BRAIN_LIVEBENCH_LEGACY_25_SINGLE_CHECKER_WITNESS_VERIFICATION_V1",
      "status":"PASS__25_OF_25_LEGACY_CHECKER_FAMILIES_HAVE_PROMPT_ONLY_DETERMINISTIC_SINGLE_CHECKER_WITNESSES",
      "pinned_livebench_commit":COMMIT,
      "pinned_blobs":PINS,
      "registered_checker_families":len(reg.INSTRUCTION_DICT),
      "single_checker_families_passed":len(results),
      "comparison_and_language_variant_cases_passed":len(variants),
      "terminal_dataset_rows_read":0,
      "terminal_prompt_content_read":False,
      "terminal_kwargs_read":False,
      "model_dependency_count":0,
      "incremental_spend_usd":0,
      "acceptance_credit_delta":0,
      "hard_nonclaim":"Single-family closure does not yet prove every allowed multi-checker composition can be jointly satisfied by one response."
    }
    Path("livebench_legacy_25_single_checker_witness_receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print(json.dumps(receipt,sort_keys=True))

if __name__=="__main__":
    main()
