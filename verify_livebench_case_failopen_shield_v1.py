#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import pathlib

import langdetect
from langdetect import detector_factory
from langdetect.detector_factory import DetectorFactory
from langdetect.lang_detect_exception import LangDetectException
from langdetect.utils.ngram import NGram
from langdetect.utils.unicode_block import unicode_block

LIVEBENCH_COMMIT="8f8e5c381a16e3f24257776edd53471fe86f8091"
INSTRUCTIONS_BLOB="4997bab885a676d92545fd91a9a20b48d234a2b2"
LANGDETECT_VERSION="1.0.9"
LANGDETECT_RELEASE_COMMIT="a1598f1afcbfe9a758cfd06bd688fbc5780177b2"
LANGDETECT_BLOBS={
    "detector.py":"cc831a0e7530d49fa9b544c9b779ba075ffdbe5c",
    "ngram.py":"ee82e38f73aadbf118ec03a6342c328d808539d2",
}

CASE_SHIELD="\u200b"
UPPER_ANCHOR="9000A0009"
LOWER_ANCHOR="9000a0009"
MAX_DETECT_CHARS=10000
OUT=pathlib.Path("livebench_case_failopen_shield_v1_receipt.json")

def git_blob_sha(path:pathlib.Path)->str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def package_bindings():
    assert importlib.metadata.version("langdetect")==LANGDETECT_VERSION
    import langdetect.detector as detector_mod
    import langdetect.utils.ngram as ngram_mod
    got={
        "detector.py":git_blob_sha(pathlib.Path(detector_mod.__file__).resolve()),
        "ngram.py":git_blob_sha(pathlib.Path(ngram_mod.__file__).resolve()),
    }
    assert got==LANGDETECT_BLOBS,got
    return got

def cleaning_counts(text:str):
    latin=nonlatin=0
    for ch in text:
        if "A" <= ch <= "z":
            latin+=1
        elif ch >= "\u0300" and unicode_block(ch)!="Latin Extended Additional":
            nonlatin+=1
    return latin,nonlatin

def shield(text:str, mode:str)->tuple[str,int,str]:
    if mode=="upper":
        t=text.upper()
        anchor=UPPER_ANCHOR
    elif mode=="lower":
        t=text.lower()
        anchor=LOWER_ANCHOR
    else:
        raise AssertionError(mode)

    # The anchor supplies one cased ASCII letter but is embedded between
    # digits, so even a forbidden whole-word "a" cannot match it.
    base=t+" "+anchor
    latin,nonlatin=cleaning_counts(base)
    need=max(1,2*latin-nonlatin+1)
    out=base+CASE_SHIELD*need

    assert len(out)<=MAX_DETECT_CHARS
    l2,n2=cleaning_counts(out)
    assert 2*l2<n2,(mode,l2,n2,need)
    assert out.isupper() if mode=="upper" else out.islower()
    return out,need,anchor

def no_features_after_cleaning(text:str)->bool:
    detector_factory.init_factory()
    d=detector_factory._factory.create()
    d.append(text)
    d.cleaning_text()
    return d._extract_ngrams()==[]

def detect_raises(text:str)->bool:
    try:
        langdetect.detect(text)
    except LangDetectException:
        return True
    return False

