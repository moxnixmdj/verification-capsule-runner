#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from pathlib import Path

URL = "https://raw.githubusercontent.com/google-research/google-research/e49bbfe381c9c0e564b937f1c4e163a2273c65cc/instruction_following_eval/data/input_data.jsonl"
BLOB = "cbe52f6eecf3986fdac745b4acba4da1408eb146"

ONES = {
    "zero":0,"one":1,"two":2,"three":3,"four":4,"five":5,"six":6,
    "seven":7,"eight":8,"nine":9,"ten":10,"eleven":11,"twelve":12,
    "thirteen":13,"fourteen":14,"fifteen":15,"sixteen":16,
    "seventeen":17,"eighteen":18,"nineteen":19,
}
TENS = {"twenty":20,"thirty":30,"forty":40,"fifty":50,"sixty":60,"seventy":70,"eighty":80,"ninety":90}
NUM = (
    r"(?:\d+|zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|"
    r"twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|"
    r"twenty(?:[- ](?:one|two|three|four|five|six|seven|eight|nine))?|"
    r"thirty(?:[- ](?:one|two|three|four|five|six|seven|eight|nine))?|"
    r"forty(?:[- ](?:one|two|three|four|five|six|seven|eight|nine))?|"
    r"fifty(?:[- ](?:one|two|three|four|five|six|seven|eight|nine))?|"
    r"sixty(?:[- ](?:one|two|three|four|five|six|seven|eight|nine))?|"
    r"seventy(?:[- ](?:one|two|three|four|five|six|seven|eight|nine))?|"
    r"eighty(?:[- ](?:one|two|three|four|five|six|seven|eight|nine))?|"
    r"ninety(?:[- ](?:one|two|three|four|five|six|seven|eight|nine))?)"
)

def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def number(s: str) -> int:
    raw = re.sub(r"[-\s]+", " ", s.strip().lower())
    if raw.isdigit():
        return int(raw)
    if raw in ONES:
        return ONES[raw]
    if raw in TENS:
        return TENS[raw]
    p = raw.split()
    if len(p)==2 and p[0] in TENS and p[1] in ONES:
        return TENS[p[0]] + ONES[p[1]]
    raise AssertionError(("number", s))

def add(regions, key, lo=None, hi=None):
    old = regions.get(key, (None, None))
    old_lo, old_hi = old
    lo = max(x for x in (old_lo, lo) if x is not None) if old_lo is not None or lo is not None else None
    hi = min(x for x in (old_hi, hi) if x is not None) if old_hi is not None or hi is not None else None
    assert lo is None or hi is None or lo <= hi, (key, old, (lo,hi))
    regions[key] = (lo, hi)

def parse_count(prompt: str, noun: str, key, regions):
    p=prompt
    pats=[
        (rf"(?P<a>{NUM})\s+(?:to|through)\s+(?P<b>{NUM})\s+{noun}", lambda m:(number(m["a"]),number(m["b"]))),
        (rf"(?:between|in\s+the\s+range\s+of)\s+(?P<a>{NUM})\s+(?:and|to)\s+(?P<b>{NUM})\s+{noun}", lambda m:(number(m["a"]),number(m["b"]))),
        (rf"(?P<a>{NUM})\s+or\s+(?P<b>{NUM})\s+{noun}", lambda m:(number(m["a"]),number(m["b"]))),
        (rf"exactly\s+(?P<a>{NUM})\s+{noun}", lambda m:(number(m["a"]),number(m["a"]))),
    ]
    for pat, fn in pats:
        for m in re.finditer(pat,p,re.I):
            add(regions,key,*fn(m))
    if noun.startswith("sentenc"):
        pat=rf"(?P<a>{NUM})[- ]line\b[\s\S]{{0,180}}?each\s+line[\s\S]{{0,80}}?exactly\s+one\s+sentence"
        for m in re.finditer(pat,p,re.I):
            x=number(m["a"]); add(regions,key,x,x)

