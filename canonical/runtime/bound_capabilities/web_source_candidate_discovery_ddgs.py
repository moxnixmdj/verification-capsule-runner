#!/usr/bin/env python3
"""Model-independent web source-candidate discovery.

This capability does not decide that a result is authoritative and does not
invent facts. It turns a broad research objective into bounded web-search
queries, preserves search provenance, normalizes/deduplicates returned URLs,
and exposes explicit authority *signals* for downstream verification.
"""
from __future__ import annotations

import ipaddress
import json
import pathlib
import re
import urllib.parse

SCHEMA = "PROJECT_BRAIN_WEB_SOURCE_CANDIDATE_DISCOVERY_V1"
MAX_OBJECTIVE_CHARS = 4000
MAX_RESULTS = 24

_STOP = {
    "a","an","and","are","as","at","be","between","by","can","could","did","do",
    "does","for","from","how","if","in","into","is","it","its","of","on","or",
    "that","the","their","then","there","these","this","to","under","use","using",
    "was","were","what","when","where","whether","which","while","with","would",
}
_OFFICIAL_TERMS = {
    "official","documentation","reference","specification","standard","standards",
    "manual","guide","api","technical","report","paper","publication",
}
_PATH_TERMS = (
    "/doc", "/docs", "/documentation", "/reference", "/spec", "/standard",
    "/manual", "/publication", "/report", "/research",
)


class SourceDiscoveryError(RuntimeError):
    pass


def _canonical(text: object) -> str:
    return " ".join(str(text or "").strip().split())


def _tokens(text: object) -> set[str]:
    return {
        t.lower()
        for t in re.findall(r"[A-Za-z0-9][A-Za-z0-9_.+-]*", str(text or ""))
        if len(t) >= 3 and t.lower() not in _STOP and not t.isdigit()
    }


def _safe_public_url(value: object) -> tuple[str, str] | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = urllib.parse.urlsplit(raw)
    except ValueError:
        return None
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        return None
    host = parsed.hostname.rstrip(".").lower()
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
        return None
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip is not None and (
        ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
        or ip.is_multicast or ip.is_unspecified
    ):
        return None
    clean = urllib.parse.urlunsplit(
        (parsed.scheme.lower(), parsed.netloc, parsed.path or "/", parsed.query, "")
    )
    return clean, host


def _authority_signals(host: str, url: str, title: str, body: str) -> list[str]:
    signals: list[str] = []
    if host.endswith(".gov") or ".gov." in host:
        signals.append("GOVERNMENT_DOMAIN")
    if host.endswith(".mil") or ".mil." in host:
        signals.append("MILITARY_DOMAIN")
    if host.endswith(".edu") or ".edu." in host or host.endswith(".ac.uk"):
        signals.append("ACADEMIC_DOMAIN")
    hay = f"{title} {body}".lower()
    if any(re.search(rf"\b{re.escape(term)}\b", hay) for term in _OFFICIAL_TERMS):
        signals.append("OFFICIAL_OR_TECHNICAL_TEXT_SIGNAL")
    low_path = urllib.parse.urlsplit(url).path.lower()
    if any(term in low_path for term in _PATH_TERMS):
        signals.append("DOCUMENTATION_OR_PUBLICATION_PATH_SIGNAL")
    return sorted(set(signals))


def _query_plan(objective: str) -> list[dict[str, str]]:
    return [
        {"kind": "OBJECTIVE_VERBATIM", "query": objective},
        {
            "kind": "OBJECTIVE_PLUS_PRIMARY_SOURCE_INTENT",
            "query": f"{objective} official primary source documentation",
        },
    ]


