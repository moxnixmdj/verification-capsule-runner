#!/usr/bin/env python3
"""Project Brain fail-closed one-shot execution guard.

No authorization is created here. Existing Brain authorization must already be
valid. This layer only prevents replay/duplicate dispatch for frozen identities.
"""
from __future__ import annotations
import argparse,base64,binascii,dataclasses,hashlib,json,os,pathlib,re,subprocess,sys,urllib.error,urllib.request,uuid
from datetime import datetime,timezone
from urllib.parse import quote

class Denied(RuntimeError): pass
class Uncertain(RuntimeError): pass
class StoreUnavailable(RuntimeError): pass

def enc(v): return json.dumps(v,sort_keys=True,separators=(",",":"),allow_nan=False)
def nonempty(v,n):
    if not isinstance(v,str) or not v.strip() or len(v)>4096: raise ValueError("INVALID_"+n.upper())
def digest(v,n,L=64):
    if not isinstance(v,str) or not re.fullmatch(f"[0-9a-f]{{{L}}}",v): raise ValueError("INVALID_"+n.upper())
def blob_sha(raw): return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def file_sha(path): return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
def key_gate(g): nonempty(g,"gate_id"); return "gates/"+hashlib.sha256(g.encode()).hexdigest()+".json"
def key_attempt(kind,a):
    if not isinstance(a,str) or not re.fullmatch(r"[0-9a-f]{32}",a): raise Denied("INVALID_ATTEMPT_ID")
    return f"{kind}/{a}.json"

@dataclasses.dataclass(frozen=True)
class Frozen:
    gate_id:str; problem_sha256:str; task_sha256:str; runtime_sha256:str; canonical_base:str; authorization_sha256:str
    def validate(self):
        nonempty(self.gate_id,"gate_id")
        for n in ("problem_sha256","task_sha256","runtime_sha256","authorization_sha256"): digest(getattr(self,n),n)
        digest(self.canonical_base,"canonical_base",40)

class MemStore:
    def __init__(self): self.d={}
    def create(self,k,v):
        if k in self.d:return False
        self.d[k]=json.loads(enc(v)); return True
    def read(self,k): return self.d.get(k)

class GitHubStore:
    def __init__(self,request,repo,branch,namespace="admissions-v1"):
        if branch in ("main","master","") or not branch: raise ValueError("EXPLICIT_COORDINATION_BRANCH_REQUIRED")
        self.request=request; self.repo=repo; self.branch=branch; self.ns=namespace
    def _path(self,k):
        if not re.fullmatch(r"[A-Za-z0-9_.\-/]+",k) or any(x in ("",".","..") for x in k.split("/")): raise ValueError("INVALID_RECORD_PATH")
        rel=f"{self.ns}/{k}"; return f"/repos/{self.repo}/contents/{rel}",rel
    def create(self,k,v):
        path,rel=self._path(k); raw=enc(v).encode()
        status,body,_=self.request("PUT",path,{"message":"Reserve immutable execution evidence","branch":self.branch,"content":base64.b64encode(raw).decode()})
        if status in (409,422): return False
        if status!=201 or not isinstance(body,dict): raise StoreUnavailable("CREATE_NOT_CONFIRMED")
        c=body.get("content")
        if not isinstance(c,dict) or c.get("path")!=rel or c.get("sha")!=blob_sha(raw): raise StoreUnavailable("CREATE_RECEIPT_BINDING_MISMATCH")
        return True
    def read(self,k):
        path,rel=self._path(k); status,body,_=self.request("GET",path+"?ref="+quote(self.branch,safe=""),None)
        if status==404:return None
        if status!=200 or not isinstance(body,dict) or body.get("type")!="file" or body.get("path")!=rel or body.get("encoding")!="base64": raise StoreUnavailable("READ_NOT_CONFIRMED")
        try:
            raw=base64.b64decode("".join(body["content"].split()),validate=True)
            if body.get("sha")!=blob_sha(raw): raise ValueError()
            v=json.loads(raw)
            if not isinstance(v,dict): raise ValueError()
            return v
        except (KeyError,ValueError,TypeError,UnicodeError,binascii.Error) as e: raise StoreUnavailable("MALFORMED_OR_CORRUPT_RECORD") from e

def create_required(store,k,v):
    try: ok=store.create(k,v)
    except Exception as e: raise Denied("RESERVATION_UNCONFIRMED_NO_DISPATCH") from e
    if ok is not True: raise Denied("ALREADY_RESERVED_OR_CREATE_NOT_CONFIRMED")
