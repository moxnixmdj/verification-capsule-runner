#!/usr/bin/env python3
"""Model-independent source identity and narrow official-site authority verification.

Claims are intentionally separated:
- Crossref can verify bibliographic identity for a DOI record.
- Wikidata P856 can corroborate that a relevant entity declares a candidate host
  as its official website.
- Crossref registration alone is NOT research authority.
- Generic infrastructure hosts such as doi.org are NOT authority for the work.
- Neither identity nor official-site status proves primary evidence or evidence sufficiency.
"""
from __future__ import annotations

import hashlib
import json
import re
import urllib.parse
import urllib.request

SCHEMA="PROJECT_BRAIN_SOURCE_IDENTITY_AND_OFFICIAL_SITE_AUTHORITY_V2"
UA="ProjectBrain-SourceAuthorityVerify/2.0 (+zero-cost model-independent research)"
_GENERIC_WORDS={
    "the","a","an","and","or","of","to","for","in","on","with","using","use","from","by",
    "whether","determine","assess","evaluate","investigate","compare","quantify","estimate",
    "official","documentation","source","study","research","current","reported","between",
    "website","site","page","api","library","catalog",
}
_GENERIC_HOST_TOKENS={"www","docs","doc","api","developer","developers","help","support","home","web"}
_INFRASTRUCTURE_HOSTS={
    "doi.org","dx.doi.org","crossref.org","www.crossref.org","duckduckgo.com",
    "html.duckduckgo.com","google.com","www.google.com","bing.com","www.bing.com",
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

def _host_labels(host):
    host=(host or "").lower().split(":")[0].strip(".")
    labels=[]
    for part in host.split("."):
        part=re.sub(r"[^a-z0-9-]+"," ",part)
        for token in part.split():
            if len(token)>=3 and token not in _GENERIC_HOST_TOKENS and token not in labels:
                labels.append(token)
    return labels

def _norm_host(host):
    value=(host or "").lower().strip(".")
    if value.startswith("www."):
        value=value[4:]
    return value

def _same_site(host_a,host_b):
    a=_norm_host(host_a)
    b=_norm_host(host_b)
    return bool(a and b and (a==b or a.endswith("."+b) or b.endswith("."+a)))

def _relevance(objective,candidate):
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

def _crossref_identity(candidate,timeout):
    doi=_norm_doi(candidate.get("doi"))
    if not doi:
        return None
    endpoint="https://api.crossref.org/works/"+urllib.parse.quote(doi,safe="")
    data,final_url,status=_fetch_json(endpoint,timeout)
    msg=(data or {}).get("message") or {}
    observed=_norm_doi(msg.get("DOI"))
    if observed!=doi:
        return {
            "signal":"CROSSREF_BIBLIOGRAPHIC_IDENTITY",
            "identity_verified":False,
            "authority_verified":False,
            "reason":"DOI_MISMATCH",
            "doi":doi,
            "observed_doi":observed,
        }
    titles=msg.get("title") or []
    registered_title=_canon(titles[0] if titles else "")
    candidate_title=_canon(candidate.get("title"))
    registered_publisher=_canon(msg.get("publisher"))
    candidate_publisher=_canon(candidate.get("publisher"))
    title_match=(not candidate_title) or candidate_title.casefold()==registered_title.casefold()
    publisher_match=(not candidate_publisher) or candidate_publisher.casefold()==registered_publisher.casefold()
    verified=bool(title_match and publisher_match)
    return {
        "signal":"CROSSREF_BIBLIOGRAPHIC_IDENTITY",
        "identity_verified":verified,
        "authority_verified":False,
        "reason":"REGISTRY_BIBLIOGRAPHIC_IDENTITY_MATCH" if verified else "BIBLIOGRAPHIC_METADATA_MISMATCH",
        "doi":doi,
        "registered_title":registered_title,
        "registered_publisher":registered_publisher,
        "registered_type":msg.get("type"),
        "registry_endpoint":final_url,
        "http_status":status,
        "authority_scope":"NONE",
        "primary_evidence_status":"NOT_VERIFIED",
    }

def _wikidata_official_site_authority(candidate,objective,timeout):
    host=(candidate.get("host") or urllib.parse.urlsplit(candidate.get("url") or "").hostname or "").lower().strip(".")
    if _norm_host(host) in {_norm_host(x) for x in _INFRASTRUCTURE_HOSTS}:
        return {
            "signal":"WIKIDATA_P856_OFFICIAL_WEBSITE",
            "identity_verified":False,
            "authority_verified":False,
            "reason":"GENERIC_INFRASTRUCTURE_HOST_NOT_SOURCE_AUTHORITY",
            "candidate_host":host,
            "primary_evidence_status":"NOT_VERIFIED",
        }

    objective_tokens=_tokens(objective)
    host_tokens=_host_labels(host)
    title_tokens=_tokens(candidate.get("title"))
    queries=[]
    # Strongest first: objective terms that also occur in the candidate host.
    for token in objective_tokens:
        if token in host_tokens and token not in queries:
            queries.append(token)
    # Then title/objective overlap, followed by remaining objective terms.
    for token in title_tokens:
        if token in objective_tokens and token not in queries:
            queries.append(token)
    for token in objective_tokens:
        if token not in queries:
            queries.append(token)

    observations=[]
    for query in queries[:8]:
        endpoint="https://www.wikidata.org/w/api.php?"+urllib.parse.urlencode({
            "action":"wbsearchentities","search":query,"language":"en","format":"json","limit":5,
        })
        try:
            data,search_final,search_status=_fetch_json(endpoint,timeout)
        except Exception as exc:
            observations.append({"query":query,"error":type(exc).__name__+":"+str(exc)[:160]})
            continue
        for item in (data or {}).get("search") or []:
            qid=_canon(item.get("id"))
            if not re.fullmatch(r"Q[1-9][0-9]*",qid):
                continue
            # Entity relevance cannot be created merely by the search engine returning it.
            entity_text=" ".join([
                _canon(item.get("label")),
                _canon(item.get("description")),
                _canon(((item.get("match") or {}).get("text"))),
            ])
            entity_tokens=set(_tokens(entity_text))
            objective_set=set(objective_tokens)
            entity_overlap=sorted(entity_tokens & objective_set)
            host_query_match=query in host_tokens
            if not entity_overlap and not host_query_match:
                continue
            entity_url="https://www.wikidata.org/wiki/Special:EntityData/"+qid+".json"
            try:
                entity,entity_final,entity_status=_fetch_json(entity_url,timeout)
            except Exception as exc:
                observations.append({"query":query,"qid":qid,"error":type(exc).__name__+":"+str(exc)[:160]})
                continue
            ent=((entity or {}).get("entities") or {}).get(qid) or {}
            claims=(ent.get("claims") or {}).get("P856") or []
            official_urls=[]
            for claim in claims:
                try:
                    value=claim["mainsnak"]["datavalue"]["value"]
                except Exception:
                    continue
                safe=_safe_url(value)
                if safe:
                    official_urls.append(safe)
            for official_url in official_urls:
                official_host=(urllib.parse.urlsplit(official_url).hostname or "").lower()
                if _same_site(host,official_host):
                    return {
                        "signal":"WIKIDATA_P856_OFFICIAL_WEBSITE",
                        "identity_verified":True,
                        "authority_verified":True,
                        "reason":"RELEVANT_ENTITY_DECLARED_OFFICIAL_WEBSITE_MATCH",
                        "authority_scope":"ENTITY_OFFICIAL_WEBSITE_IDENTITY",
                        "qid":qid,
                        "entity_label":_canon(item.get("label")),
                        "entity_description":_canon(item.get("description")),
                        "entity_objective_overlap":entity_overlap,
                        "matched_query":query,
                        "candidate_host":host,
                        "official_url":official_url,
                        "registry_endpoint":entity_final,
                        "http_status":entity_status,
                        "primary_evidence_status":"NOT_VERIFIED",
                    }
        observations.append({"query":query,"search_endpoint":search_final,"http_status":search_status})
    return {
        "signal":"WIKIDATA_P856_OFFICIAL_WEBSITE",
        "identity_verified":False,
        "authority_verified":False,
        "reason":"NO_RELEVANT_ENTITY_OFFICIAL_WEBSITE_MATCH",
        "candidate_host":host,
        "queries":queries[:8],
        "observations":observations[:12],
        "primary_evidence_status":"NOT_VERIFIED",
    }

def verify_candidate(objective,candidate,timeout=20):
    if not isinstance(candidate,dict):
        raise ValueError("CANDIDATE_OBJECT_REQUIRED")
    url=_safe_url(candidate.get("url"))
    if url is None:
        return {"status":"REJECTED","reason":"INVALID_OR_UNSAFE_URL","candidate":candidate}
    normalized=dict(candidate)
    normalized["url"]=url
    normalized["host"]=(urllib.parse.urlsplit(url).hostname or "").lower()

    signals=[]
    crossref=_crossref_identity(normalized,timeout)
    if crossref is not None:
        signals.append(crossref)
    wikidata=_wikidata_official_site_authority(normalized,objective,timeout)
    signals.append(wikidata)

    relevance=_relevance(objective,normalized)
    identity_verified=any(s.get("identity_verified") is True for s in signals)
    authority_verified=any(s.get("authority_verified") is True for s in signals)
    if authority_verified and relevance["status"]=="OBJECTIVE_TERM_CORROBORATED":
        status="OFFICIAL_SOURCE_AUTHORITY_VERIFIED"
    elif identity_verified:
        status="SOURCE_IDENTITY_VERIFIED_AUTHORITY_UNRESOLVED"
    else:
        status="SOURCE_IDENTITY_AND_AUTHORITY_UNRESOLVED"

    return {
        "status":status,
        "candidate":normalized,
        "relevance":relevance,
        "signals":signals,
        "identity_verified":identity_verified,
        "authority_verified":authority_verified,
        "authority_scope":"ENTITY_OFFICIAL_WEBSITE_IDENTITY" if authority_verified else "NONE",
        "primary_evidence_status":"NOT_VERIFIED",
        "evidence_sufficiency_status":"NOT_VERIFIED",
    }

def verify_discovery(discovery,timeout=20,max_candidates=12):
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
                "status":"SOURCE_IDENTITY_AND_AUTHORITY_UNRESOLVED",
                "reason":type(exc).__name__+":"+str(exc)[:300],
                "candidate":candidate,
                "identity_verified":False,
                "authority_verified":False,
                "primary_evidence_status":"NOT_VERIFIED",
                "evidence_sufficiency_status":"NOT_VERIFIED",
            })
    authority=[r for r in results if r.get("status")=="OFFICIAL_SOURCE_AUTHORITY_VERIFIED"]
    identities=[r for r in results if r.get("identity_verified") is True]
    status=("OFFICIAL_SOURCE_AUTHORITY_CANDIDATES_AVAILABLE" if authority
            else "SOURCE_IDENTITIES_AVAILABLE_AUTHORITY_UNRESOLVED" if identities
            else "SOURCE_IDENTITY_AND_AUTHORITY_UNRESOLVED")
    return {
        "schema":SCHEMA,
        "status":status,
        "objective":objective,
        "objective_sha256":hashlib.sha256(objective.encode("utf-8")).hexdigest(),
        "candidate_count":len(candidates),
        "identity_verified_count":len(identities),
        "authority_verified_count":len(authority),
        "identity_verified_candidates":identities,
        "authority_verified_candidates":authority,
        "results":results,
        "authority_claim_scope":"ENTITY_OFFICIAL_WEBSITE_IDENTITY_ONLY",
        "crossref_authority_policy":"BIBLIOGRAPHIC_IDENTITY_ONLY_NEVER_AUTHORITY",
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
    raise SystemExit(0 if out["status"]!="SOURCE_IDENTITY_AND_AUTHORITY_UNRESOLVED" else 2)
