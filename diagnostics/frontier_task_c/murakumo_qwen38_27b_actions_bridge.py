#!/usr/bin/env python3
import argparse, base64, hashlib, json, pathlib, time, urllib.parse, urllib.request

ALLOWED_HOSTS={
    "raw.githubusercontent.com","github.com","api.github.com","docs.github.com"
}
MODEL_ID="qwen3.8-27b-uncensored"
PLANNER_ENDPOINT="https://api.murakumo.cloud/v1/chat/completions"

def atomic_write(path,obj):
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(obj,sort_keys=True)+"\n",encoding="utf-8")
    tmp.replace(path)

def safe_url(url):
    u=urllib.parse.urlparse(str(url))
    if u.scheme!="https" or not u.hostname or u.hostname.lower() not in ALLOWED_HOSTS:
        raise ValueError("URL_NOT_ALLOWED")
    return u.geturl()

def fetch_public(url,method="GET",headers=None,data=None,timeout=30,max_bytes=500000):
    url=safe_url(url)
    req=urllib.request.Request(
        url,data=data,
        headers=dict(headers or {"User-Agent":"ProjectBrain-TaskC/1"}),
        method=method
    )
    t=time.monotonic()
    with urllib.request.urlopen(req,timeout=timeout) as r:
        final=r.geturl()
        if urllib.parse.urlparse(final).hostname.lower() not in ALLOWED_HOSTS:
            raise ValueError("REDIRECT_HOST_NOT_ALLOWED")
        body=r.read(max_bytes)
        return r.status,final,dict(r.headers),body,round(time.monotonic()-t,3)

def planner(payload):
    body=json.dumps({
      "model":MODEL_ID,
      "messages":[
        {"role":"system","content":"You are a bounded technical research planner. Return JSON text only in the exact schema requested by the prompt. Do not emit tool_calls."},
        {"role":"user","content":str(payload.get("prompt") or "")}
      ],
      "temperature":0.1,
      "max_tokens":1024
    }).encode()
    req=urllib.request.Request(
        PLANNER_ENDPOINT,data=body,
        headers={"Content-Type":"application/json","User-Agent":"ProjectBrain-TaskC-Planner/1"},
        method="POST"
    )
    t=time.monotonic()
    with urllib.request.urlopen(req,timeout=420) as r:
        obj=json.loads(r.read(3_000_000).decode("utf-8"))
    observed=str(obj.get("model") or "")
    if observed!=MODEL_ID:
        raise RuntimeError("PLANNER_MODEL_IDENTITY_MISMATCH:"+observed)
    msg=((obj.get("choices") or [{}])[0].get("message") or {})
    content=msg.get("content")
    if not isinstance(content,str) or not content.strip():
        content=msg.get("reasoning_content")
    if not isinstance(content,str) or not content.strip():
        raise RuntimeError("PLANNER_EMPTY")
    return {
      "text":content,
      "model":MODEL_ID,
      "duration_s":round(time.monotonic()-t,3),
      "errors":[],
      "backend":"MURAKUMO_PUBLIC_PINNED_QWEN38_27B"
    }

def handle(req):
    kind=str(req.get("kind") or "")
    payload=req.get("payload") or {}
    if kind=="planner":
        return planner(payload)
    if kind=="http_get":
        status,final,headers,body,wall=fetch_public(
            payload["url"],
            timeout=float(payload.get("timeout_s") or 30),
            max_bytes=int(payload.get("max_bytes") or 250000)
        )
        return {
          "url":final,"status":status,
          "body_sha256":hashlib.sha256(body).hexdigest(),
          "body_excerpt":body[:24000].decode("utf-8","replace"),
          "duration_s":wall,
          "transport":"TASK_C_BRIDGE_PUBLIC_HTTPS"
        }
    if kind=="urlopen":
        data=base64.b64decode(payload["data_b64"]) if payload.get("data_b64") else None
        status,final,headers,body,wall=fetch_public(
            payload["url"],method=str(payload.get("method") or "GET"),
            headers=payload.get("headers") or {},data=data,
            timeout=float(payload.get("timeout_s") or 30),max_bytes=3_000_000
        )
        return {
          "status":status,"final_url":final,"headers":headers,
          "body_b64":base64.b64encode(body).decode("ascii"),
          "duration_s":wall
        }
    raise ValueError("KIND_NOT_ALLOWED:"+kind)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--dir",required=True)
    args=ap.parse_args()
    d=pathlib.Path(args.dir); d.mkdir(parents=True,exist_ok=True)
    log=d/"TASK_C_BRIDGE_LOG.jsonl"
    while True:
        for p in sorted(d.glob("*.request.json")):
            sha=p.name.split(".",1)[0]
            out=d/(sha+".response.json")
            if out.exists():
                continue
            try:
                req=json.loads(p.read_text(encoding="utf-8"))
                base={k:v for k,v in req.items() if k!="request_sha256"}
                calc=hashlib.sha256(
                    json.dumps(base,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
                ).hexdigest()
                if calc!=sha or req.get("request_sha256")!=sha:
                    raise ValueError("REQUEST_HASH_MISMATCH")
                t=time.monotonic()
                result=handle(req)
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
                  "planner_backend":result.get("backend"),
                  "url":result.get("url")
                }
            except Exception as e:
                resp={
                  "schema":"PROJECT_BRAIN_EXTERNAL_TOOL_RESPONSE_V1",
                  "request_sha256":sha,
                  "kind":req.get("kind") if "req" in locals() else None,
                  "agent_id":req.get("agent_id") if "req" in locals() else None,
                  "task_id":req.get("task_id") if "req" in locals() else None,
                  "status":"error","result":{"error":type(e).__name__+":"+str(e)}
                }
                rec={
                  "request_sha256":sha,"kind":resp.get("kind"),"status":"error",
                  "error":type(e).__name__+":"+str(e)
                }
            atomic_write(out,resp)
            with log.open("a",encoding="utf-8") as fh:
                fh.write(json.dumps(rec,sort_keys=True)+"\n")
        time.sleep(0.02)

if __name__=="__main__":
    main()