def create_identical(store,k,v):
    try: ok=store.create(k,v)
    except Exception as e: raise Denied("HISTORICAL_IMPORT_WRITE_UNCONFIRMED") from e
    if ok is True:return
    old=store.read(k)
    if old is None or enc(old)!=enc(v): raise Denied("CONFLICTING_HISTORICAL_RESERVATION")

def reserve_live(store,spec,owner,run_ref):
    spec.validate(); nonempty(owner,"owner_id"); nonempty(run_ref,"run_ref"); a=uuid.uuid4().hex
    r={"schema":"BRAIN_DISPATCH_RESERVATION_V1","attempt_id":a,"owner_id":owner,"frozen":dataclasses.asdict(spec),"reserved_at":datetime.now(timezone.utc).isoformat()}
    create_required(store,key_gate(spec.gate_id),r); create_required(store,"problems/"+spec.problem_sha256+".json",r)
    ack={"schema":"BRAIN_DISPATCH_ACK_V1","attempt_id":a,"gate_id":spec.gate_id,"run_ref":run_ref}
    try: ok=store.create(key_attempt("dispatches",a),ack)
    except Exception as e: raise Uncertain("DISPATCH_ACK_UNCERTAIN:"+a) from e
    if ok is not True: raise Uncertain("DISPATCH_ACK_NOT_PERSISTED:"+a)
    return a

def seed_history(store,spec,item):
    spec.validate(); a=item["attempt_id"]; key_attempt("dispatches",a); nonempty(item["owner_id"],"owner_id"); nonempty(item["source_ref"],"source_ref"); digest(item["source_evidence_sha256"],"source_evidence_sha256"); nonempty(item["observed_at"],"observed_at")
    r={"schema":"BRAIN_DISPATCH_RESERVATION_V1","attempt_id":a,"owner_id":item["owner_id"],"frozen":dataclasses.asdict(spec),"reserved_at":item["observed_at"],"reservation_origin":"HISTORICAL_RECONCILIATION_V1","historical_evidence":{"source_ref":item["source_ref"],"evidence_sha256":item["source_evidence_sha256"]}}
    create_identical(store,key_gate(spec.gate_id),r); create_identical(store,"problems/"+spec.problem_sha256+".json",r)
    if store.read(key_gate(spec.gate_id))!=store.read("problems/"+spec.problem_sha256+".json"): raise Denied("INCOMPLETE_HISTORICAL_RESERVATION")

def request_factory(token):
    nonempty(token,"github_token")
    def request(method,path,payload):
        raw=None if payload is None else enc(payload).encode(); headers={"Accept":"application/vnd.github+json","Authorization":"Bearer "+token,"X-GitHub-Api-Version":"2022-11-28","User-Agent":"project-brain-execution-guard/1"}
        if raw is not None:headers["Content-Type"]="application/json"
        req=urllib.request.Request("https://api.github.com"+path,data=raw,method=method,headers=headers)
        try:
            with urllib.request.urlopen(req,timeout=20) as resp: status=int(resp.status); b=resp.read(1_000_000); h=dict(resp.headers.items())
        except urllib.error.HTTPError as e: status=int(e.code); b=e.read(1_000_000); h=dict(e.headers.items()) if e.headers else {}
        except Exception as e: raise StoreUnavailable("GITHUB_TRANSPORT_UNCERTAIN_NO_RETRY") from e
        try: body=json.loads(b.decode()) if b else {}
        except Exception as e: raise StoreUnavailable("GITHUB_RESPONSE_NOT_JSON") from e
        low={str(k).lower():str(v) for k,v in h.items()}; msg=str(body.get("message","")) if isinstance(body,dict) else ""
        if status==429 or (status==403 and (low.get("x-ratelimit-remaining")=="0" or "rate limit" in msg.lower())): raise StoreUnavailable("GITHUB_RATE_LIMIT_NO_RETRY")
        return status,body,h
    return request

def github_store():
    token=os.environ.get("GITHUB_TOKEN",""); repo=os.environ.get("BRAIN_EXECUTION_GUARD_REPOSITORY") or os.environ.get("GITHUB_REPOSITORY",""); branch=os.environ.get("BRAIN_EXECUTION_GUARD_BRANCH",""); ns=os.environ.get("BRAIN_EXECUTION_GUARD_NAMESPACE","admissions-v1")
    if not token or not repo or not branch: raise ValueError("GITHUB_GUARD_ENV_INCOMPLETE")
    request=request_factory(token); status,body,_=request("GET",f"/repos/{repo}/branches/{quote(branch,safe='')}",None)
    if status!=200 or not isinstance(body,dict) or body.get("name")!=branch or body.get("protected") is not True: raise Denied("COORDINATION_BRANCH_NOT_PROTECTED")
    return GitHubStore(request,repo,branch,ns)

