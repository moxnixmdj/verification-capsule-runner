#!/usr/bin/env python3
from __future__ import annotations

import importlib.metadata
import json
import pathlib
import sys

import langdetect
from langdetect import detector_factory
from langdetect.lang_detect_exception import LangDetectException
from langdetect.utils.ngram import NGram
from langdetect.utils.unicode_block import unicode_block

LIVEBENCH_COMMIT="8f8e5c381a16e3f24257776edd53471fe86f8091"
INSTRUCTIONS_BLOB="4997bab885a676d92545fd91a9a20b48d234a2b2"
LANGDETECT_VERSION="1.0.9"
CASE_SHIELD="\u200b"
OUT=pathlib.Path("livebench_case_failopen_shield_v1_receipt.json")


def cleaning_counts(text:str)->tuple[int,int]:
    latin=nonlatin=0
    for ch in text:
        if "A" <= ch <= "z":
            latin+=1
        elif ch >= "\u0300" and unicode_block(ch)!="Latin Extended Additional":
            nonlatin+=1
    return latin,nonlatin


def force_detector_exception(anchor:str)->str:
    latin,nonlatin=cleaning_counts(anchor)
    k=max(1,2*latin-nonlatin+1)
    candidate=anchor+CASE_SHIELD*k
    l2,n2=cleaning_counts(candidate)
    assert 2*l2<n2
    return candidate


def detector_really_raises(text:str)->bool:
    try:
        langdetect.detect(text)
    except LangDetectException:
        return True
    return False


def main()->None:
    assert importlib.metadata.version("langdetect")==LANGDETECT_VERSION
    assert NGram.normalize(CASE_SHIELD)==" "
    assert CASE_SHIELD >= "\u0300"
    assert unicode_block(CASE_SHIELD)!="Latin Extended Additional"

    detector_factory.init_factory()
    assert CASE_SHIELD not in detector_factory._factory.word_lang_prob_map

    live="/tmp/LiveBench/livebench/if_runner"
    sys.path.insert(0,live)
    from instruction_following_eval import instructions

    # Frozen instructions.py comments out the logging import while both case
    # checker exception handlers still call logging.error(...).
    assert "logging" not in instructions.__dict__

    rows=[]
    for mode,anchor,checker_cls in (
        ("upper","A",instructions.CapitalLettersEnglishChecker),
        ("lower","a",instructions.LowercaseLettersEnglishChecker),
    ):
        candidate=force_detector_exception(anchor)
        assert detector_really_raises(candidate)
        checker=checker_cls("probe")
        checker.build_description()

        observed=None
        try:
            checker.check_following(candidate)
        except Exception as exc:
            observed={"type":type(exc).__name__,"message":str(exc)}
        assert observed is not None
        assert observed["type"]=="NameError",observed
        assert "logging" in observed["message"].lower(),observed

        rows.append({
            "mode":mode,
            "candidate_repr":repr(candidate),
            "langdetect_exception_forced":True,
            "exact_checker_result":"RAISES_NameError_NOT_PASS",
            "observed_exception":observed,
        })

    receipt={
        "schema":"PROJECT_BRAIN_LIVEBENCH_CASE_FAILOPEN_NEGATIVE_PROOF_V1",
        "status":"PASS__PROPOSED_LANGDETECT_EXCEPTION_SHIELD_IS_INVALID__FROZEN_CASE_CHECKERS_RAISE_NAMEERROR",
        "bindings":{
            "livebench_commit":LIVEBENCH_COMMIT,
            "instructions_blob":INSTRUCTIONS_BLOB,
            "langdetect_version":LANGDETECT_VERSION,
        },
        "rows":rows,
        "consequence":[
            "DO_NOT_USE_LANGDETECT_EXCEPTION_AS_A_SUCCESS_PATH_FOR_FROZEN_LIVEBENCH_CASE_CHECKERS",
            "THE_COMMENTED_OUT_LOGGING_IMPORT_TURNS_THE_HANDLER_INTO_A_NAMEERROR_PATH",
            "CASE_CONSTRUCTION_MUST_KEEP_LANGDETECT_ON_ITS_NORMAL_RETURN_PATH",
        ],
        "hard_nonclaims":[
            "THIS_NEGATIVE_PROOF_DOES_NOT_INVALIDATE_NORMAL_ENGLISH_CARRIERS",
            "THIS_DOES_NOT_GRANT_LIVEBENCH_ACCEPTANCE_CAPABILITY_OR_OWNERSHIP_CREDIT",
        ],
        "terminal_rows_read":0,
        "terminal_kwargs_read":0,
        "target_scores_read":0,
        "acceptance_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
    }
    OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(receipt,sort_keys=True))


if __name__=="__main__":
    main()