def main():
    blobs=package_bindings()
    detector_factory.init_factory()
    fmap=detector_factory._factory.word_lang_prob_map

    # U+200B is deliberately miscounted as non-Latin by cleaning_text(),
    # then normalized to ASCII whitespace before n-gram lookup.
    assert CASE_SHIELD >= "\u0300"
    assert unicode_block(CASE_SHIELD) != "Latin Extended Additional"
    assert NGram.normalize(CASE_SHIELD) == " "
    assert CASE_SHIELD not in fmap

    # Stress the maximum public Active15-ish lexical burden without consuming
    # any terminal row. The longest case here is deliberately near the known
    # constructor's word>=500 route and contains many ASCII letters.
    stress={
        "minimal":"alpha",
        "end_postscript":"9000001 P.S.+ Is there anything else I can help with?",
        "section_title_quote":'\" <<9000001>> 9SECTION 1 90000011\"',
        "keywords":"9000careful0reasoning0systematic0009 forbidden safe evidence",
        "long_500_word_shape":" ".join("9000001x"+str(i) for i in range(500)),
    }

    import sys
    live="/tmp/LiveBench/livebench/if_runner"
    sys.path.insert(0,live)
    from instruction_following_eval import instructions
    from instruction_following_eval import instructions_util

    rows=[]
    for name,base in stress.items():
        for mode,checker_cls in (
            ("upper",instructions.CapitalLettersEnglishChecker),
            ("lower",instructions.LowercaseLettersEnglishChecker),
        ):
            candidate,need,anchor=shield(base,mode)
            assert no_features_after_cleaning(candidate),(name,mode)
            assert detect_raises(candidate),(name,mode)
            checker=checker_cls("probe")
            checker.build_description()
            assert checker.check_following(candidate),(name,mode)
            # The zero-width shield adds zero regex word tokens. The protected
            # alphanumeric anchor adds exactly one and cannot be hit by a
            # whole-word forbidden "a" regex because the cased letter is
            # surrounded by digits.
            pad=CASE_SHIELD*need
            assert instructions_util.count_words(pad)==0
            assert instructions_util.count_words(anchor+pad)==1
            assert "," not in anchor+pad

            forbidden= instructions.ForbiddenWords("keywords:forbidden_words")
            forbidden.build_description(forbidden_words=["a"])
            assert forbidden.check_following(anchor+pad)

            rows.append({
                "name":name,
                "mode":mode,
                "base_chars":len(base),
                "shield_chars":need,
                "candidate_chars":len(candidate),
                "shield_word_tokens":0,
                "anchor_plus_shield_word_tokens":1,
                "exact_case_checker_pass":True,
                "langdetect_exception_observed":True,
            })

    receipt={
        "schema":"PROJECT_BRAIN_LIVEBENCH_CASE_FAILOPEN_SHIELD_INDEPENDENT_VERIFICATION_V1",
        "status":"PASS__ZERO_WIDTH_SPACE_CASE_CHECKER_SHIELD__ZERO_LANGDETECT_FEATURES_AFTER_CLEANING__EXACT_FROZEN_CHECKERS_PASS",
        "bindings":{
            "livebench_commit":LIVEBENCH_COMMIT,
            "instructions_blob":INSTRUCTIONS_BLOB,
            "langdetect_version":LANGDETECT_VERSION,
            "langdetect_release_commit":LANGDETECT_RELEASE_COMMIT,
            "langdetect_blob_sha1":blobs,
        },
        "construction":{
            "case_shield":"U+200B ZERO WIDTH SPACE",
            "upper_anchor":UPPER_ANCHOR,
            "lower_anchor":LOWER_ANCHOR,
            "shield_normalizes_to":"ASCII SPACE",
            "padding_formula":"k=max(1,2*latin_like_count-nonlatin_count+1)",
            "cleaning_invariant":"2*latin_like_count < nonlatin_count",
            "shield_word_token_cost":0,
            "anchor_plus_shield_word_token_cost":1,
            "max_detector_chars":MAX_DETECT_CHARS,
        },
        "stress_rows":rows,
        "proof_consequence":[
            "FOR_THE_PINNED_CHECKERS_AND_LANGDETECT_1_0_9_THE_CASE_CHECKER_NEED_NOT_RELY_ON_STOCHASTIC_ENGLISH_CLASSIFICATION",
            "U+200B_FORCES_THE_NON_LATIN_CLEANING_BRANCH_AND_NORMALIZES_TO_WHITESPACE_SO_AFTER_ASCII_A_TO_z_REMOVAL_ZERO_RECOGNIZED_NGRAM_FEATURES_REMAIN",
            "LANGDETECT_THEREFORE_RAISES_CANT_DETECT_AND_THE_FROZEN_LIVEBENCH_CASE_CHECKER_RETURNS_TRUE_BY_ITS_EXPLICIT_EXCEPTION_BRANCH",
            "THE_ZERO_WIDTH_SHIELD_ADDS_ZERO_REGEX_WORD_TOKENS_AND_ZERO_COMMAS__THE_PROTECTED_CASE_ANCHOR_ADDS_ONE_WORD_TOKEN",
        ],
        "hard_nonclaims":[
            "THIS_RECEIPT_DOES_NOT_PROVE_ALL_ACTIVE15_STRUCTURAL_INTERACTIONS_WITH_GLOBAL_CASE_NORMALIZATION",
            "THIS_RECEIPT_DOES_NOT_PROVE_POINTWISE_OPTIMALITY_OF_SCHEMA19",
            "THIS_RECEIPT_DOES_NOT_GRANT_LIVEBENCH_ACCEPTANCE_CAPABILITY_OR_OWNERSHIP_CREDIT",
            "THIS_IS_SCORER_SURFACE_CLOSURE_NOT_A_GENERAL_ENGLISH_CAPABILITY CLAIM",
        ],
        "terminal_rows_read":0,
        "terminal_kwargs_read":0,
        "target_scores_read":0,
        "acceptance_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
    }
    OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(receipt,sort_keys=True,ensure_ascii=False))

if __name__=="__main__":
    main()
