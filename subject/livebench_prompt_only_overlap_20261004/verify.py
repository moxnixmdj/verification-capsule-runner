#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import json
import re
import string
import sys
from pathlib import Path

SUBJECT = Path(__file__).with_name("subject.py")
IFBENCH = Path("/tmp/IFBench/data/IFBench_test.jsonl")
LIVEBENCH_ROOT = Path("/tmp/LiveBench")

def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("SPEC_LOAD_FAILED")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def trigrams(value: str) -> set[str]:
    value = str(value)
    return {value[i:i+3] for i in range(max(0, len(value)-2))}

def exact_overlap(response: str, reference: str) -> float:
    g = trigrams(response)
    assert g, "response has no trigrams"
    return 100.0 * len(g & trigrams(reference)) / len(g)

def exact_consonant_cluster(response: str) -> bool:
    words = response.lower().strip().split()
    letters = set(string.ascii_lowercase)
    consonants = set("bcdfghjklmnpqrstvwxyz")
    for word in words:
        if all(char not in letters for char in word):
            continue
        cluster = False
        for i in range(len(word)-1):
            if word[i] in consonants and word[i+1] in consonants:
                cluster = True
                break
        if not cluster:
            return False
    return True

def main() -> int:
    subject = load_module(SUBJECT, "subject")
    util = load_module(
        LIVEBENCH_ROOT / "livebench/if_runner/ifbench/instructions_util.py",
        "frozen_instructions_util",
    )
    rows=[json.loads(x) for x in IFBENCH.read_text(encoding="utf-8").splitlines() if x.strip()]
    checked=[]
    ratio_count=0
    exact_pass=0
    exact_equals_robust=0
    keyword_rows=0
    keyword_pass=0
    consonant_rows=0
    consonant_pass=0
    prompt_only_fields_ok=0

    for row in rows:
        ids=list(row.get("instruction_id_list") or [])
        if "ratio:overlap" not in ids:
            continue
        ratio_count += 1
        i=ids.index("ratio:overlap")
        kw=(row.get("kwargs") or [])[i]
        target=float(kw["percentage"])
        reference=str(kw["reference_text"])
        prompt=str(row["prompt"])

        # Construction receives only the visible prompt. Public kwargs are read
        # after construction exclusively by this independent falsification grader.
        out=subject.construct_from_prompt(prompt)
        response=str(out["response"])
        prompt_only_fields_ok += int(
            out.get("raw_reference_text_required") is False
            and out.get("hidden_kwargs_required") is False
            and out.get("whitespace_free_response") is True
        )
        actual=exact_overlap(response, reference)
        in_band=(target-2 <= actual <= target+2)
        exact_pass += int(in_band)
        equal=abs(actual-float(out["score_percent"])) < 1e-12
        exact_equals_robust += int(equal)

        aux={}
        if "sentence:keyword" in ids:
            keyword_rows += 1
            j=ids.index("sentence:keyword")
            akw=(row.get("kwargs") or [])[j]
            word=str(akw.get("word") or akw.get("keyword") or "")
            N=int(akw.get("N"))
            sentences=util.split_into_sentences(response)
            ok=len(sentences) >= N and word.lower() in sentences[N-1].lower()
            keyword_pass += int(ok)
            aux["sentence_keyword"]=ok
            assert ok, ("sentence:keyword fail", row.get("key"), N, word, sentences)

        if "words:consonants" in ids:
            consonant_rows += 1
            ok=exact_consonant_cluster(response)
            consonant_pass += int(ok)
            aux["words_consonants"]=ok
            assert ok, ("words:consonants fail", row.get("key"))

        checked.append({
            "key":row.get("key"),
            "instruction_ids":ids,
            "target":target,
            "actual_raw_reference_percent":actual,
            "candidate_robust_percent":float(out["score_percent"]),
            "overlap_pass":in_band,
            "robust_exact_equal":equal,
            "aux":aux,
        })
        assert in_band, ("overlap fail", row.get("key"), target, actual)
        assert equal, ("robust mismatch", row.get("key"), actual, out["score_percent"])

    assert ratio_count == 12, ratio_count
    assert exact_pass == 12, exact_pass
    assert exact_equals_robust == 12, exact_equals_robust
    assert prompt_only_fields_ok == 12, prompt_only_fields_ok
    assert keyword_rows == 4 and keyword_pass == 4, (keyword_rows, keyword_pass)
    assert consonant_rows == 3 and consonant_pass == 3, (consonant_rows, consonant_pass)

    receipt={
        "schema":"PROJECT_BRAIN_LIVEBENCH_PROMPT_ONLY_OVERLAP_INDEPENDENT_VERIFICATION_V1",
        "status":"PASS",
        "subject_git_blob_sha":"6c2ffb2752932e4aca3d6dae4a18b3f40e3d3d66",
        "pinned_public_sources":{
            "ifbench_commit":"1c40f0c10d9b5c5c2f10a175a28007ebb64f7f4d",
            "ifbench_test_git_blob_sha":"a8e343ed928d8b4e649b9dba651fed7757ccacc3",
            "livebench_commit":"8f8e5c381a16e3f24257776edd53471fe86f8091",
            "livebench_instructions_git_blob_sha":"02b2dfeb50f036b89bec3df34522c73f756d8f44",
            "livebench_instructions_util_git_blob_sha":"21b13c7fcfc2c2de01e80c9e7dd222b9bca81342",
        },
        "verified":{
            "public_ifbench_rows":len(rows),
            "ratio_overlap_rows":ratio_count,
            "prompt_only_construction_rows":prompt_only_fields_ok,
            "raw_reference_overlap_band_pass":exact_pass,
            "candidate_robust_score_exactly_equals_raw_reference_score":exact_equals_robust,
            "sentence_keyword_mixed_rows":keyword_rows,
            "sentence_keyword_exact_semantics_pass":keyword_pass,
            "consonant_cluster_mixed_rows":consonant_rows,
            "consonant_cluster_exact_semantics_pass":consonant_pass,
        },
        "hard_nonclaims":[
            "NO_UNEXPOSED_TERMINAL_LIVEBENCH_ROWS_READ",
            "NO_FROZEN_TERMINAL_GRAMMAR_EQUIVALENCE",
            "NO_LIVEBENCH_ACCEPTANCE_OR_EXECUTION_CREDIT",
        ],
        "rows":checked,
    }
    Path("livebench_prompt_only_overlap_receipt.json").write_text(
        json.dumps(receipt,indent=2,sort_keys=True,ensure_ascii=False)+"\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt,sort_keys=True,ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