def parse_keyword(prompt: str, regions):
    keytok=r"[A-Za-z][A-Za-z0-9_-]*"
    specs=[
        (rf"(?:the\s+word|word|keyword)\s+[\"']?(?P<k>{keytok})[\"']?[\s\S]{{0,24}}?(?:appear|appears|be\s+used)?\s*(?P<a>{NUM})\s+(?:to|through)\s+(?P<b>{NUM})\s+times", lambda m:(number(m["a"]),number(m["b"]))),
        (rf"(?:the\s+word|word|keyword)\s+[\"']?(?P<k>{keytok})[\"']?[\s\S]{{0,24}}?(?:appear|appears|be\s+used)?\s*(?P<a>{NUM})\s+or\s+(?P<b>{NUM})\s+times", lambda m:(number(m["a"]),number(m["b"]))),
        (rf"(?:the\s+word|word|keyword)\s+[\"']?(?P<k>{keytok})[\"']?\s+(?:should\s+)?(?:appear|appears|be\s+used)?\s*at\s+least\s+(?P<a>{NUM})\s+times", lambda m:(number(m["a"]),None)),
        (rf"(?:use|include|mention)\s+(?:the\s+)?(?:word|keyword)\s+[\"']?(?P<k>{keytok})[\"']?[\s\S]{{0,28}}?at\s+least\s+(?P<a>{NUM})\s+times", lambda m:(number(m["a"]),None)),
        (rf"(?:the\s+word|word|keyword)\s+[\"']?(?P<k>{keytok})[\"']?[\s\S]{{0,30}}?(?:at\s+most|no\s+more\s+than)\s+(?P<a>{NUM})(?:\s+times|\b)", lambda m:(None,number(m["a"]))),
    ]
    for pat,fn in specs:
        for m in re.finditer(pat,prompt,re.I):
            add(regions,("keywords:frequency",m["k"].lower()),*fn(m))

def parse_capital(prompt: str, regions):
    context=r"(?:words?\s+(?:with\s+)?(?:all\s+)?capital\s+letters|all[- ]caps\s+words?|(?:such\s+)?capitalized\s+words?)"
    for m in re.finditer(rf"(?P<a>{NUM})\s+(?:to|through)\s+(?P<b>{NUM})\s+{context}",prompt,re.I):
        add(regions,("change_case:capital_word_frequency","all_capital_words"),number(m["a"]),number(m["b"]))
    for m in re.finditer(rf"{context}[\s\S]{{0,45}}?less\s+than\s+(?P<a>{NUM})\s+times",prompt,re.I):
        add(regions,("change_case:capital_word_frequency","all_capital_words"),None,number(m["a"])-1)
    for m in re.finditer(rf"{context}[\s\S]{{0,45}}?at\s+most\s+(?P<a>{NUM})\s+times",prompt,re.I):
        add(regions,("change_case:capital_word_frequency","all_capital_words"),None,number(m["a"]))
    positive=re.compile(
        r"(?:use|include|have)\s+(?:(?:some|a\s+few)\s+)?words?\s+"
        r"(?:in\s+all\s+caps|with\s+(?:all\s+)?capital\s+letters|in\s+all\s+capital\s+letters)",
        re.I,
    )
    if positive.search(prompt):
        add(regions,("change_case:capital_word_frequency","all_capital_words"),1,None)

def visible_regions(prompt: str):
    regions={}
    parse_count(prompt,r"words?\b",("length_constraints:number_words","response_words"),regions)
    parse_count(prompt,r"sentences?\b",("length_constraints:number_sentences","response_sentences"),regions)
    parse_keyword(prompt,regions)
    parse_capital(prompt,regions)
    return regions

def hidden_regions(row):
    groups={}
    ids=row.get("instruction_id_list") or []
    kws=row.get("kwargs") or []
    for i,iid in enumerate(ids):
        kw=kws[i] if i < len(kws) and isinstance(kws[i],dict) else {}
        if iid=="length_constraints:number_words":
            key=(iid,"response_words"); rel=kw["relation"]; n=int(kw["num_words"])
        elif iid=="length_constraints:number_sentences":
            key=(iid,"response_sentences"); rel=kw["relation"]; n=int(kw["num_sentences"])
        elif iid=="keywords:frequency":
            key=(iid,str(kw["keyword"]).lower()); rel=kw["relation"]; n=int(kw["frequency"])
        elif iid=="change_case:capital_word_frequency":
            key=(iid,"all_capital_words"); rel=kw["capital_relation"]; n=int(kw["capital_frequency"])
        else:
            continue
        if rel=="at least":
            add(groups,key,n,None)
        elif rel=="less than":
            add(groups,key,None,n-1)
        else:
            raise AssertionError((iid,rel))
    return groups

