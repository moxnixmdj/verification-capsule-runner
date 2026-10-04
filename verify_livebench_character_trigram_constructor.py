#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, re, urllib.request
from pathlib import Path

DATA_URL = "https://raw.githubusercontent.com/allenai/IFBench/1c40f0c10d9b5c5c2f10a175a28007ebb64f7f4d/data/IFBench_test.jsonl"
DATA_BLOB = "a8e343ed928d8b4e649b9dba651fed7757ccacc3"
SCORER_URL = "https://raw.githubusercontent.com/LiveBench/LiveBench/8f8e5c381a16e3f24257776edd53471fe86f8091/livebench/if_runner/ifbench/instructions.py"
SCORER_BLOB = "02b2dfeb50f036b89bec3df34522c73f756d8f44"

def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent":"project-brain-independent-verifier"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()

def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip()

def grams(s: str) -> set[str]:
    return {s[i:i+3] for i in range(max(0, len(s)-2))}

def choose(ref: str, pct: float):
    best = None
    for tok in re.split(r"\s+", ref):
        if len(tok) < 3:
            continue
        for a in range(len(tok)):
            for b in range(a+3, len(tok)+1):
                sub = tok[a:b]
                O = len(grams(sub))
                if O <= 0:
                    continue
                for m in range(0, 101):
                    score = 100.0 * O / (O + m)
                    err = abs(score - pct)
                    if err <= 2.0 + 1e-12:
                        cand = (m, O, len(sub), sub, score, err)
                        if best is None or cand < best:
                            best = cand
    return best

def fresh_chars(ref: str, m: int) -> str:
    chars=[]
    cp=0xE000
    while len(chars) < m:
        ch=chr(cp)
        cp += 1
        if ch not in ref:
            chars.append(ch)
    return "".join(chars)

def main() -> int:
    raw = fetch(DATA_URL)
    scorer_raw = fetch(SCORER_URL)
    assert git_blob_sha(raw) == DATA_BLOB
    assert git_blob_sha(scorer_raw) == SCORER_BLOB
    scorer = scorer_raw.decode("utf-8")
    assert "class NGramOverlapChecker" in scorer
    assert "ngrams = set(nltk.ngrams(value, n))" in scorer
    assert "ref_ngrams = set(nltk.ngrams(self._reference_text, n))" in scorer
    assert "nltk.word_tokenize" not in scorer[scorer.index("class NGramOverlapChecker"):scorer.index("class NumbersCountChecker")]

    rows=[json.loads(x) for x in raw.decode("utf-8").splitlines() if x.strip()]
    receipts=[]
    for row in rows:
        ids=list(row.get("instruction_id_list") or [])
        kws=list(row.get("kwargs") or [])
        prompt=str(row.get("prompt") or "")
        for i, instruction_id in enumerate(ids):
            if instruction_id != "ratio:overlap":
                continue
            kw=kws[i] if i < len(kws) and isinstance(kws[i],dict) else {}
            ref=str(kw.get("reference_text") or "")
            pct=float(kw.get("percentage"))
            assert ref
            assert norm_ws(ref) in norm_ws(prompt)
            chosen=choose(ref,pct)
            assert chosen is not None, (row.get("key"),pct)
            m,O,_L,B,formula_score,err=chosen
            assert B in ref
            assert B in prompt
            q=fresh_chars(ref,m)
            assert len(set(q)) == m and all(ch not in ref for ch in q)
            z=B+q
            Gz=grams(z)
            Gr=grams(ref)
            actual=100.0*len(Gz & Gr)/len(Gz)
            assert len(grams(B)) == O
            assert len(Gz) == O+m, (row.get("key"),O,m,len(Gz))
            assert len(Gz & Gr) == O, (row.get("key"),O,len(Gz & Gr))
            assert abs(actual-formula_score) < 1e-12
            assert pct-2.0 <= actual <= pct+2.0
            receipts.append({
                "key":str(row.get("key")),
                "target_percent":pct,
                "B":B,
                "O":O,
                "m":m,
                "constructed_percent":actual,
                "compound_instruction_ids":ids,
            })

    assert len(receipts)==12, len(receipts)
    receipt={
        "schema":"PROJECT_BRAIN_LIVEBENCH_CHARACTER_TRIGRAM_CONSTRUCTOR_PUBLIC_VERIFICATION_V1",
        "status":"PASS",
        "pinned_sources":{
            "ifbench_test_git_blob_sha":git_blob_sha(raw),
            "frozen_livebench_scorer_git_blob_sha":git_blob_sha(scorer_raw),
        },
        "verified":{
            "frozen_scorer_uses_character_trigrams":True,
            "public_ratio_overlap_rows":12,
            "normalized_reference_visible_rows":12,
            "constructor_target_existence_rows":12,
            "formula":"overlap=O/(O+m)",
            "rows":receipts,
        },
        "hard_nonclaims":[
            "NO_FULL_TASK_SUCCESS_CLAIM_FOR_COMPOUND_ROWS",
            "NO_EXACT_FROZEN_TERMINAL_DATASET_EQUIVALENCE",
            "NO_LIVEBENCH_ACCEPTANCE_CREDIT",
            "NO_TERMINAL_CASE_DATA_USED",
            "NO_RUNTIME_BASE_SEGMENT_EXTRACTION_PROOF",
        ],
    }
    Path("livebench_character_trigram_constructor_receipt.json").write_text(
        json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8"
    )
    print(json.dumps(receipt,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
