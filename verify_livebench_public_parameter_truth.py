#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, re, urllib.request
from pathlib import Path

IFBENCH_URL = "https://raw.githubusercontent.com/allenai/IFBench/1c40f0c10d9b5c5c2f10a175a28007ebb64f7f4d/data/IFBench_test.jsonl"
IFBENCH_BLOB = "a8e343ed928d8b4e649b9dba651fed7757ccacc3"
CHECKER_URL = "https://raw.githubusercontent.com/LiveBench/LiveBench/8f8e5c381a16e3f24257776edd53471fe86f8091/livebench/if_runner/ifbench/instructions.py"
CHECKER_BLOB = "02b2dfeb50f036b89bec3df34522c73f756d8f44"

def fetch(url: str) -> bytes:
    req=urllib.request.Request(url,headers={"User-Agent":"project-brain-independent-verifier"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()

def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip()

def main() -> int:
    raw = fetch(IFBENCH_URL)
    checker_raw = fetch(CHECKER_URL)
    assert git_blob_sha(raw) == IFBENCH_BLOB, (git_blob_sha(raw), IFBENCH_BLOB)
    assert git_blob_sha(checker_raw) == CHECKER_BLOB, (git_blob_sha(checker_raw), CHECKER_BLOB)
    checker = checker_raw.decode("utf-8")
    assert "class NGramOverlapChecker" in checker
    assert "nltk.ngrams(value, n)" in checker
    assert "nltk.ngrams(self._reference_text, n)" in checker

    rows=[json.loads(x) for x in raw.decode("utf-8").splitlines() if x.strip()]
    overlap={"instruction_rows":0,"raw_reference_visible":0,"normalized_reference_visible":0}
    repeat={"instruction_rows":0,"raw_prompt_visible":0,"score_relevant_slice_equal":0}
    repeat_prompt=0

    for row in rows:
        prompt=str(row.get("prompt") or "")
        ids=list(row.get("instruction_id_list") or [])
        kwargs=list(row.get("kwargs") or [])
        for i, instruction_id in enumerate(ids):
            kw=kwargs[i] if i < len(kwargs) and isinstance(kwargs[i],dict) else {}
            if instruction_id=="ratio:overlap":
                overlap["instruction_rows"]+=1
                ref=str(kw.get("reference_text") or "")
                overlap["raw_reference_visible"]+=int(bool(ref) and ref in prompt)
                overlap["normalized_reference_visible"]+=int(bool(ref) and norm_ws(ref) in norm_ws(prompt))
            elif instruction_id=="repeat:repeat_span":
                repeat["instruction_rows"]+=1
                src=str(kw.get("prompt_to_repeat") or "")
                repeat["raw_prompt_visible"]+=int(bool(src) and src in prompt)
                start,end=kw.get("n_start"),kw.get("n_end")
                if isinstance(start,(int,float)) and isinstance(end,(int,float)):
                    start,end=int(start),int(end)
                    suffix=(
                        f"Copy the span of words that lies between (and including) index {start} and {end}, "
                        "the indices are word indices, split by whitespace!"
                    )
                    if prompt.endswith(suffix):
                        base=prompt[:-len(suffix)].rstrip()
                        a=re.findall(r"\S+",base)[start:end+1]
                        b=re.findall(r"\S+",src)[start:end+1]
                        repeat["score_relevant_slice_equal"]+=int(a==b)
            elif instruction_id=="combination:repeat_prompt":
                repeat_prompt+=1

    expected={
        "rows":300,
        "ratio_overlap":{"instruction_rows":12,"raw_reference_visible":5,"normalized_reference_visible":12},
        "repeat_span":{"instruction_rows":4,"raw_prompt_visible":3,"score_relevant_slice_equal":4},
        "legacy_repeat_prompt_rows":0,
    }
    actual={"rows":len(rows),"ratio_overlap":overlap,"repeat_span":repeat,"legacy_repeat_prompt_rows":repeat_prompt}
    assert actual==expected,(actual,expected)

    receipt={
        "schema":"PROJECT_BRAIN_LIVEBENCH_PUBLIC_PARAMETER_TRUTH_INDEPENDENT_VERIFICATION_V1",
        "status":"PASS",
        "source_git_blobs":{"ifbench_test":git_blob_sha(raw),"livebench_ifbench_instructions":git_blob_sha(checker_raw)},
        "actual":actual,
        "verified_deductions":[
            "EXACT_REFERENCE_TEXT_LITERAL_VISIBILITY_FAILS_ON_7_OF_12_PINNED_PUBLIC_RATIO_OVERLAP_ROWS",
            "WHITESPACE_NORMALIZATION_CANNOT_BE_ASSUMED_SCORE_PRESERVING_BECAUSE_CHECKER_APPLIES_CHARACTER_NGRAMS_TO_EXACT_REFERENCE_TEXT",
            "REPEAT_SPAN_SCORE_RELEVANT_WORD_SLICE_IS_RECOVERABLE_ON_4_OF_4_PINNED_PUBLIC_ROWS",
            "PINNED_PUBLIC_IFBENCH_OOD_POPULATION_HAS_ZERO_LEGACY_REPEAT_PROMPT_ROWS"
        ],
        "hard_nonclaims":[
            "NO_FROZEN_TERMINAL_LIVEBENCH_DATASET_EQUIVALENCE",
            "NO_LIVEBENCH_ACCEPTANCE_OR_EXECUTION_CREDIT",
            "NO_CLAIM_THAT_NGRAM_EXACT_REFERENCE_CANNOT_BE_RECOVERED_BY_ANOTHER_ADMISSIBLE_PUBLIC_ROUTE"
        ]
    }
    Path("livebench_public_parameter_truth_receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(receipt,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
