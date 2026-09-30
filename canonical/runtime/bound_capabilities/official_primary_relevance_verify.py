#!/usr/bin/env python3
"""Fail-closed verification for official primary technical docs + direct relevance.

Claim scope is intentionally narrow:
- candidate retrieval provenance is live and verified;
- candidate host is independently authority-bound to an official website;
- the live page is first-party technical documentation/spec/reference material;
- the live page directly covers multiple salient concepts from the objective.

This does not verify general scholarly primary-source status or evidence sufficiency.
"""
from __future__ import annotations

import html
import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser

SCHEMA="PROJECT_BRAIN_OFFICIAL_PRIMARY_RELEVANCE_VERIFICATION_V1"
UA="ProjectBrain-OfficialPrimaryRelevance/1.0 (+zero-cost model-independent research)"

_STOP={
    "determine","whether","ordinary","materially","results","result","than","under",
    "use","using","authoritative","primary","technical","evidence","real","executable",
    "experiment","choose","justify","research","method","discover","verify","necessary",
    "source","tool","route","test","claim","identify","material","limitations","limitation",
    "independently","consequential","produce","decision","quality","answer","provenance",
    "according","official","page","document","documentation","website","site","from","into",
    "with","that","this","those","these","their","there","where","when","what","which","while",
    "have","has","had","will","would","could","should","more","less","same","every","needed",
    "needed","needed","needed","and","the","for","are","can","yield",
}
_TITLE_MARKERS={
    "documentation","reference","manual","specification","standard","standards",
    "guidelines","guide","api","library","technical",
}
_PATH_SEGMENTS={
    "docs","doc","documentation","reference","ref","manual","spec","specs",
    "standard","standards","tr","api","library",
}
_HOST_PREFIXES={"docs","doc","developer","developers","reference","standards","spec"}


class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts=[]
        self._skip=0
    def handle_starttag(self,tag,attrs):
        if tag.lower() in {"script","style","noscript","svg"}:
            self._skip+=1
    def handle_endtag(self,tag):
        if tag.lower() in {"script","style","noscript","svg"} and self._skip:
            self._skip-=1
    def handle_data(self,data):
        if not self._skip:
            self.parts.append(data)


def _safe_url(raw):
    try:
        u=urllib.parse.urlsplit(str(raw or "").strip())
    except Exception:
        return None
    if u.scheme not in {"http","https"} or not u.netloc:
        return None
    host=(u.hostname or "").lower().strip(".")
    if not host or host in {"localhost","127.0.0.1","::1"} or host.endswith((".local",".internal")):
        return None
    return urllib.parse.urlunsplit((u.scheme,u.netloc,u.path,u.query,""))


def _site_host(value):
    host=(value or "").lower().strip(".")
    return host[4:] if host.startswith("www.") else host


def _same_site(left,right):
    a=_site_host(left)
    b=_site_host(right)
    return bool(a and b and (a==b or a.endswith("."+b) or b.endswith("."+a)))


def _fetch_text(url,timeout=20):
    safe=_safe_url(url)
    if safe is None:
        raise ValueError("SAFE_PUBLIC_HTTP_URL_REQUIRED")
    req=urllib.request.Request(
        safe,
        headers={"User-Agent":UA,"Accept":"text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.1"},
    )
    with urllib.request.urlopen(req,timeout=max(2,min(int(timeout),30))) as r:
        raw=r.read(1_500_000)
        final=_safe_url(r.geturl())
        if final is None:
            raise ValueError("UNSAFE_FINAL_URL")
        ctype=str(r.headers.get("Content-Type") or "")
    low=ctype.lower()
    decoded=raw.decode("utf-8","replace")
    if "html" in low or "xhtml" in low:
        p=_Text()
        p.feed(decoded)
        text=" ".join(p.parts)
    elif low.startswith("text/") or not ctype:
        text=decoded
    else:
        raise ValueError("SUPPORTED_TEXT_DOCUMENT_REQUIRED")
    return {
        "url":safe,
        "final_url":final,
        "content_type":ctype,
        "text":" ".join(html.unescape(text).split())[:1_000_000],
    }