def discover(
    objective: object,
    *,
    max_results: int = 12,
    searcher=None,
) -> dict:
    text = _canonical(objective)
    if not text:
        raise SourceDiscoveryError("OBJECTIVE_REQUIRED")
    if len(text) > MAX_OBJECTIVE_CHARS:
        raise SourceDiscoveryError("OBJECTIVE_TOO_LONG")
    limit = max(1, min(int(max_results), MAX_RESULTS))
    objective_tokens = _tokens(text)

    if searcher is None:
        try:
            from ddgs import DDGS
        except Exception as exc:
            raise SourceDiscoveryError(
                "DDGS_DEPENDENCY_UNAVAILABLE:" + type(exc).__name__
            ) from exc

        engine = DDGS(timeout=10)

        def searcher(query: str, n: int):
            return engine.text(
                query,
                region="us-en",
                safesearch="moderate",
                max_results=n,
                backend="auto",
            )

    seen: dict[str, dict] = {}
    attempts: list[dict] = []
    per_query = max(5, min(limit, 12))

    for q in _query_plan(text):
        try:
            rows = list(searcher(q["query"], per_query) or [])
        except Exception as exc:
            attempts.append(
                {
                    "kind": q["kind"],
                    "query": q["query"],
                    "status": "ERROR",
                    "error": type(exc).__name__ + ":" + str(exc)[:500],
                }
            )
            continue
        attempts.append(
            {
                "kind": q["kind"],
                "query": q["query"],
                "status": "OK",
                "returned_count": len(rows),
            }
        )
        for source_rank, row in enumerate(rows, start=1):
            if not isinstance(row, dict):
                continue
            safe = _safe_public_url(row.get("href") or row.get("url"))
            if safe is None:
                continue
            url, host = safe
            title = _canonical(row.get("title"))
            body = _canonical(row.get("body") or row.get("snippet") or row.get("description"))
            result_tokens = _tokens(f"{title} {body} {host}")
            overlap = sorted(objective_tokens & result_tokens)
            overlap_ratio = (
                len(overlap) / max(1, len(objective_tokens))
                if objective_tokens else 0.0
            )
            signals = _authority_signals(host, url, title, body)
            quality_score = round(
                (4.0 * overlap_ratio)
                + (0.5 * len(signals))
                + (1.0 / max(1, source_rank)),
                6,
            )
            item = {
                "url": url,
                "host": host,
                "title": title,
                "snippet": body,
                "query_kind": q["kind"],
                "source_rank": source_rank,
                "objective_overlap_tokens": overlap,
                "objective_overlap_ratio": round(overlap_ratio, 6),
                "authority_signals": signals,
                "authority_status": "CANDIDATE_UNVERIFIED",
                "quality_score": quality_score,
            }
            prior = seen.get(url)
            if prior is None or item["quality_score"] > prior["quality_score"]:
                seen[url] = item

    candidates = sorted(
        seen.values(),
        key=lambda x: (-float(x["quality_score"]), x["host"], x["url"]),
    )[:limit]
    if not candidates:
        raise SourceDiscoveryError(
            "NO_SOURCE_CANDIDATES:" + json.dumps(attempts, sort_keys=True)[:2000]
        )
    return {
        "schema": SCHEMA,
        "status": "SOURCE_CANDIDATES_DISCOVERED",
        "objective": text,
        "query_plan": _query_plan(text),
        "attempts": attempts,
        "candidates": candidates,
        "candidate_count": len(candidates),
        "authority_claim_made": False,
        "invented_source_urls": [],
        "invented_facts": [],
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }


def run(args: dict, root: object) -> dict:
    if not isinstance(args, dict):
        raise SourceDiscoveryError("ARGS_INVALID")
    result = discover(
        args.get("objective") or args.get("goal") or args.get("query"),
        max_results=int(args.get("max_results") or 12),
    )
    output_path = args.get("output_path")
    if output_path:
        root = pathlib.Path(root).resolve()
        path = (root / str(output_path)).resolve()
        if path == root or root not in path.parents:
            raise SourceDiscoveryError("OUTPUT_PATH_OUTSIDE_REPOSITORY")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        result["output_path"] = str(path.relative_to(root)).replace("\\", "/")
        result["output_verified"] = True
    return result
