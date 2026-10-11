#!/usr/bin/env python3
from __future__ import annotations
import argparse, concurrent.futures, hashlib, json, re, time, unicodedata, urllib.parse, urllib.request
from pathlib import Path
from typing import Any

DATASET="ai-safety-institute/trivia_qa_verified"
CONFIG="default"
SPLIT="validation"
OFFSET=25
N=25
EXPECTED_TOTAL=3381
UA="ProjectBrain-HLE-ExactRetrievalV2-ConsumedDiagnostic/1.0"
SCHEMA="PROJECT_BRAIN_HLE_EXACT_RETRIEVAL_V2_CONSUMED_PUBLIC_DIAGNOSTIC_V1"

def canon_obj(x:Any)->bytes:
    return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()

def sha_obj(x:Any)->str:
    return hashlib.sha256(canon_obj(x)).hexdigest()

def fetch_rows()->list[dict[str,Any]]:
    q=urllib.parse.urlencode({"dataset":DATASET,"config":CONFIG,"split":SPLIT,"offset":OFFSET,"length":N})
    url="https://datasets-server.huggingface.co/rows?"+q
    last=None
    for attempt in range(4):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":UA})
            with urllib.request.urlopen(req,timeout=30) as r:
                obj=json.loads(r.read().decode())
            if int(obj.get("num_rows_total") or -1)!=EXPECTED_TOTAL:
                raise RuntimeError("TOTAL_ROWS_MISMATCH")
            rows=obj.get("rows")
            if not isinstance(rows,list) or len(rows)!=N:
                raise RuntimeError("ROW_COUNT_MISMATCH")
            out=[]
            for j,item in enumerate(rows):
                idx=OFFSET+j
                if int(item.get("row_idx",-1))!=idx:
                    raise RuntimeError("ORDER_MISMATCH")
                row=item.get("row") or {}
                question=row.get("question"); answer=row.get("answer")
                if not isinstance(question,str) or not question.strip() or not isinstance(answer,str) or not answer.strip():
                    raise RuntimeError("ROW_INVALID")
                out.append({"row_idx":idx,"question":question,"answer":answer})
            return out
        except Exception as e:
            last=e
            if attempt==3: raise
            time.sleep(2**attempt)
    raise RuntimeError(type(last).__name__ if last else "FETCH_FAILED")

