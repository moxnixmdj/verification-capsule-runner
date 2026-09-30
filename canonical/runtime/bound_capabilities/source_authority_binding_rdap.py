#!/usr/bin/env python3
"""Fail-closed model-independent source authority binding via public RDAP.

Given a provenance-verified candidate host plus a claimed issuing/source entity,
verify only the narrow relation that public domain-registration data binds the
registered domain to that entity. This does NOT establish primary-source status,
factual authority for a claim, relevance, or evidence sufficiency.
"""
from __future__ import annotations
import json
import pathlib
import re
import urllib.parse
import urllib.request

SCHEMA="PROJECT_BRAIN_SOURCE_AUTHORITY_BINDING_V1"
UA="ProjectBrain-AuthorityBinding/1.0 (+zero-cost model-independent research)"
LEGAL={"inc","incorporated","llc","ltd","limited","corp","corporation","company","co","gmbh","plc"}

def _safe_host(raw):
    text=str(raw or "").strip()
    if "://" in text:
        try:
            host=(urllib.parse.urlsplit(text).hostname or "").lower().strip(".")
        except Exception:
            return None
    else:
        host=text.lower().strip(".")
    if (not host or host in {"localhost","127.0.0.1","::1"}
        or host.endswith((".local",".internal")) or "." not in host):
        return None
    if not re.fullmatch(r"[a-z0-9.-]+",host):
        return None
    return host

def _candidate_host(candidate):
    c=dict(candidate or {})
    for key in ("final_host","final_url","candidate_url","url"):
        host=_safe_host(c.get(key))
        if host:
            return host
    return None

def _domain_candidates(host):
    parts=str(host or "").split(".")
    out=[]
    for i in range(0,max(0,len(parts)-1)):
        d=".".join(parts[i:])
        if d.count(".")>=1 and d not in out:
            out.append(d)
    return out

def _fetch_rdap(domain,timeout):
    url="https://rdap.org/domain/"+urllib.parse.quote(domain,safe="")
    req=urllib.request.Request(url,headers={
        "User-Agent":UA,
        "Accept":"application/rdap+json,application/json;q=0.9,*/*;q=0.1",
    })
    with urllib.request.urlopen(req,timeout=timeout) as r:
        raw=r.read(2_000_000)
        return json.loads(raw.decode("utf-8","replace")),r.geturl(),int(getattr(r,"status",200))

def _vcard_names(entity):
    out=[]
    vc=(entity or {}).get("vcardArray")
    if not (isinstance(vc,list) and len(vc)==2 and isinstance(vc[1],list)):
        return out
    for item in vc[1]:
        if not (isinstance(item,list) and len(item)>=4):
            continue
        if str(item[0]).lower() not in {"fn","org"}:
            continue
        value=item[3]
        if isinstance(value,list):
            value=" ".join(str(x) for x in value)
        value=" ".join(str(value or "").split())
        if value:
            out.append(value)
    return out

def _registrant_names(record):
    names=[]
    for entity in (record or {}).get("entities") or []:
        roles={str(x).lower() for x in (entity or {}).get("roles") or []}
        if "registrant" in roles:
            names.extend(_vcard_names(entity))
    # Some registries nest contact entities.
    for entity in (record or {}).get("entities") or []:
        for nested in (entity or {}).get("entities") or []:
            roles={str(x).lower() for x in (nested or {}).get("roles") or []}
            if "registrant" in roles:
                names.extend(_vcard_names(nested))
    return list(dict.fromkeys(names))

def _tokens(text):
    toks=re.findall(r"[a-z0-9]+",str(text or "").lower())
    return [t for t in toks if t not in LEGAL]

def _entity_match(claimed,observed):
    a=_tokens(claimed); b=_tokens(observed)
    if not a or not b:
        return False
    sa,sb=set(a),set(b)
    if sa==sb:
        return True
    inter=len(sa&sb); union=len(sa|sb)
    return inter>=2 and inter/union>=0.8 and (sa<=sb or sb<=sa)

def verify(candidate,claimed_entity,timeout=15):
    host=_candidate_host(candidate)
    claimed=" ".join(str(claimed_entity or "").split())
    base={
      "schema":SCHEMA,
      "candidate_host":host,
      "claimed_entity":claimed or None,
      "authority_status":"UNVERIFIED",
      "primary_source_status":"UNVERIFIED",
      "relevance_status":"UNVERIFIED",
      "evidence_sufficiency_status":"UNVERIFIED",
      "model_dependency_count":0,
      "incremental_spend_usd":0,
    }
    if not host:
        return {**base,"status":"UNVERIFIED","reason":"SAFE_PUBLIC_CANDIDATE_HOST_REQUIRED"}
    if not claimed:
        return {**base,"status":"UNVERIFIED","reason":"CLAIMED_SOURCE_ENTITY_REQUIRED"}
    timeout=max(2,min(int(timeout),30))
    errors=[]
    for domain in _domain_candidates(host):
        try:
            record,final_url,http_status=_fetch_rdap(domain,timeout)
        except Exception as exc:
            errors.append({"domain":domain,"error_class":type(exc).__name__})
            continue
        names=_registrant_names(record)
        matches=[name for name in names if _entity_match(claimed,name)]
        if matches:
            return {
              **base,
              "status":"AUTHORITY_BINDING_VERIFIED",
              "verification_method":"PUBLIC_RDAP_REGISTRANT_BINDING",
              "authority_status":"VERIFIED_HOST_TO_ISSUING_ENTITY_BINDING",
              "registered_domain":str(record.get("ldhName") or domain).lower(),
              "rdap_endpoint":"https://rdap.org/domain/{domain}",
              "rdap_final_url":final_url,
              "http_status":http_status,
              "matched_registrant":matches[0],
              "registrant_names":names,
            }
        # A successful public record with registrant data that does not match is
        # decisive for this domain; do not strip farther and accidentally match
        # a parent zone.
        if names:
            return {
              **base,
              "status":"UNVERIFIED",
              "reason":"RDAP_REGISTRANT_ENTITY_MISMATCH",
              "registered_domain":str(record.get("ldhName") or domain).lower(),
              "rdap_final_url":final_url,
              "registrant_names":names,
            }
    return {**base,"status":"UNVERIFIED","reason":"PUBLIC_RDAP_REGISTRANT_IDENTITY_UNAVAILABLE","rdap_errors":errors}

def _safe_path(root,raw):
    root=pathlib.Path(root).resolve()
    p=(root/str(raw or "")).resolve()
    if p!=root and root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return p

def run(args,root):
    inp=_safe_path(root,args.get("input_path"))
    out=_safe_path(root,args.get("output_path"))
    if not inp.is_file():
        raise RuntimeError("AUTHORITY_BINDING_INPUT_MISSING")
    data=json.loads(inp.read_text(encoding="utf-8"))
    result=verify(data.get("candidate") or data,data.get("claimed_entity"),args.get("timeout_s",15))
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return {
      **result,
      "output_path":str(out.relative_to(pathlib.Path(root).resolve())),
      "output_verified":result.get("status")=="AUTHORITY_BINDING_VERIFIED",
    }