def main():
    req=urllib.request.Request(URL,headers={"User-Agent":"project-brain-independent-verifier"})
    with urllib.request.urlopen(req,timeout=30) as f:
        raw=f.read()
    assert git_blob_sha(raw)==BLOB,(git_blob_sha(raw),BLOB)
    rows=[json.loads(x) for x in raw.decode().splitlines() if x.strip()]
    assert len(rows)==541

    duplicate_rows=[]
    by_id={}
    extra=0
    for row in rows:
        counts={}
        for iid in row.get("instruction_id_list") or []:
            counts[iid]=counts.get(iid,0)+1
        d={k:v for k,v in counts.items() if v>1}
        if d:
            duplicate_rows.append(row)
            for iid,n in d.items():
                by_id[iid]=by_id.get(iid,0)+1
                extra += n-1

    assert len(duplicate_rows)==17,len(duplicate_rows)
    assert extra==17,extra
    assert by_id=={
        "change_case:capital_word_frequency":5,
        "keywords:frequency":3,
        "length_constraints:number_sentences":6,
        "length_constraints:number_words":2,
        "startend:quotation":1,
    },by_id

    numeric_verified=0
    quotation_verified=0
    failures=[]
    for row in duplicate_rows:
        hidden=hidden_regions(row)
        visible=visible_regions(str(row.get("prompt") or ""))
        for key, expected in hidden.items():
            got=visible.get(key)
            if got!=expected:
                failures.append({"key":row.get("key"),"constraint":key,"expected":expected,"got":got})
            else:
                numeric_verified += 1
        ids=row.get("instruction_id_list") or []
        if ids.count("startend:quotation")>1:
            q=[(row.get("kwargs") or [])[i] for i,x in enumerate(ids) if x=="startend:quotation"]
            assert all(x=={} for x in q),q
            assert "double quotation" in str(row.get("prompt") or "").lower()
            quotation_verified += 1

    assert not failures,failures
    assert numeric_verified==16,numeric_verified
    assert quotation_verified==1,quotation_verified

    receipt={
        "schema":"PROJECT_BRAIN_LIVEBENCH_LEGACY_CARDINALITY_REGION_INDEPENDENT_VERIFICATION_V1",
        "status":"PASS",
        "public_source":{
            "repository":"google-research/google-research",
            "commit":"e49bbfe381c9c0e564b937f1c4e163a2273c65cc",
            "path":"instruction_following_eval/data/input_data.jsonl",
            "git_blob_sha":git_blob_sha(raw),
            "rows":len(rows),
        },
        "duplicate_structure":{
            "rows_with_duplicate_instruction_ids":len(duplicate_rows),
            "extra_duplicate_instances":extra,
            "by_family":by_id,
            "numeric_semantic_regions_exactly_recovered":numeric_verified,
            "parameterless_idempotent_quotation_duplicate_rows":quotation_verified,
        },
        "verified_deductions":[
            "BLIND_DEDUPLICATION_BY_INSTRUCTION_ID_IS_UNSOUND_ON_PUBLIC_LEGACY_IFEVAL",
            "SAME_FAMILY_DUPLICATES_CAN_ENCODE_RANGE_INTERSECTIONS_OR_DISTINCT_SELECTOR_CONSTRAINTS",
            "THE_17_PUBLIC_DUPLICATE_ROWS_ARE_EXACTLY_REPRESENTABLE_AS_SEMANTIC_FEASIBLE_REGIONS_PLUS_ONE_PARAMETERLESS_IDEMPOTENT_DUPLICATE",
            "VISIBLE_SEMANTIC_REGIONS_AVOID_DEPENDENCE_ON_HIDDEN_OFF_BY_ONE_CHECKER_PARAMETERIZATION_FOR_THE_VERIFIED_DUPLICATE_CARDINALITY_SURFACE",
        ],
        "hard_nonclaims":[
            "NO_FROZEN_TERMINAL_DISTRIBUTION_EQUIVALENCE",
            "NO_TERMINAL_PROMPT_OR_KWARG_CONTENT_READ",
            "NO_LIVEBENCH_ACCEPTANCE_OR_CAPABILITY_CREDIT",
            "NO_CLAIM_ALL_541_ROWS_OR_ALL_25_TYPES_ARE_FULLY_COMPILED",
        ],
    }
    Path("livebench_legacy_cardinality_region_receipt.json").write_text(
        json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8"
    )
    print(json.dumps(receipt,sort_keys=True))

if __name__=="__main__":
    main()
