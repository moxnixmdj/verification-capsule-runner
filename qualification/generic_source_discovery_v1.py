#!/usr/bin/env python3
"""Model-independent source-candidate discovery and URL binding.
Never declares a discovered page authoritative.
"""
from __future__ import annotations
import json,re,subprocess,urllib.parse,urllib.request
from dataclasses import dataclass,asdict

SCHEMA="PROJECT_BRAIN_GENERIC_SOURCE_CANDIDATE_DISCOVERY_V1"
_STOP={"a","an","and","are","as","at","be","by","can","could","determine","does","for","from","how","if","in","into","is","it","its","of","on","or","that","the","their","this","to","using","whether","which","while","with","would","assess","evaluate","investigate","estimate","quantify","compare","analyze","analyse","authoritative","source","sources","primary","official","evidence"}
_AUTH=("official","documentation","manual","reference","standard","specification","technical","dataset","data","api","publication","report")

@dataclass(frozen=True)
class Candidate:
    rank:int; query_index:int; title:str; url:str; snippet:str; host:str
    structural_score:int; authority_status:str="UNVERIFIED_CANDIDATE"

def _tokens(text):
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9_.+/#-]*",text or "")

def build_queries(objective):
    raw=" ".join((objective or "").strip().split())
    if not raw: raise ValueError("OBJECTIVE_REQUIRED")
    terms=[]; seen=set()
    for tok in _tokens(raw):
        low=tok.lower().strip("._-/#")
        if not low or low in _STOP or len(low)<2: continue
        if low not in seen: seen.add(low); terms.append(tok)
        if len(terms)>=18: break
    if len(terms)<2: raise ValueError("OBJECTIVE_TOO_UNDERSPECIFIED")
    core=" ".join(terms)
    return [f"{core} official documentation primary source",f"{core} technical reference standard"]

def _parse(blob):
    obj=json.loads(blob)
    if isinstance(obj,list): return [x for x in obj if isinstance(x,dict)]
    if isinstance(obj,dict):
        for k in ("results","items"):
            if isinstance(obj.get(k),list): return [x for x in obj[k] if isinstance(x,dict)]
    raise RuntimeError("DDGR_JSON_SHAPE_UNSUPPORTED")

def _field(item,*names):
    for n in names:
        v=item.get(n)
        if isinstance(v,str) and v.strip(): return v.strip()
    return ""

def _score(host,title,snippet,objective):
    h=host.lower(); body=f"{title} {snippet}".lower(); s=0
    if h.endswith(".gov") or ".gov." in h: s+=30
    if h.endswith(".mil") or ".mil." in h: s+=30
    if h.endswith(".edu") or ".edu." in h: s+=18
    if h.startswith("docs.") or ".docs." in h: s+=8
    s+=sum(2 for t in _AUTH if t in body)
    ot={t.lower().strip("._-/#") for t in _tokens(objective) if len(t)>=4 and t.lower() not in _STOP}
    ht=set(re.findall(r"[a-z0-9]+",h))
    s+=min(12,3*len(ot&ht))
    return s

def discover(objective):
    queries=build_queries(objective); merged={}; obs=[]
    for qi,q in enumerate(queries):
        p=subprocess.run(["ddgr","--json","--np","--num","15",q],text=True,capture_output=True,timeout=45)
        obs.append({"query_index":qi,"query":q,"returncode":p.returncode,"stderr_tail":p.stderr[-1000:]})
        if p.returncode: continue
        try: items=_parse(p.stdout)
        except Exception as e:
            obs[-1]["parse_error"]=f"{type(e).__name__}:{e}"; continue
        for rank,item in enumerate(items):
            url=_field(item,"url","href","link"); title=_field(item,"title","heading"); snippet=_field(item,"abstract","body","snippet","text")
            try: u=urllib.parse.urlsplit(url)
            except Exception: continue
            if u.scheme not in ("http","https") or not u.netloc: continue
            host=u.hostname or ""; key=urllib.parse.urlunsplit((u.scheme,u.netloc,u.path,u.query,""))
            c=Candidate(rank,qi,title,key,snippet,host,_score(host,title,snippet,objective))
            old=merged.get(key)
            if old is None or (c.structural_score,-c.rank)>(old.structural_score,-old.rank): merged[key]=c
    cs=sorted(merged.values(),key=lambda c:(-c.structural_score,c.query_index,c.rank,c.url))[:30]
    return {"schema":SCHEMA,"status":"CANDIDATES_DISCOVERED" if cs else "NO_CANDIDATES","objective":" ".join((objective or "").strip().split()),"queries":queries,"observations":obs,"candidates":[asdict(c) for c in cs],"model_dependency_count":0,"authority_claimed":False}

def verify_url_binding(url,timeout=15):
    req=urllib.request.Request(url,headers={"User-Agent":"ProjectBrainSourceDiscovery/1.0","Accept":"text/html,application/xhtml+xml,application/json,text/plain;q=0.9,*/*;q=0.5","Range":"bytes=0-8191"},method="GET")
    try:
        with urllib.request.urlopen(req,timeout=timeout) as r:
            chunk=r.read(8192)
            return {"status":"BOUND","input_url":url,"final_url":r.geturl(),"http_status":getattr(r,"status",None),"content_type":r.headers.get("Content-Type",""),"bytes_observed":len(chunk)}
    except Exception as e:
        return {"status":"BINDING_FAILED","input_url":url,"error":f"{type(e).__name__}:{e}"}
