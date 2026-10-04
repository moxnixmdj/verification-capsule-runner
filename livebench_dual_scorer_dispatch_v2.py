from __future__ import annotations
import re
from typing import Any, Mapping

CUTOFF="2025-11-25"
THINK_RE=re.compile(r"<think>.*?<\/think>", re.DOTALL)
SOLUTION_RE=re.compile(r"<solution>(.*?)<\/solution>", re.DOTALL)

def scorer_family(question: Mapping[str,Any])->str:
    if question.get("category")!="instruction_following":
        raise ValueError("CATEGORY_NOT_INSTRUCTION_FOLLOWING")
    release=str(question.get("livebench_release_date") or "")[:10]
    if not release:
        raise ValueError("RELEASE_DATE_REQUIRED")
    return "LEGACY_IFEVAL" if release < CUTOFF else "IFBENCH"

def strip_think(answer: str)->str:
    return THINK_RE.sub("",str(answer or "")).strip()

def modern_response(answer: str)->str:
    clean=strip_think(answer)
    m=SOLUTION_RE.search(clean)
    return m.group(1).strip() if m else clean.strip()

def score_case(question: Mapping[str,Any], answer: str, *, legacy_eval, current_eval, score_results)->dict[str,Any]:
    family=scorer_family(question)
    try:
        if family=="LEGACY_IFEVAL":
            response=strip_think(answer)
            prompt=question["turns"][0]
            kwargs=[{k:v for k,v in dict(d or {}).items() if v is not None} for d in question["kwargs"]]
            inp=legacy_eval.InputExample(
                key=question.get("question_id",question.get("key")),
                instruction_id_list=list(question["instruction_id_list"]),
                prompt=prompt,
                kwargs=kwargs,
            )
            out=legacy_eval.test_instruction_following_strict(inp,{prompt:response})
        else:
            response=modern_response(answer)
            inp=current_eval.InputExample(
                key=question.get("key",question.get("question_id")),
                instruction_id_list=list(question["instruction_id_list"]),
                prompt=question["turns"][0],
                kwargs=[dict(x or {}) for x in question["kwargs"]],
            )
            out=current_eval.test_instruction_following_strict(inp,response)
        n=len(out.follow_instruction_list)
        followed=sum(1 for x in out.follow_instruction_list if x)
        score=float(score_results(out.follow_all_instructions,out.follow_instruction_list))
        return {
            "score":score,
            "follow_all":bool(out.follow_all_instructions),
            "instruction_count":n,
            "instructions_followed":followed,
            "scorer_family":family,
            "scoring_error":None,
        }
    except Exception as exc:
        return {
            "score":0.0,
            "follow_all":False,
            "instruction_count":len(question.get("instruction_id_list") or []),
            "instructions_followed":0,
            "scorer_family":family,
            "scoring_error":type(exc).__name__+":"+str(exc)[:300],
        }
