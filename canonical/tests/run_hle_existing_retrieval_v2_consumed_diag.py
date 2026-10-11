#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,re,time,unicodedata,urllib.parse,urllib.request
from pathlib import Path
from canonical.runtime.hle_exact_retrieval_extract_v2 import propose

DATASET="ai-safety-institute/trivia_qa_verified";CONFIG="default";SPLIT="validation"
OFFSET=25;N=25;EXPECTED_TOTAL=3381
_ARTICLE=re.compile(r"\b(a|an|the)\b",re.I)

def fetch_rows():
    q=urllib.parse.urlencode({"dataset":DATASET,"config":CONFIG,"split":SPLIT,"offset":OFFSET,"length":N})
    req=urllib.request.Request("https://datasets-server.huggingface.co/rows?"+q,headers={"User-Agent":"ProjectBrain-RetrievalV2-Diagnostic/1.0"})
    with urllib.request.urlopen(req,timeout=30) as r: obj=json.loads(r.read().decode())
    assert obj["num_rows_total"]==EXPECTED_TOTAL and len(obj["rows"])==N
    return [{"idx":x["row_idx"],"q":x["row"]["question"],"a":x["row"]["answer"]} for x in obj["rows"]]

def norm(v):
    x=unicodedata.normalize("NFKD",str(v or "")).lower()
    x="".join(ch for ch in x if not unicodedata.category(ch).startswith("P"))
    return " ".join(_ARTICLE.sub(" ",x).split())

def main():
    rows=fetch_rows(); out=[]; attempted=exact=0
    for row in rows:
        o=propose(task_id=f"triviaqa_validation_row_{row['idx']}",question=row["q"],has_nonempty_image_payload=False)
        cand=o.get("candidate_answer") if isinstance(o.get("candidate_answer"),str) else ""
        hit=bool(cand.strip()) and norm(cand)==norm(row["a"])
        attempted+=int(bool(cand.strip())); exact+=int(hit)
        out.append({
            "row_idx":row["idx"],"attempted":bool(cand.strip()),"normalized_exact":hit,
            "status":o.get("status"),"question_kind":o.get("question_kind"),
            "search_status":o.get("search_status"),
            "search_result_count":o.get("search_result_count"),
            "fetched_url_count":o.get("fetched_url_count"),
            "fallback_general_form":o.get("fallback_general_form"),
            "candidate_sha256":hashlib.sha256(cand.encode()).hexdigest(),
            "external_model_calls":int(o.get("external_model_calls",0) or 0),
            "model_dependency_count":int(o.get("model_dependency_count",0) or 0),
            "gold_accessed":bool(o.get("gold_accessed",False)),
        })
        if out[-1]["external_model_calls"] or out[-1]["model_dependency_count"] or out[-1]["gold_accessed"]:
            raise RuntimeError("CAPABILITY_BOUNDARY_VIOLATION")
        time.sleep(0.20)
    summary={
      "schema":"PROJECT_BRAIN_HLE_EXISTING_RETRIEVAL_V2_CONSUMED_DIAGNOSTIC_V1",
      "sample_size":N,"attempted":attempted,"attempt_rate":attempted/N,
      "normalized_exact":exact,"normalized_exact_rate":exact/N,
      "gate":{"minimum_attempt_rate":0.25,"minimum_normalized_exact_rate":0.20,
              "passed":attempted/N>=0.25 and exact/N>=0.20},
      "per_slot":out,"external_model_calls_total":0,"model_dependency_count_total":0,
      "hle_questions_consumed":0,"hle_gold_consumed":0,"hle_score_credit":0
    }
    Path("/tmp/retrieval_v2_diag.json").write_text(json.dumps(summary,sort_keys=True,indent=2)+"\n")
    print(json.dumps({k:v for k,v in summary.items() if k!="per_slot"},sort_keys=True))
    for x in out: print(json.dumps(x,sort_keys=True))
if __name__=="__main__": main()