def prepare(path:Path)->None:
    rows=fetch_rows()
    questions=[{"row_idx":r["row_idx"],"task_id":f"triviaqa_validation_row_{r['row_idx']}",
                "question":r["question"],"question_sha256":hashlib.sha256(r["question"].encode()).hexdigest()} for r in rows]
    doc={"schema":SCHEMA,"phase":"QUESTIONS_ONLY_PREPARED","dataset":DATASET,"split":SPLIT,
         "slice":"ROWS_25_TO_49_ALREADY_CONSUMED_DIAGNOSTIC_FOR_EXACT_RETRIEVAL_V2","rows":N,
         "questions_manifest_sha256":sha_obj(questions),"questions":questions,"gold_written":False}
    path.write_text(json.dumps(doc,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print(json.dumps({k:v for k,v in doc.items() if k!="questions"},sort_keys=True))

def solve_one(item:dict[str,Any])->dict[str,Any]:
    from canonical.runtime.hle_exact_retrieval_extract_v2 import propose
    out=propose(task_id=item["task_id"],question=item["question"],has_nonempty_image_payload=False)
    ans=out.get("candidate_answer")
    ans=ans if isinstance(ans,str) else ""
    if any(int(out.get(k,0) or 0) for k in ("external_model_calls","external_reasoning_model_calls","model_dependency_count")):
        raise RuntimeError("EXTERNAL_COGNITION")
    if out.get("gold_accessed") is not False:
        raise RuntimeError("GOLD_ACCOUNTING")
    return {
        "row_idx":item["row_idx"],"task_id":item["task_id"],"question_sha256":item["question_sha256"],
        "candidate_answer":ans,"candidate_answer_sha256":hashlib.sha256(ans.encode()).hexdigest(),
        "attempted":bool(ans.strip()),"status":out.get("status"),
        "question_kind":out.get("question_kind"),
        "fallback_general_form":out.get("fallback_general_form"),
        "candidate_score":out.get("candidate_score"),
        "runner_up_margin":out.get("runner_up_margin"),
        "independent_support_host_count":out.get("independent_support_host_count",0),
        "external_model_calls":0,"external_reasoning_model_calls":0,"model_dependency_count":0,"gold_accessed":False,
    }

def solve(qpath:Path,cpath:Path,workers:int)->None:
    doc=json.loads(qpath.read_text())
    qs=doc.get("questions")
    if not isinstance(qs,list) or len(qs)!=N or sha_obj(qs)!=doc.get("questions_manifest_sha256"):
        raise RuntimeError("QUESTIONS_INVALID")
    out=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futs={pool.submit(solve_one,x):x for x in qs}
        for f,x in futs.items():
            try: out.append(f.result())
            except Exception as e:
                out.append({"row_idx":x["row_idx"],"task_id":x["task_id"],"question_sha256":x["question_sha256"],
                            "candidate_answer":"","candidate_answer_sha256":hashlib.sha256(b"").hexdigest(),
                            "attempted":False,"status":"SOLVER_EXCEPTION:"+type(e).__name__,
                            "question_kind":None,"fallback_general_form":None,"candidate_score":None,
                            "runner_up_margin":None,"independent_support_host_count":0,
                            "external_model_calls":0,"external_reasoning_model_calls":0,
                            "model_dependency_count":0,"gold_accessed":False})
    out.sort(key=lambda x:x["row_idx"])
    sealed={"schema":SCHEMA,"phase":"COMMITMENTS_SEALED_BEFORE_GOLD_SCORE","commitment_count":len(out),
            "questions_manifest_sha256":doc["questions_manifest_sha256"],"commitments_manifest_sha256":sha_obj(out),
            "commitments":out,"gold_loaded_by_solver_process":False,
            "external_model_calls_total":0,"external_reasoning_model_calls_total":0,"model_dependency_count_total":0}
    cpath.write_text(json.dumps(sealed,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"phase":sealed["phase"],"attempted":sum(x["attempted"] for x in out),
                      "commitments_manifest_sha256":sealed["commitments_manifest_sha256"]},sort_keys=True))

_ARTICLE=re.compile(r"\b(a|an|the)\b",re.I)
def norm(v:str)->str:
    x=unicodedata.normalize("NFKD",str(v or "")).lower()
    x="".join(ch for ch in x if not unicodedata.category(ch).startswith("P"))
    return " ".join(_ARTICLE.sub(" ",x).split())

def score(qpath:Path,cpath:Path,spath:Path)->None:
    qdoc=json.loads(qpath.read_text()); sealed=json.loads(cpath.read_text())
    cs=sealed.get("commitments")
    if not isinstance(cs,list) or len(cs)!=N or sha_obj(cs)!=sealed.get("commitments_manifest_sha256"):
        raise RuntimeError("COMMITMENTS_INVALID")
    rows=fetch_rows(); by={r["row_idx"]:r for r in rows}; questions={x["row_idx"]:x for x in qdoc["questions"]}
    attempted=exact=0; per=[]
    for c in cs:
        idx=c["row_idx"]; candidate=c["candidate_answer"]; gold=by[idx]["answer"]
        hit=bool(candidate.strip()) and norm(candidate)==norm(gold)
        attempted+=int(bool(candidate.strip())); exact+=int(hit)
        per.append({"row_idx":idx,"question":by[idx]["question"],"gold":gold,"candidate":candidate,
                    "normalized_exact":hit,"status":c["status"],"question_kind":c["question_kind"],
                    "fallback_general_form":c["fallback_general_form"],
                    "candidate_score":c["candidate_score"],"runner_up_margin":c["runner_up_margin"],
                    "independent_support_host_count":c["independent_support_host_count"]})
    summary={"schema":SCHEMA,"dataset":DATASET,"split":SPLIT,"slice":"ROWS_25_TO_49_ALREADY_CONSUMED_DIAGNOSTIC_FOR_EXACT_RETRIEVAL_V2",
             "sample_size":N,"attempted":attempted,"attempt_rate":attempted/N,"normalized_exact":exact,
             "normalized_exact_rate":exact/N,"diagnostic_gate":{"min_attempt_rate":0.25,"min_exact_rate":0.20,
             "passed":attempted/N>=0.25 and exact/N>=0.20},"per_slot":per,
             "external_model_calls_total":0,"external_reasoning_model_calls_total":0,"model_dependency_count_total":0,
             "hle_questions_consumed":0,"hle_gold_consumed":0,"hle_score_credit":0}
    spath.write_text(json.dumps(summary,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print(json.dumps({k:v for k,v in summary.items() if k!="per_slot"},sort_keys=True))
    for row in per: print(json.dumps(row,ensure_ascii=False,sort_keys=True))

def main():
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest="cmd",required=True)
    a=sub.add_parser("prepare"); a.add_argument("--questions",type=Path,required=True)
    a=sub.add_parser("solve"); a.add_argument("--questions",type=Path,required=True); a.add_argument("--commitments",type=Path,required=True); a.add_argument("--workers",type=int,default=3)
    a=sub.add_parser("score"); a.add_argument("--questions",type=Path,required=True); a.add_argument("--commitments",type=Path,required=True); a.add_argument("--summary",type=Path,required=True)
    x=p.parse_args()
    if x.cmd=="prepare": prepare(x.questions)
    elif x.cmd=="solve": solve(x.questions,x.commitments,x.workers)
    else: score(x.questions,x.commitments,x.summary)
if __name__=="__main__": main()