def _stem(token):
    t=token.lower().strip("._-")
    if t.startswith("summ"):
        return "sum"
    if t.startswith("numer"):
        return "numeric"
    if t.startswith("float"):
        return "float"
    if t.startswith("cancel"):
        return "cancel"
    if t in {"stability","stable"}:
        return "stable"
    if t.endswith("ies") and len(t)>5:
        t=t[:-3]+"y"
    elif t.endswith("ing") and len(t)>6:
        t=t[:-3]
    elif t.endswith("ed") and len(t)>5:
        t=t[:-2]
    elif t.endswith("s") and len(t)>5 and not t.endswith("ss"):
        t=t[:-1]
    return t


def _tokens(text):
    out=[]
    for raw in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]{2,}",str(text or "")):
        t=_stem(raw)
        if len(t)<3 or t in _STOP or t.isdigit():
            continue
        out.append(t)
    return out


def _salient(text):
    seen=[]
    for t in _tokens(text):
        if t not in seen:
            seen.append(t)
    return seen


def _technical_document_signal(url,title):
    u=urllib.parse.urlsplit(url)
    host=(u.hostname or "").lower()
    first=host.split(".",1)[0] if host else ""
    segments={x.lower() for x in u.path.split("/") if x}
    title_tokens=set(_tokens(title))
    signals=[]
    if first in _HOST_PREFIXES:
        signals.append("TECHNICAL_DOC_HOST_PREFIX")
    if segments.intersection(_PATH_SEGMENTS):
        signals.append("TECHNICAL_DOC_PATH")
    if title_tokens.intersection(_TITLE_MARKERS):
        signals.append("TECHNICAL_DOC_TITLE")
    return signals


def _relevance(objective,title,page_text):
    objective_tokens=_salient(objective)
    objective_set=set(objective_tokens)
    source_tokens=_tokens((title or "")+" "+(page_text or ""))
    source_set=set(source_tokens)
    matched=[x for x in objective_tokens if x in source_set]

    local_pairs=[]
    seen=set()
    window=8
    for i,left in enumerate(source_tokens):
        if left not in objective_set:
            continue
        for right in source_tokens[i+1:i+1+window]:
            if right not in objective_set or right==left:
                continue
            key=tuple(sorted((left,right)))
            if key in seen:
                continue
            seen.add(key)
            local_pairs.append([left,right])

    return {
        "salient_objective_terms":objective_tokens,
        "matched_salient_terms":matched,
        "matched_salient_count":len(matched),
        "matched_adjacent_concepts":local_pairs,
        "matched_adjacent_concept_count":len(local_pairs),
        "verified":len(matched)>=3 and len(local_pairs)>=1,
        "method":"DIRECT_NORMALIZED_TOKEN_COVERAGE_WITH_LOCAL_SOURCE_COOCCURRENCE",
    }


def _unverified(reason,**extra):
    out={
        "schema":SCHEMA,
        "status":"UNVERIFIED",
        "reason":reason,
        "primary_source_status":"UNVERIFIED",
        "relevance_status":"UNVERIFIED",
        "evidence_sufficiency_status":"UNVERIFIED",
        "model_dependency_count":0,
        "incremental_spend_usd":0,
    }
    out.update(extra)
    return out


