#!/usr/bin/env python3
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping, Sequence

ANSWER_PREFIX="Answer:"

@dataclass(frozen=True)
class StrictHLEVerdict:
    correct: bool
    extracted_answer: str|None
    reason: str

def extract_declared_answer(response:str):
    if not isinstance(response,str):
        return None,"RESPONSE_NOT_STRING"
    hits=[]
    for raw in response.replace("\r\n","\n").replace("\r","\n").split("\n"):
        line=raw.strip()
        if line.startswith(ANSWER_PREFIX):
            hits.append(line[len(ANSWER_PREFIX):].strip())
    if len(hits)!=1:
        return None,"ANSWER_LINE_COUNT_"+str(len(hits))
    if not hits[0]:
        return None,"ANSWER_EMPTY"
    return hits[0],"OK"

def strict_reference_verdict(response:str,correct_answer:str)->StrictHLEVerdict:
    if not isinstance(correct_answer,str):
        return StrictHLEVerdict(False,None,"REFERENCE_NOT_STRING")
    answer,reason=extract_declared_answer(response)
    if answer is None:
        return StrictHLEVerdict(False,None,reason)
    reference=correct_answer.strip()
    if not reference:
        return StrictHLEVerdict(False,answer,"REFERENCE_EMPTY")
    if answer==reference:
        return StrictHLEVerdict(True,answer,"EXACT_REFERENCE_MATCH")
    return StrictHLEVerdict(False,answer,"NOT_EXACT_REFERENCE_MATCH")

def score_predictions(prediction_by_id:Mapping[str,str],references:Sequence[Mapping[str,str]])->dict:
    total=len(references);correct=0;rows=[];seen=set()
    for ref in references:
        qid=ref.get("id");ans=ref.get("answer")
        if not isinstance(qid,str) or not qid or qid in seen:
            raise ValueError("REFERENCE_IDS_MUST_BE_UNIQUE_NONEMPTY_STRINGS")
        seen.add(qid)
        response=prediction_by_id.get(qid)
        verdict=StrictHLEVerdict(False,None,"MISSING_PREDICTION") if response is None else strict_reference_verdict(response,ans)
        correct+=int(verdict.correct)
        rows.append({"id":qid,"correct":verdict.correct,"reason":verdict.reason,"extracted_answer":verdict.extracted_answer})
    return {"correct":correct,"total":total,"accuracy_percent":(100.0*correct/total) if total else 0.0,
            "rows":rows,"official_score_equivalence_claimed":False,
            "scorer_role":"STRICT_OBJECTIVE_LOWER_BOUND_ON_REFERENCE_EXACTNESS"}

def self_test():
    assert strict_reference_verdict("Answer: Paris","Paris").correct
    assert not strict_reference_verdict("Answer: 0.5","1/2").correct
    assert not strict_reference_verdict("Answer: A\nAnswer: B","A").correct
    r=score_predictions({"q1":"Answer: A"},{"id":"bad"} if False else [{"id":"q1","answer":"A"},{"id":"q2","answer":"B"}])
    assert r["correct"]==1 and r["total"]==2 and r["official_score_equivalence_claimed"] is False

if __name__=="__main__":
    self_test();print("SELF_TEST_PASS")
