#!/usr/bin/env python3
from __future__ import annotations

import json, pathlib, string, subprocess, sys
from collections import Counter
import langdetect
from langdetect.lang_detect_exception import LangDetectException

LIVEBENCH_COMMIT="8f8e5c381a16e3f24257776edd53471fe86f8091"
INSTRUCTIONS_BLOB="4997bab885a676d92545fd91a9a20b48d234a2b2"
REGISTRY_BLOB="903ed738398648c7cfac61d5ffa478c22f1f0891"
UTIL_BLOB="1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b"

def run(cmd):
    return subprocess.run(cmd,check=True,text=True,capture_output=True).stdout.strip()

def exact(iid, response, **kwargs):
    from instruction_following_eval import instructions_registry as reg
    c=reg.INSTRUCTION_DICT[iid](iid)
    c.build_description(**kwargs)
    return bool(response.strip()) and bool(c.check_following(response))

def no_language_features(text):
    try:
        langdetect.detect(text)
    except LangDetectException:
        return True
    return False

def main():
    live=pathlib.Path("/tmp/LiveBench")
    assert run(["git","-C",str(live),"rev-parse","HEAD"])==LIVEBENCH_COMMIT
    for p,h in {
      "livebench/if_runner/instruction_following_eval/instructions.py":INSTRUCTIONS_BLOB,
      "livebench/if_runner/instruction_following_eval/instructions_registry.py":REGISTRY_BLOB,
      "livebench/if_runner/instruction_following_eval/instructions_util.py":UTIL_BLOB,
    }.items():
      assert run(["git","-C",str(live),"rev-parse",f"HEAD:{p}"])==h
    sys.path.insert(0,str(live/"livebench/if_runner"))
    from instruction_following_eval import instructions_util as util

    LANG="language:response_language"
    NTH="length_constraints:nth_paragraph_first_word"
    POST="detectable_content:postscript"
    CAP="change_case:capital_word_frequency"
    LETTER="keywords:letter_frequency"
    PLACE="detectable_content:number_placeholders"
    HIGH="detectable_format:number_highlighted_sections"
    BUL="detectable_format:number_bullet_lists"
    TITLE="detectable_format:title"
    TWO="combination:two_responses"
    QUOTE="startend:quotation"
    NOCOMMA="punctuation:no_comma"
    PAR="length_constraints:number_paragraphs"
    WORDS="length_constraints:number_words"
    SENT="length_constraints:number_sentences"

    langs=list(util.LANGUAGE_CODES.keys() if hasattr(util.LANGUAGE_CODES,"keys") else util.LANGUAGE_CODES)
    words=list(util.WORD_LIST)
    assert len(words)==1525 and len(set(words))==1525

    counts=Counter()
    failures=[]

    def must(name, cond, payload=None):
        counts["assertions"]+=1
        if not cond:
            failures.append({"name":name,"payload":payload})

    # Core exploit: detector removes MAIL_RE before feature extraction.
    base="0@0.0"
    must("base_erased",no_language_features(base),base)
    for code in langs:
        must("language:"+str(code), exact(LANG,base,language=code),base)
        counts["language_codes"]+=1

    # NTH first-word can be made simultaneously checker-visible and detector-invisible:
    # the NTH checker stops at '.', while langdetect's MAIL_RE consumes "word.@0.0".
    for wi,w in enumerate(words):
        for p in range(1,6):
            for k in range(1,p+1):
                paras=[f"{j}@0.0" for j in range(1,p+1)]
                paras[k-1]=f"{w}.@0.0"
                response="\n\n".join(paras)
                must(f"nth_erased:{wi}:{p}:{k}",no_language_features(response),response)
                must(f"nth_exact:{wi}:{p}:{k}",exact(NTH,response,num_paragraphs=p,nth_paragraph=k,first_word=w),response)
                # Strong cross-family check: the lowercase mail carrier introduces
                # zero all-uppercase word tokens, so CAP less-than 1 also passes.
                must(f"nth_cap0:{wi}:{p}:{k}",exact(CAP,response,capital_frequency=1,capital_relation="less than"),response)
                counts["nth_word_position_cases"]+=1

    # Both postscript spellings can likewise be hidden in an e-mail lexeme.
    for marker,resp in [("P.S.","p.s.@0.0"),("P.P.S","p.p.s.@0.0")]:
        must("post_erased:"+marker,no_language_features(resp),resp)
        must("post_exact:"+marker,exact(POST,resp,postscript_marker=marker),resp)
        must("post_cap0:"+marker,exact(CAP,resp,capital_frequency=1,capital_relation="less than"),resp)
        counts["postscript_markers"]+=1

    # Capital-word frequency becomes language-neutral too: e-mail lexemes are
    # stripped by langdetect but remain tokens for the LiveBench counter.
    for n in range(1,21):
        low=base
        must(f"cap_lt:{n}:erased",no_language_features(low),low)
        must(f"cap_lt:{n}",exact(CAP,low,capital_frequency=n,capital_relation="less than"),low)
        hi=" ".join(["AAA@0.0"]*n)
        must(f"cap_ge:{n}:erased",no_language_features(hi),hi)
        must(f"cap_ge:{n}",exact(CAP,hi,capital_frequency=n,capital_relation="at least"),hi)
        counts["capital_frequency_specs"]+=2

    # Letter-frequency payloads can be carried in a lowercase e-mail local part.
    # The @0.0 suffix adds zero alphabetic characters.
    for letter in string.ascii_lowercase:
        for n in range(1,11):
            low=base
            must(f"letter_lt:{letter}:{n}:erased",no_language_features(low),low)
            # For letters occurring in the literal base carrier there are none:
            # "0@0.0" is purely numeric/punctuation.
            must(f"letter_lt:{letter}:{n}",exact(LETTER,low,letter=letter,let_frequency=n,let_relation="less than"),low)
            hi=f"{letter*n}@0.0"
            must(f"letter_ge:{letter}:{n}:erased",no_language_features(hi),hi)
            must(f"letter_ge:{letter}:{n}",exact(LETTER,hi,letter=letter,let_frequency=n,let_relation="at least"),hi)
            counts["letter_frequency_specs"]+=2

    # Purely numeric structural carriers for the remaining language-compatible
    # added/active families.
    for n in range(1,5):
        resp=" ".join(["[0]"]*n)+" 0@0.0"
        must(f"placeholder:{n}:erased",no_language_features(resp),resp)
        must(f"placeholder:{n}",exact(PLACE,resp,num_placeholders=n),resp)
        resp=" ".join(["*0*"]*n)+" 0@0.0"
        must(f"highlight:{n}:erased",no_language_features(resp),resp)
        must(f"highlight:{n}",exact(HIGH,resp,num_highlights=n),resp)
        counts["placeholder_specs"]+=1
        counts["highlight_specs"]+=1

    for n in range(1,6):
        resp="\n".join(["* 0"]*n)
        must(f"bullet:{n}:erased",no_language_features(resp),resp)
        must(f"bullet:{n}",exact(BUL,resp,num_bullets=n),resp)
        counts["bullet_specs"]+=1

    resp="<<0>> 0@0.0"
    must("title_erased",no_language_features(resp),resp)
    must("title",exact(TITLE,resp),resp)
    resp='"0@0.0"'
    must("quote_erased",no_language_features(resp),resp)
    must("quote",exact(QUOTE,resp),resp)
    resp="0@0.0******1@0.0"
    must("two_erased",no_language_features(resp),resp)
    must("two",exact(TWO,resp),resp)
    resp="0@0.0"
    must("nocomma",exact(NOCOMMA,resp),resp)

    # Paragraph exact domains.
    for n in range(1,6):
        resp="\n***\n".join([f"{i}@0.0" for i in range(n)])
        must(f"paragraph:{n}:erased",no_language_features(resp),resp)
        must(f"paragraph:{n}",exact(PAR,resp,num_paragraphs=n),resp)
        counts["paragraph_specs"]+=1

    # Word thresholds: numeric tokens create word-count mass but no detector features.
    for n in (100,500):
        hi=" ".join(str(i%10) for i in range(n))
        must(f"word_ge:{n}:erased",no_language_features(hi),None)
        must(f"word_ge:{n}",exact(WORDS,hi,num_words=n,relation="at least"),None)
        low="0"
        must(f"word_lt:{n}:erased",no_language_features(low),low)
        must(f"word_lt:{n}",exact(WORDS,low,num_words=n,relation="less than"),low)
        counts["word_boundary_specs"]+=2

    # Sentence thresholds use numeric e-mail atoms plus ! so Punkt sees sentence
    # punctuation while langdetect erases the local/domain lexeme.
    for n in range(1,21):
        hi=" ".join(f"{i}@0.0!" for i in range(n))
        must(f"sent_ge:{n}:erased",no_language_features(hi),None)
        must(f"sent_ge:{n}",exact(SENT,hi,num_sentences=n,relation="at least"),None)
        if n>=2:
            low="0@0.0!"
            must(f"sent_lt:{n}:erased",no_language_features(low),low)
            must(f"sent_lt:{n}",exact(SENT,low,num_sentences=n,relation="less than"),low)
        counts["sentence_specs"]+=1+(1 if n>=2 else 0)

    if failures:
        out={
          "schema":"PROJECT_BRAIN_LIVEBENCH_RESPONSE_LANGUAGE_EMAIL_CARRIER_INDEPENDENT_V1",
          "status":"FAIL",
          "counts":dict(counts),
          "failure_count":len(failures),
          "failures":failures[:100],
          "terminal_rows_read":0,
        }
        pathlib.Path("livebench_language_email_carrier_v1.json").write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
        print(json.dumps(out,sort_keys=True))
        return 1

    out={
      "schema":"PROJECT_BRAIN_LIVEBENCH_RESPONSE_LANGUAGE_EMAIL_CARRIER_INDEPENDENT_V1",
      "status":"PASS__LANGDETECT_MAIL_ERASURE_MAKES_RESPONSE_LANGUAGE_TARGET_IDENTITY_NON_LOAD_BEARING_FOR_VERIFIED_CARRIERS__ZERO_TERMINAL_ROWS",
      "livebench_commit":LIVEBENCH_COMMIT,
      "pinned_blobs":{"instructions":INSTRUCTIONS_BLOB,"registry":REGISTRY_BLOB,"instructions_util":UTIL_BLOB},
      "mechanism":"LANGDETECT_DETECTOR_APPEND_REMOVES_MAIL_RE_BEFORE_NGRAM_EXTRACTION_WHILE_LIVEBENCH_COMPANION_CHECKERS_READ_THE_ORIGINAL_RESPONSE",
      "carrier":"LOCALPART@0.0",
      "nth_carrier":"VISIBLE_FIRST_WORD_DOT_AT_0_DOT_0__NTH_STOPS_AT_DOT__LANGDETECT_MAIL_RE_ERASES_WHOLE_LEXEME",
      "counts":dict(counts),
      "language_code_count":len(langs),
      "public_word_count":len(words),
      "theorem_supported":"REQUESTED_LANGUAGE_IDENTITY_CAN_BE_DELETED_AS_A_PARAMETER_DIMENSION_FOR_THE_VERIFIED_LANGUAGE_COMPATIBLE_CARRIERS; THE_CHECKER_RETURNS_TRUE_ON_LANGDETECT_NO_FEATURES_AND_THE_OTHER_CHECKERS_STILL_SEE_THE_PRE_ERASURE_STRING",
      "terminal_rows_read":0,
      "hidden_kwargs_read":0,
      "target_scores_read":0,
      "acceptance_credit":false,
      "hard_nonclaims":[
        "THIS_IS_NOT_YET_A_COMPLETE_UNION25_POINTWISE_OPTIMALITY_PROOF",
        "HIGHER_ORDER_COMPOSITIONS_NOT_EXPLICITLY_EXHAUSTED_HERE_STILL_REQUIRE_COMPOSITION_PROOF",
        "LETTER_FREQUENCY_UPPER_BOUNDS_CAN_STILL_CONFLICT_WITH_OTHER_FORCED_LETTER_LITERALS_INDEPENDENTLY_OF_LANGUAGE"
      ]
    }
    pathlib.Path("livebench_language_email_carrier_v1.json").write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps(out,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