def verify(objective,candidate,provenance,authority,fetch_text=None,timeout=20):
    objective=" ".join(str(objective or "").strip().split())
    if not objective:
        return _unverified("OBJECTIVE_REQUIRED")
    if not isinstance(candidate,dict):
        return _unverified("CANDIDATE_OBJECT_REQUIRED")
    url=_safe_url(candidate.get("url"))
    if url is None:
        return _unverified("SAFE_PUBLIC_HTTP_URL_REQUIRED")

    if not isinstance(provenance,dict) or provenance.get("status")!="RETRIEVAL_PROVENANCE_VERIFIED":
        return _unverified("LIVE_RETRIEVAL_PROVENANCE_REQUIRED")
    prov_final=_safe_url(provenance.get("final_url") or url)
    prov_host=(urllib.parse.urlsplit(prov_final or "").hostname or "").lower()
    if prov_final is None:
        return _unverified("SAFE_PROVENANCE_FINAL_URL_REQUIRED")

    if (
        not isinstance(authority,dict)
        or authority.get("status")!="AUTHORITY_IDENTITY_VERIFIED"
        or authority.get("authority_status")!="VERIFIED"
    ):
        return _unverified("VERIFIED_AUTHORITY_BINDING_REQUIRED")

    official_host=str(authority.get("official_host") or "").lower().strip(".")
    candidate_host=(urllib.parse.urlsplit(url).hostname or "").lower()
    authority_candidate=str(authority.get("candidate_host") or candidate_host).lower().strip(".")
    if not official_host or not _same_site(candidate_host,official_host) or not _same_site(authority_candidate,official_host):
        return _unverified("AUTHORITY_HOST_RELATION_MISMATCH")
    if not _same_site(prov_host,official_host):
        return _unverified("PROVENANCE_FINAL_HOST_OUTSIDE_AUTHORITY_SITE")

    fetcher=fetch_text or _fetch_text
    try:
        page=fetcher(prov_final,timeout)
    except Exception as exc:
        return _unverified("LIVE_TECHNICAL_DOCUMENT_FETCH_FAILED",error_class=type(exc).__name__,error=str(exc)[:300])
    if not isinstance(page,dict):
        return _unverified("LIVE_TECHNICAL_DOCUMENT_RESULT_INVALID")
    live_final=_safe_url(page.get("final_url") or prov_final)
    if live_final is None:
        return _unverified("SAFE_LIVE_FINAL_URL_REQUIRED")
    live_host=(urllib.parse.urlsplit(live_final).hostname or "").lower()
    if not _same_site(live_host,official_host):
        return _unverified("LIVE_DOCUMENT_REDIRECT_OUTSIDE_AUTHORITY_SITE")

    ctype=str(page.get("content_type") or "").lower()
    if ctype and not (ctype.startswith("text/") or "html" in ctype or "xhtml" in ctype):
        return _unverified("SUPPORTED_TEXT_DOCUMENT_REQUIRED")

    title=str(candidate.get("title") or "")
    signals=_technical_document_signal(live_final,title)
    if not signals:
        return _unverified(
            "OFFICIAL_PAGE_NOT_VERIFIED_AS_TECHNICAL_DOCUMENT",
            candidate_url=url,final_url=live_final,authority_host=official_host,
        )

    relevance=_relevance(objective,title,str(page.get("text") or ""))
    primary_status="VERIFIED_OFFICIAL_FIRST_PARTY_TECHNICAL_DOCUMENT"
    if not relevance["verified"]:
        return {
            "schema":SCHEMA,
            "status":"UNVERIFIED",
            "reason":"DIRECT_OBJECTIVE_RELEVANCE_NOT_VERIFIED",
            "candidate_url":url,
            "final_url":live_final,
            "authority_host":official_host,
            "technical_document_signals":signals,
            "primary_source_status":primary_status,
            "relevance_status":"UNVERIFIED",
            "relevance":relevance,
            "evidence_sufficiency_status":"UNVERIFIED",
            "model_dependency_count":0,
            "incremental_spend_usd":0,
        }

    return {
        "schema":SCHEMA,
        "status":"PRIMARY_RELEVANCE_VERIFIED",
        "verification_method":"AUTHORITY_BOUND_FIRST_PARTY_TECHNICAL_DOC_PLUS_DIRECT_OBJECTIVE_COVERAGE",
        "candidate_url":url,
        "final_url":live_final,
        "authority_host":official_host,
        "technical_document_signals":signals,
        "primary_source_status":primary_status,
        "primary_source_claim_scope":"FIRST_PARTY_TECHNICAL_DOCUMENT_FOR_THE_AUTHORITY_BOUND_ENTITY",
        "relevance_status":"VERIFIED_DIRECT_OBJECTIVE_COVERAGE",
        "relevance":relevance,
        "evidence_sufficiency_status":"UNVERIFIED",
        "evidence_sufficiency_claims_made":False,
        "model_dependency_count":0,
        "incremental_spend_usd":0,
    }
