#!/usr/bin/env python3
import argparse, base64, hashlib, json, pathlib, time, urllib.parse, urllib.request

ALLOWED_HOSTS={
    "huggingface.co","github.com","api.github.com","raw.githubusercontent.com",
    "www.ncbi.nlm.nih.gov","ncbi.nlm.nih.gov","pmc.ncbi.nlm.nih.gov","pubmed.ncbi.nlm.nih.gov"
}
MODEL_LABEL="Qwen3.5-9B-M-Q4_K_M-local"

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
    req=urllib.request.Request(url,data=data,headers=dict(headers or {"User-Agent":"ProjectBrain-Qwen9B-TaskB/1"}),method=method)
    with urllib.request.urlopen(req,timeout=timeout) as r:
        final=r.geturl()
        if urllib.parse.urlparse(final).hostname.lower() not in ALLOWED_HOSTS:
            raise ValueError("REDIRECT_HOST_NOT_ALLOWED")
        body=r.read(max_bytes)
        return r.status,final,dict(r.headers),body

def planner(server,payload):
    body=json.dumps({
      "model":"local",
      "messages":[{"role":"user","content":str(payload.get("prompt") or "")}],
      "temperature":0.1,
      "max_tokens":512,
      "stream":False
    }).encode()
    req=urllib.request.Request(server.rstrip("/")+"/v1/chat/completions",data=body,headers={"Content-Type":"application/json"},method="POST")
    t=time.monotonic()
    with urllib.request.urlopen(req,timeout=240) as r:
        obj=json.loads(r.read(3_000_000).decode("utf-8"))
    msg=((obj.get("choices") or [{}])[0].get("message") or {})
    content=msg.get("content")
    if not isinstance(content,str) or not content.strip():
        content=msg.get("reasoning_content")
    if not isinstance(content,str) or not content.strip():
        raise RuntimeError("LOCAL_PLANNER_EMPTY")
    return {"text":content,"model":MODEL_LABEL,"duration_s":round(time.monotonic()-t,3),"errors":[],"backend":"LOCAL_LLAMA_SERVER"}

def handle(server,req):
    kind=str(req.get("kind") or "")
    payload=req.get("payload") or {}
    if kind=="planner":
        return planner(server,payload)
    if kind=="http_get":
        status,final,headers,body=fetch_public(payload["url"],timeout=float(payload.get("timeout_s") or 30),max_bytes=int(payload.get("max_bytes") or 250000))
        return {"url":final,"status":status,"body_sha256":hashlib.sha256(body).hexdigest(),"body_excerpt":body[:16000].decode("utf-8","replace"),"duration_s":0,"transport":"LOCAL_BRIDGE_PUBLIC_HTTPS"}
    if kind=="urlopen":
        data=base64.b64decode(payload["data_b64"]) if payload.get("data_b64") else None
        status,final,headers,body=fetch_public(payload["url"],method=str(payload.get("method") or "GET"),headers=payload.get("headers") or {},data=data,timeout=float(payload.get("timeout_s") or 30),max_bytes=3_000_000)
        return {"status":status,"final_url":final,"headers":headers,"body_b64":base64.b64encode(body).decode("ascii")}
    raise ValueError("KIND_NOT_ALLOWED:"+kind)

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
            if out.exists(): continue
            try:
                req=json.loads(p.read_text(encoding="utf-8"))
                base={k:v for k,v in req.items() if k!="request_sha256"}
                calc=hashlib.sha256(json.dumps(base,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
                if calc!=sha or req.get("request_sha256")!=sha:
                    raise ValueError("REQUEST_HASH_MISMATCH")
                t=time.monotonic()
                result=handle(args.server,req)
                resp={"schema":"PROJECT_BRAIN_EXTERNAL_TOOL_RESPONSE_V1","request_sha256":sha,"kind":req.get("kind"),"agent_id":req.get("agent_id"),"task_id":req.get("task_id"),"status":"ok","result":result}
                rec={"request_sha256":sha,"kind":req.get("kind"),"status":"ok","duration_s":round(time.monotonic()-t,3),"planner_model":result.get("model"),"planner_backend":result.get("backend"),"url":result.get("url")}
            except Exception as e:
                resp={"schema":"PROJECT_BRAIN_EXTERNAL_TOOL_RESPONSE_V1","request_sha256":sha,"kind":req.get("kind") if "req" in locals() else None,"agent_id":req.get("agent_id") if "req" in locals() else None,"task_id":req.get("task_id") if "req" in locals() else None,"status":"error","result":{"error":type(e).__name__+":"+str(e)}}
                rec={"request_sha256":sha,"kind":resp.get("kind"),"status":"error","error":type(e).__name__+":"+str(e)}
            atomic_write(out,resp)
            with log.open("a",encoding="utf-8") as fh: fh.write(json.dumps(rec,sort_keys=True)+"\n")
        time.sleep(0.02)
if __name__=="__main__": main()
