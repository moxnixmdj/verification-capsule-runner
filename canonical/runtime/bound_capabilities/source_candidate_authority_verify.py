#!/usr/bin/env python3
"""Model-independent source-candidate authority-identity verification.

This verifier makes deliberately narrow claims:
- Crossref can verify that a DOI candidate is registered with matching bibliographic identity.
- Wikidata P856 can independently corroborate that a web host is an entity's declared official website.
- Neither route proves that a source contains sufficient evidence for the research objective.
- Neither route, by itself, proves that a scholarly work is primary research.

No model cognition, source whitelist, or task-specific literals are used.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import urllib.parse
import urllib.request

SCHEMA="PROJECT_BRAIN_SOURCE_CANDIDATE_AUTHORITY_IDENTITY_V1"
UA="ProjectBrain-SourceAuthorityVerify/1.0 (+zero-cost model-independent research)"
_GENERIC_HOST_TOKENS={"www","docs","doc","api","developer","developers","help","support","home","web"}
_GENERIC_WORDS={
    "the","a","an","and","or","of","to","for","in","on","with","using","use","from","by",
    "whether","determine","assess","evaluate","investigate","compare","quantify","estimate",
    "official","documentation","source","study","research","current","reported","between",
}

def _canon(value):
    return " ".join(str(value or "").strip().split())

def _safe_url(raw):
    try:
        u=urllib.parse.urlsplit(str(raw or "").strip())
    except Exception:
        return None
    if u.scheme not in ("http","https") or not u.netloc:
        return None
    host=(u.hostname or "").lower().strip(".")
    if not host or host in {"localhost","127.0.0.1","::1"} or host.endswith((".local",".internal")):
        return None
    return urllib.parse.urlunsplit((u.scheme,u.netloc,u.path,u.query,""))

def _fetch_json(url, timeout=20, max_bytes=2_500_000):
    safe=_safe_url(url)
    if safe is None:
        raise ValueError("UNSAFE_URL")
    req=urllib.request.Request(safe,headers={"User-Agent":UA,"Accept":"application/json,*/*;q=0.1"})
    with urllib.request.urlopen(req,timeout=max(2,min(int(timeout),30))) as r:
        raw=r.read(max_bytes)
        final=_safe_url(r.geturl())
        if final is None:
            raise ValueError("UNSAFE_FINAL_URL")
        return json.loads(raw.decode("utf-8","replace")), final, int(getattr(r,"status",200))

def _tokens(text):
    out=[]
    for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9.+#_-]{2,}",_canon(text).lower()):
        token=token.strip("._-")
        if len(token)<3 or token in _GENERIC_WORDS:
            continue
        if token not in out:
            out.append(token)
    return out

def _relevance(objective, candidate):
    obj=set(_tokens(objective))
    cand=set(_tokens(" ".join([
        _canon(candidate.get("title")),
        _canon(candidate.get("publisher")),
        _canon(candidate.get("host")),
        _canon(candidate.get("doi")),
    ])))
    common=sorted(obj & cand)
    return {
        "status":"OBJECTIVE_TERM_CORROBORATED" if common else "UNRESOLVED",
        "matched_terms":common[:16],
        "objective_token_count":len(obj),
    }

def _norm_doi(raw):
    value=_canon(raw).lower()
    for prefix in ("https://doi.org/","http://doi.org/","doi:"):
        if value.startswith(prefix):
            value=value[len(prefix):]
    return value.strip()

def _crossref_verify(candidate, timeout):
    doi=_norm_doi(candidate.get("doi"))
    if not doi:
        return None
    endpoint="https://api.crossref.org/works/"+urllib.parse.quote(doi,safe="")
    data, final_url, status=_fetch_json(endpoint,timeout)
    msg=(data or {}).get("message") or {}
    observed=_norm_doi(msg.get("DOI"))
    if observed!=doi:
        return {
            "signal":"CROSSREF_REGISTRY",
            "verified":False,
            "reason":"DOI_MISMATCH",
            "doi":doi,
            "observed_doi":observed,
        }
    titles=msg.get("title") or []
    reg_title=_canon(titles[0] if titles else "")
    cand_title=_canon(candidate.get("title"))
    reg_pub=_canon(msg.get("publisher"))
    cand_pub=_canon(candidate.get("publisher"))
    title_match=(not cand_title) or (cand_title.casefold()==reg_title.casefold())
    publisher_match=(not cand_pub) or (cand_pub.casefold()==reg_pub.casefold())
    return {
        "signal":"CROSSREF_REGISTRY",
        "verified":bool(title_match and publisher_match),
        "reason":"REGISTRY_BIBLIOGRAPHIC_IDENTITY_MATCH" if title_match and publisher_match else "BIBLIOGRAPHIC_METADATA_MISMATCH",
        "doi":doi,
        "registered_title":reg_title,
        "registered_publisher":reg_pub,
        "registered_type":msg.get("type"),
        "registry_endpoint":final_url,
        "http_status":status,
        "primary_evidence_status":"NOT_VERIFIED",
    }

def _host_labels(host):
    host=(host or "").lower().split(":")[0].strip(".")
    labels=[]
    for part in host.split("."):
        part=re.sub(r"[^a-z0-9-]+"," ",part)
        for token in part.split():
            if len(token)>=3 and token not in _GENERIC_HOST_TOKENS and token not in labels:
                labels.append(token)
    return labels

def _same_site(host_a,host_b):
    a=(host_a or "").lower().strip(".")
    b=(host_b or "").lower().strip(".")
    return bool(a and b and (a==b or a.endswith("."+b) or b.endswith("."+a)))

def _wikidata_official_site_verify(candidate, objective, timeout):
    host=(candidate.get("host") or urllib.parse.urlsplit(candidate.get("url") or "").hostname or "").lower()
    labels=_host_labels(host)
    title_tokens=_tokens(candidate.get("title"))[:4]
    objective_tokens=_tokens(objective)[:8]
    queries=[]
    for token in labels+title_tokens+objective_tokens:
        if token not in queries:
            queries.append(token)
    observations=[]
    for query in queries[:8]:
        endpoint="https://www.wikidata.org/w/api.php?"+urllib.parse.urlencode({
            "action":"wbsearchentities","search":query,"language":"en","format":"json","limit":5,
        })
        try:
            data, final_url, status=_fetch_json(endpoint,timeout)
        except Exception as exc:
            observations.append({"query":query,"error":type(exc).__name__+":"+str(exc)[:160]})
            continue
        for item in (data or {}).get("search") or []:
            qid=_canon(item.get("id"))
            if not re.fullmatch(r"Q[1-9][0-9]*",qid):
                continue
            entity_url="https://www.wikidata.org/wiki/Special:EntityData/"+qid+".json"
            try:
                entity, entity_final, entity_status=_fetch_json(entity_url,timeout)
            except Exception as exc:
                observations.append({"query":query,"qid":qid,"error":type(exc).__name__+":"+str(exc)[:160]})
                continue
            ent=((entity or {}).get("entities") or {}).get(qid) or {}
            claims=(ent.get("claims") or {}).get("P856") or []
            official=[]
            for claim in claims:
                try:
                    value=claim["mainsnak"]["datavalue"]["value"]
                except Exception:
                    continue
                safe=_safe_url(value)
                if safe:
                    official.append(safe)
            for official_url in official:
                official_host=(urllib.parse.urlsplit(official_url).hostname or "").lower()
                if _same_site(host,official_host):
                    return {
                        "signal":"WIKIDATA_P856_OFFICIAL_WEBSITE",
                        "verified":True,
                        "reason":"CANDIDATE_HOST_MATCHES_DECLARED_OFFICIAL_WEBSITE",
                        "qid":qid,
                        "entity_label":_canon(item.get("label")),
                        "matched_query":query,
                        "candidate_host":host,
                        "official_url":official_url,
                        "registry_endpoint":entity_final,
                        "http_status":entity_status,
                        "primary_evidence_status":"NOT_VERIFIED",
                    }
        observations.append({"query":query,"search_endpoint":final_url,"http_status":status})
    return {
        "signal":"WIKIDATA_P856_OFFICIAL_WEBSITE",
        "verified":False,
        "reason":"NO_MATCHING_OFFICIAL_WEBSITE_IDENTITY",
        "candidate_host":host,
        "queries":queries[:8],
        "observations":observations[:12],
        "primary_evidence_status":"NOT_VERIFIED",
    }

def verify_candidate(objective, candidate, timeout=20):
    if not isinstance(candidate,dict):
        raise ValueError("CANDIDATE_OBJECT_REQUIRED")
    url=_safe_url(candidate.get("url"))
    if url is None:
        return {"status":"REJECTED","reason":"INVALID_OR_UNSAFE_URL","candidate":candidate}
    normalized=dict(candidate)
    normalized["url"]=url
    normalized["host"]=(urllib.parse.urlsplit(url).hostname or "").lower()
    signals=[]
    crossref=_crossref_verify(normalized,timeout)
    if crossref is not None:
        signals.append(crossref)
    wikidata=_wikidata_official_site_verify(normalized,objective,timeout)
    signals.append(wikidata)
    relevance=_relevance(objective,normalized)
    verified=[x for x in signals if x.get("verified") is True]
    if verified and relevance["status"]=="OBJECTIVE_TERM_CORROBORATED":
        status="AUTHORITY_IDENTITY_CANDIDATE_VERIFIED"
    elif verified:
        status="SOURCE_IDENTITY_VERIFIED_RELEVANCE_UNRESOLVED"
    else:
        status="AUTHORITY_IDENTITY_UNRESOLVED"
    return {
        "status":status,
        "candidate":normalized,
        "relevance":relevance,
        "authority_identity_signals":signals,
        "authority_identity_verified":bool(verified),
        "primary_evidence_status":"NOT_VERIFIED",
        "evidence_sufficiency_status":"NOT_VERIFIED",
    }

def verify_discovery(discovery, timeout=20, max_candidates=12):
    if not isinstance(discovery,dict):
        raise ValueError("DISCOVERY_OBJECT_REQUIRED")
    objective=_canon(discovery.get("objective") or discovery.get("query"))
    if not objective:
        raise ValueError("OBJECTIVE_REQUIRED")
    candidates=discovery.get("candidates") or []
    if not isinstance(candidates,list):
        raise ValueError("CANDIDATES_LIST_REQUIRED")
    results=[]
    for candidate in candidates[:max(1,min(int(max_candidates),20))]:
        try:
            results.append(verify_candidate(objective,candidate,timeout=timeout))
        except Exception as exc:
            results.append({
                "status":"AUTHORITY_IDENTITY_UNRESOLVED",
                "reason":type(exc).__name__+":"+str(exc)[:300],
                "candidate":candidate,
                "authority_identity_verified":False,
                "primary_evidence_status":"NOT_VERIFIED",
                "evidence_sufficiency_status":"NOT_VERIFIED",
            })
    admitted=[r for r in results if r.get("status")=="AUTHORITY_IDENTITY_CANDIDATE_VERIFIED"]
    return {
        "schema":SCHEMA,
        "status":"AUTHORITY_IDENTITY_CANDIDATES_AVAILABLE" if admitted else "AUTHORITY_IDENTITY_UNRESOLVED",
        "objective":objective,
        "objective_sha256":hashlib.sha256(objective.encode("utf-8")).hexdigest(),
        "candidate_count":len(candidates),
        "verified_candidate_count":len(admitted),
        "verified_candidates":admitted,
        "results":results,
        "authority_claim_scope":"IDENTITY_AND_REGISTRY_SIGNAL_ONLY",
        "primary_evidence_verification":"NOT_PERFORMED",
        "evidence_sufficiency_verification":"NOT_PERFORMED",
        "model_dependency_count":0,
        "incremental_spend_usd":0,
    }

if __name__=="__main__":
    import pathlib,sys
    if len(sys.argv)!=2:
        raise SystemExit("usage: source_candidate_authority_verify.py DISCOVERY.json")
    discovery=json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
    out=verify_discovery(discovery)
    print(json.dumps(out,indent=2,sort_keys=True))
    raise SystemExit(0 if out["status"]=="AUTHORITY_IDENTITY_CANDIDATES_AVAILABLE" else 2)
