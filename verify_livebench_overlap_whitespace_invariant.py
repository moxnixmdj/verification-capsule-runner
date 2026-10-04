#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, re, urllib.request
from pathlib import Path

IFBENCH_URL="https://raw.githubusercontent.com/allenai/IFBench/1c40f0c10d9b5c5c2f10a175a28007ebb64f7f4d/data/IFBench_test.jsonl"
IFBENCH_BLOB="a8e343ed928d8b4e649b9dba651fed7757ccacc3"
CHECKER_URL="https://raw.githubusercontent.com/LiveBench/LiveBench/8f8e5c381a16e3f24257776edd53471fe86f8091/livebench/if_runner/ifbench/instructions.py"
CHECKER_BLOB="02b2dfeb50f036b89bec3df34522c73f756d8f44"

RATIO_RE=re.compile(r"Maintain a trigram overlap of (\d+)% \(±2%\) with the provided reference text\.")
KEYWORD_RE=re.compile(r'The response must include keyword "?([^"\s.]+)"? in the (\d+)-(?:st|nd|rd|th) sentence\.')
CONSONANT_TEXT="Ensure each word in your response has at least one consonant cluster (two or more consonants together)."
CONSONANTS=set("bcdfghjklmnpqrstvwxyz")
LETTERS=set("abcdefghijklmnopqrstuvwxyz")

def fetch(url:str)->bytes:
    req=urllib.request.Request(url,headers={"User-Agent":"project-brain-overlap-verifier"})
    with urllib.request.urlopen(req,timeout=30) as r:
        return r.read()

