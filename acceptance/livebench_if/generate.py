#!/usr/bin/env python3
from __future__ import annotations
import concurrent.futures as cf
import hashlib, json, os, pathlib, time, urllib.request
import pyarrow.parquet as pq
from canonical.runtime.instruction_following_brain_configuration_v1 import messages_for_prompt

DATASET=pathlib.Path(os.environ.get("LIVEBENCH_IF_DATASET","/tmp/livebench_if.parquet"))
SERVER=os.environ.get("LLAMA_SERVER","http://127.0.0.1:8080").rstrip("/")
OUT=pathlib.Path(os.environ.get("CONFIGURED_OUT","configured_responses.jsonl"))
ABLATION_OUT=pathlib.Path(os.environ.get("ABLATION_OUT","ablation_responses.jsonl"))
MAX_TOKENS=512
SEED=20261002
PARALLELISM=2
ABLATION_N=40
ABLATION_PREFIX="BRAIN_LIVEBENCH_IF_ABLATION_V1\0"

def _completion(messages, qid):
    body=json.dumps({
        "model":"local",
        "messages":messages,
        "temperature":0,
        "top_p":1,
        "max_tokens":MAX_TOKENS,
        "seed":SEED,
        "stream":False,
    },ensure_ascii=False).encode("utf-8")
    last=None
    for attempt in (1,2):
        try:
            req=urllib.request.Request(
                SERVER+"/v1/chat/completions",data=body,
                headers={"Content-Type":"application/json"},method="POST")
            t=time.monotonic()
            with urllib.request.urlopen(req,timeout=300) as r:
                obj=json.loads(r.read(4_000_000).decode("utf-8"))
            msg=((obj.get("choices") or [{}])[0].get("message") or {})
            text=msg.get("content")
            if not isinstance(text,str) or not text.strip():
                text=msg.get("reasoning_content")
            if not isinstance(text,str) or not text.strip():
                raise RuntimeError("EMPTY_MODEL_RESPONSE")
            return {
                "question_id":qid,"response":text,
                "attempt":attempt,"duration_s":round(time.monotonic()-t,3)
            }
        except Exception as exc:
            last=exc
            if attempt==2:
                raise
            time.sleep(1)
    raise last

def _rows():
    table=pq.read_table(DATASET,columns=["question_id","turns"])
    rows=table.to_pylist()
    if len(rows)!=400:
        raise RuntimeError(f"EXPECTED_400_ROWS_GOT_{len(rows)}")
    out=[]
    seen=set()
    for row in rows:
        qid=str(row["question_id"])
        if qid in seen: raise RuntimeError("DUPLICATE_QUESTION_ID")
        seen.add(qid)
        turns=row.get("turns")
        if not isinstance(turns,list) or len(turns)!=1 or not isinstance(turns[0],str):
            raise RuntimeError("INVALID_USER_VISIBLE_TURN")
        out.append((qid,turns[0]))
    return out

def _write(path, rows):
    path.write_text("".join(json.dumps(x,ensure_ascii=False,sort_keys=True)+"\n" for x in rows),encoding="utf-8")

def main():
    rows=_rows()
    configured=[]
    def do_config(item):
        qid,prompt=item
        return _completion(messages_for_prompt(prompt),qid)
    with cf.ThreadPoolExecutor(max_workers=PARALLELISM) as ex:
        futs={ex.submit(do_config,item):item[0] for item in rows}
        for fut in cf.as_completed(futs):
            configured.append(fut.result())
            if len(configured)%20==0: print("CONFIGURED_COMPLETE",len(configured),flush=True)
    configured.sort(key=lambda x:x["question_id"])
    _write(OUT,configured)

    chosen=sorted(
        rows,
        key=lambda x: hashlib.sha256((ABLATION_PREFIX+x[0]).encode()).hexdigest()
    )[:ABLATION_N]
    baseline=[]
    def do_base(item):
        qid,prompt=item
        return _completion([{"role":"user","content":prompt}],qid)
    with cf.ThreadPoolExecutor(max_workers=PARALLELISM) as ex:
        futs={ex.submit(do_base,item):item[0] for item in chosen}
        for fut in cf.as_completed(futs):
            baseline.append(fut.result())
    baseline.sort(key=lambda x:x["question_id"])
    _write(ABLATION_OUT,baseline)
    manifest={
        "schema":"PROJECT_BRAIN_LIVEBENCH_IF_GENERATION_RESULT_V1",
        "configured_count":len(configured),
        "ablation_count":len(baseline),
        "configured_response_sha256":hashlib.sha256(OUT.read_bytes()).hexdigest(),
        "ablation_response_sha256":hashlib.sha256(ABLATION_OUT.read_bytes()).hexdigest(),
        "candidate_visible_columns":["question_id","turns"],
        "hidden_evaluator_columns_consumed_during_generation":[],
        "generation_parameters":{"temperature":0,"top_p":1,"max_tokens":MAX_TOKENS,"seed":SEED,"parallelism":PARALLELISM},
    }
    pathlib.Path("generation_manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    print(json.dumps(manifest,sort_keys=True))

if __name__=="__main__":
    main()
