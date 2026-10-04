#!/usr/bin/env python3
import json, pathlib, re, subprocess, sys

LIVE="8f8e5c381a16e3f24257776edd53471fe86f8091"
PUA="\ue000"

def sh(*a):
    return subprocess.run(a,check=True,text=True,capture_output=True).stdout.strip()

root=pathlib.Path("/tmp/LiveBench")
assert sh("git","-C",str(root),"rev-parse","HEAD")==LIVE
sys.path.insert(0,str(root/"livebench/if_runner"))

import langdetect
from langdetect.lang_detect_exception import LangDetectException
from instruction_following_eval import instructions_registry, instructions_util

assert re.match(r"\w",PUA) is None and not PUA.isalpha()
assert not PUA.isupper() and not PUA.islower()
assert instructions_util.count_words(PUA*64)==0

def carrier(payload):
    out=candidate.inject_before_suffix(payload)
    assert out.startswith(payload)
    return out

direct=0
for n in (0,1,10,100,500,1000,2500,3000):
    t=carrier("a"*n+" 9000001? [0] *0*")
    try:
        langdetect.detect(t)
    except LangDetectException:
        direct+=1
    else:
        raise AssertionError(("unexpected detectable text",n))

sample=carrier("English looking sample 9000001? [0] *0*")
codes=tuple(instructions_util.LANGUAGE_CODES)
for code in codes:
    c=instructions_registry.INSTRUCTION_DICT["language:response_language"]("language:response_language")
    c.build_description(language=code)
    assert c.check_following(sample) is True

up=instructions_registry.INSTRUCTION_DICT["change_case:english_capital"]("change_case:english_capital")
up.build_description()
u=carrier("ALPHA BETA")
assert u.isupper() and up.check_following(u) is True

lo=instructions_registry.INSTRUCTION_DICT["change_case:english_lowercase"]("change_case:english_lowercase")
lo.build_description()
l=carrier("alpha beta")
assert l.islower() and lo.check_following(l) is True

receipt={
 "schema":"PROJECT_BRAIN_LIVEBENCH_UNION25_LANGUAGE_CARRIER_V1",
 "status":"PASS__CONTENT_BOUND_CANDIDATE__EXACT_RUNTIME_LANGUAGE_EXCEPTION_CARRIER",
 "candidate_blob":SUBJECT_BLOB,
 "direct_exception_cases":direct,
 "language_targets":len(codes),
 "language_targets_passed":len(codes),
 "word_count_delta":instructions_util.count_words(PUA*64),
 "terminal_rows_read":0,
 "acceptance_credit_delta":0,
 "nonclaim":"COMPOSITION_AND_UNION25_POINTWISE_OPTIMALITY_REMAIN_UNPROVED"
}
pathlib.Path("livebench_union25_language_carrier_v1.json").write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
print(json.dumps(receipt,sort_keys=True))