def load_binding(path):
    p=pathlib.Path(path).resolve(); d=json.loads(p.read_text())
    if d.get("schema")!="BRAIN_EXECUTION_GUARD_BINDING_V1": raise ValueError("GUARD_BINDING_SCHEMA_INVALID")
    f=Frozen(**d["frozen"]); f.validate(); exp={"problem":f.problem_sha256,"task":f.task_sha256,"runtime":f.runtime_sha256,"authorization":f.authorization_sha256}
    for name,sha in exp.items():
        item=d.get("bindings",{}).get(name); q=(p.parent/item["path"]).resolve() if isinstance(item,dict) and isinstance(item.get("path"),str) else None
        if q is None or not q.is_file() or item.get("sha256")!=sha or file_sha(q)!=sha: raise ValueError("GUARD_BOUND_FILE_HASH_MISMATCH:"+name)
    if os.environ.get("BRAIN_CANONICAL_BASE","")!=f.canonical_base: raise ValueError("BRAIN_CANONICAL_BASE_MISMATCH")
    return f

def run_ref():
    repo=os.environ.get("GITHUB_REPOSITORY",""); rid=os.environ.get("GITHUB_RUN_ID",""); att=os.environ.get("GITHUB_RUN_ATTEMPT","1"); server=os.environ.get("GITHUB_SERVER_URL","https://github.com").rstrip("/")
    if not repo or not rid: raise ValueError("GITHUB_RUN_IDENTITY_REQUIRED")
    return f"{server}/{repo}/actions/runs/{rid}/attempts/{att}"
def owner():
    vals=[os.environ.get(x,"") for x in ("GITHUB_WORKFLOW_REF","GITHUB_RUN_ID","GITHUB_RUN_ATTEMPT","GITHUB_JOB")]
    if any(not v for v in vals): raise ValueError("GITHUB_OWNER_IDENTITY_REQUIRED")
    return "github-actions:"+":".join(vals)

def cmd_run(ns):
    spec=load_binding(ns.binding); store=github_store(); ref=run_ref(); a=reserve_live(store,spec,owner(),ref)
    env=os.environ.copy()
    for secret_name in ("GITHUB_TOKEN","GH_TOKEN","GITHUB_PAT","GITHUB_APP_TOKEN","BRAIN_EXECUTION_GUARD_TOKEN"):
        env.pop(secret_name,None)
    env.update(BRAIN_EXECUTION_ATTEMPT_ID=a,BRAIN_EXECUTION_GUARD_RUN_REF=ref,BRAIN_EXECUTION_GUARD_GATE_ID=spec.gate_id)
    print(enc({"schema":"BRAIN_EXECUTION_GUARD_LAUNCH_V1","status":"ADMISSION_ACKNOWLEDGED_BEFORE_CHILD_START","attempt_id":a,"run_ref":ref,"gate_id":spec.gate_id}),flush=True)
    return subprocess.run(ns.command,env=env,check=False).returncode

def cmd_seed(ns):
    d=json.loads(pathlib.Path(ns.manifest).read_text()); items=d.get("items")
    if d.get("schema")!="BRAIN_EXECUTION_HISTORICAL_IMPORT_V1" or not isinstance(items,list) or not items: raise ValueError("HISTORICAL_IMPORT_INVALID")
    for item in items: seed_history(MemStore(),Frozen(**item["frozen"]),item)
    store=github_store()
    for item in items: seed_history(store,Frozen(**item["frozen"]),item)
    print(enc({"status":"HISTORICAL_IMPORT_COMPLETE","count":len(items)})); return 0

def main():
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest="cmd",required=True)
    r=sub.add_parser("run"); r.add_argument("--binding",required=True); r.add_argument("command",nargs=argparse.REMAINDER)
    s=sub.add_parser("seed-history"); s.add_argument("--manifest",required=True)
    ns=p.parse_args()
    if ns.cmd=="run":
        if ns.command and ns.command[0]=="--":ns.command=ns.command[1:]
        if not ns.command:raise ValueError("PROTECTED_COMMAND_REQUIRED")
        return cmd_run(ns)
    return cmd_seed(ns)
if __name__=="__main__":
    try: raise SystemExit(main())
    except (Denied,Uncertain,StoreUnavailable,ValueError,KeyError,TypeError) as e:
        print("EXECUTION_GUARD_DENIED:"+str(e),file=sys.stderr); raise SystemExit(73)