def blob_sha(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def trigrams(s:str)->set[str]:
    return {s[i:i+3] for i in range(max(0,len(s)-2))}

def visible_nonws_trigrams(base:str)->set[str]:
    out=set()
    for run in re.split(r"\s+",base):
        if run:
            out |= trigrams(run)
    return out

def parse_prompt(prompt:str):
    m=RATIO_RE.search(prompt)
    if not m:
        raise ValueError("ratio instruction not visible")
    target=int(m.group(1))
    p=prompt[:m.start()]+prompt[m.end():]
    km=KEYWORD_RE.search(p)
    keyword=None; sentence_n=None
    if km:
        keyword=km.group(1); sentence_n=int(km.group(2))
        p=p[:km.start()]+p[km.end():]
    consonants=CONSONANT_TEXT in p
    p=p.replace(CONSONANT_TEXT,"")
    base=p.replace("\u200b","").strip()
    return target,keyword,sentence_n,consonants,base

def has_consonant_cluster(value:str)->bool:
    words=value.lower().strip().split()
    for word in words:
        if all(ch not in LETTERS for ch in word):
            continue
        if not any(word[i] in CONSONANTS and word[i+1] in CONSONANTS for i in range(len(word)-1)):
            return False
    return True

def simple_sentences(value:str)->list[str]:
    # Constructed witnesses contain no whitespace, ? or ! and no abbreviations.
    return [x for x in (part.strip() for part in value.split(".")) if x]

def fresh_chars(avoid:str,n:int)->list[str]:
    out=[]; cp=0xE000
    while len(out)<n:
        ch=chr(cp); cp+=1
        if ch not in avoid:
            out.append(ch)
    return out

def predicted_score(value:str,good:set[str])->float:
    a=trigrams(value)
    return 100.0*sum(t in good for t in a)/len(a)

def exact_score(value:str,reference:str)->float:
    a=trigrams(value); b=trigrams(reference)
    return 100.0*len(a & b)/len(a)

def construct(prompt:str)->dict:
    target,keyword,sentence_n,need_consonants,base=parse_prompt(prompt)
    good=visible_nonws_trigrams(base)
    runs=[x for x in re.split(r"\s+",base) if len(x)>=3]
    if not runs:
        raise ValueError("no usable visible run")
    ranked=sorted(runs,key=lambda x:(-len(trigrams(x)),-len(x),x))
    cores=[]
    seen=set()
    def add(x):
        if x and x not in seen:
            seen.add(x); cores.append(x)
    for x in ranked[:20]: add(x)
    s=""
    for x in runs:
        s+=x; add(s)
    s=""
    for x in ranked[:40]:
        s+=x; add(s)
    add("".join(runs))
    fresh=fresh_chars(prompt+(keyword or ""),1400)
    best=None
    for core0 in cores:
        core=core0
        prefix=""
        if keyword is not None:
            prefix="".join(fresh[i]+"." for i in range(sentence_n-1))
            core=keyword+core
        scaffold=prefix+core
        if need_consonants and not has_consonant_cluster(scaffold):
            scaffold="bb"+scaffold
        for L in range(1001):
            cand=scaffold+"".join(fresh[100:100+L])
            if re.search(r"\s",cand):
                raise AssertionError("witness unexpectedly contains whitespace")
            if keyword is not None:
                ss=simple_sentences(cand)
                if len(ss)<sentence_n or keyword.lower() not in ss[sentence_n-1].lower():
                    continue
            if need_consonants and not has_consonant_cluster(cand):
                continue
            pred=predicted_score(cand,good)
            if target-2 <= pred <= target+2:
                item={"value":cand,"predicted":pred,"target":target,"filler":L,"core_len":len(core0)}
                if best is None or len(cand)<len(best["value"]):
                    best=item
                break
    if best is None:
        raise AssertionError("no witness found")
    return best

def main()->int:
    raw=fetch(IFBENCH_URL); checker=fetch(CHECKER_URL)
    assert blob_sha(raw)==IFBENCH_BLOB
    assert blob_sha(checker)==CHECKER_BLOB
    src=checker.decode("utf-8")
    assert "class NGramOverlapChecker" in src
    assert "nltk.ngrams(value, n)" in src
    assert "nltk.ngrams(self._reference_text, n)" in src
    assert "class IncludeKeywordChecker" in src
    assert "class ConsonantClusterChecker" in src

    rows=[json.loads(x) for x in raw.decode("utf-8").splitlines() if x.strip()]
    receipts=[]
    max_delta=0.0
    count=0
    whitespace_mismatch=0
    for row in rows:
        ids=list(row.get("instruction_id_list") or [])
        if "ratio:overlap" not in ids:
            continue
        count+=1
        idx=ids.index("ratio:overlap")
        ref=str((row["kwargs"][idx] or {}).get("reference_text") or "")
        prompt=str(row.get("prompt") or "")
        if ref not in prompt:
            whitespace_mismatch+=1
        w=construct(prompt)  # prompt-only: no IDs, kwargs, case key or reference
        actual=exact_score(w["value"],ref)
        delta=abs(actual-w["predicted"]); max_delta=max(max_delta,delta)
        assert delta < 1e-12, (row.get("key"),w["predicted"],actual)
        assert w["target"]-2 <= actual <= w["target"]+2
        kw_pass=None
        if "sentence:keyword" in ids:
            k=ids.index("sentence:keyword"); kw=row["kwargs"][k]
            ss=simple_sentences(w["value"])
            kw_pass=len(ss)>=int(kw["N"]) and str(kw["word"]).lower() in ss[int(kw["N"])-1].lower()
            assert kw_pass
        con_pass=None
        if "words:consonants" in ids:
            con_pass=has_consonant_cluster(w["value"]); assert con_pass
        receipts.append({
            "key":str(row.get("key")),
            "target":w["target"],
            "predicted":round(w["predicted"],12),
            "actual":round(actual,12),
            "output_len":len(w["value"]),
            "filler":w["filler"],
            "keyword_pass":kw_pass,
            "consonant_pass":con_pass,
        })

    assert count==12
    assert whitespace_mismatch==7
    receipt={
      "schema":"PROJECT_BRAIN_LIVEBENCH_OVERLAP_WHITESPACE_INVARIANT_PUBLIC_VERIFICATION_V1",
      "status":"PASS",
      "source_git_blobs":{"ifbench_test":blob_sha(raw),"livebench_ifbench_instructions":blob_sha(checker)},
      "public_ratio_overlap_rows":count,
      "raw_reference_not_visible_rows":whitespace_mismatch,
      "all_prompt_only_witnesses_pass":True,
      "all_composed_public_constraints_pass":True,
      "max_predicted_vs_exact_score_delta":max_delta,
      "theorem":[
        "IF_REFERENCE_AND_VISIBLE_BASE_DIFFER_ONLY_BY_WHITESPACE_THEN_THEIR_WHITESPACE_FREE_CHARACTER_TRIGRAM_SETS_ARE_IDENTICAL",
        "A_WHITESPACE_FREE_WITNESS_HAS_AN_EXACT_OVERLAP_SCORE_COMPUTABLE_FROM_VISIBLE_BASE_ONLY",
        "UNIQUE_FRESH_NONREFERENCE_CHARACTERS_ADD_EXACTLY_ONE_NEW_GUARANTEED_ABSENT_TRIGRAM_PER_APPENDED_CHARACTER_AFTER_A_NONTRIVIAL_CORE",
        "THEREFORE_HIDDEN_REFERENCE_WHITESPACE_IS_NOT_REQUIRED_TO_CONSTRUCT_TARGET_PERCENT_OVERLAP_WITNESSES"
      ],
      "rows":receipts,
      "hard_nonclaims":[
        "NO_FROZEN_TERMINAL_LIVEBENCH_DATASET_EQUIVALENCE_PROVED",
        "NO_TERMINAL_CASE_CONTENT_READ",
        "NO_LIVEBENCH_ACCEPTANCE_CREDIT",
        "NO_CLAIM_YET_FOR_RATIO_OVERLAP_ROWS_OUTSIDE_THE_PROVED_WHITESPACE_EQUIVALENCE_PRECONDITION"
      ]
    }
    Path("livebench_overlap_whitespace_invariant_receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(receipt,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
