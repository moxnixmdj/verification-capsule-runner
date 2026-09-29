#!/usr/bin/env python3
import argparse, json, pathlib, time, urllib.request

MODEL_LABEL="Qwen3.5-9B-M-Q4_K_M-local"

def atomic_write(path,obj):
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(obj,sort_keys=True)+"\n",encoding="utf-8")
    tmp.replace(path)

def planner(server,payload):
    prompt=str(payload.get("prompt") or "")
    body=json.dumps({
      "model":"local",
      "messages":[{"role":"user","content":prompt}],
      "temperature":0.05,
      "max_tokens":1800,
      "stream":False
    }).encode()
    req=urllib.request.Request(
      server.rstrip("/")+"/v1/chat/completions",
      data=body,
      headers={"Content-Type":"application/json"},
      method="POST"
    )
    t=time.monotonic()
    with urllib.request.urlopen(req,timeout=300) as r:
        obj=json.loads(r.read(6_000_000).decode("utf-8"))
    msg=((obj.get("choices") or [{}])[0].get("message") or {})
    content=msg.get("content")
    if not isinstance(content,str) or not content.strip():
        content=msg.get("reasoning_content")
    if not isinstance(content,str) or not content.strip():
        raise RuntimeError("LOCAL_PLANNER_EMPTY")
    return {
      "text":content,
      "model":MODEL_LABEL,
      "duration_s":round(time.monotonic()-t,3),
      "errors":[],
      "backend":"LOCAL_LLAMA_SERVER_QWEN9B_CLICK_TASK_C"
    }

def handle(server,req):
    kind=str(req.get("kind") or "")
    if kind!="planner":
        raise ValueError("TASK_C_NETWORK_AND_NONPLANNER_BRIDGE_ACTIONS_DISABLED:"+kind)
    return planner(server,req.get("payload") or {})

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--dir",required=True)
    ap.add_argument("--server",default="http://127.0.0.1:8080")
    args=ap.parse_args()
    d=pathlib.Path(args.dir); d.mkdir(parents=True,exist_ok=True)
    log=d/"LOCAL_BRIDGE_LOG.jsonl"
    while True:
        for p in sorted(d.glob("*.request.json")):
            sha=p.name.split(".",1)[0]
            out=d/(sha+".response.json")
            if out.exists():
                continue
            req={}
            try:
                req=json.loads(p.read_text(encoding="utf-8"))
                base={k:v for k,v in req.items() if k!="request_sha256"}
                import hashlib
                calc=hashlib.sha256(json.dumps(base,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
                if calc!=sha or req.get("request_sha256")!=sha:
                    raise ValueError("REQUEST_HASH_MISMATCH")
                t=time.monotonic()
                result=handle(args.server,req)
                resp={
                  "schema":"PROJECT_BRAIN_EXTERNAL_TOOL_RESPONSE_V1",
                  "request_sha256":sha,"kind":req.get("kind"),
                  "agent_id":req.get("agent_id"),"task_id":req.get("task_id"),
                  "status":"ok","result":result
                }
                rec={
                  "request_sha256":sha,"kind":req.get("kind"),"status":"ok",
                  "duration_s":round(time.monotonic()-t,3),
                  "planner_model":result.get("model"),
                  "planner_backend":result.get("backend")
                }
            except Exception as e:
                resp={
                  "schema":"PROJECT_BRAIN_EXTERNAL_TOOL_RESPONSE_V1",
                  "request_sha256":sha,"kind":req.get("kind"),
                  "agent_id":req.get("agent_id"),"task_id":req.get("task_id"),
                  "status":"error","result":{"error":type(e).__name__+":"+str(e)}
                }
                rec={
                  "request_sha256":sha,"kind":req.get("kind"),"status":"error",
                  "error":type(e).__name__+":"+str(e)
                }
            atomic_write(out,resp)
            with log.open("a",encoding="utf-8") as fh:
                fh.write(json.dumps(rec,sort_keys=True)+"\n")
        time.sleep(0.02)

if __name__=="__main__":
    main()
