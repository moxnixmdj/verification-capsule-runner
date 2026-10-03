"""Fail-closed evidence omniretrieval planner.

Compiles one normalized proof obligation into independent discovery channels so
"no result" cannot be inferred from English keyword search alone.
Zero acceptance credit; discovery/scheduling only.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import re
from typing import Iterable, Sequence

CHANNELS = (
    "LEXICAL",
    "MULTILINGUAL_SEED",
    "INVARIANT",
    "STRUCTURAL_CODE",
    "HISTORY",
    "GRAPH",
    "ECOSYSTEM",
)

@dataclass(frozen=True)
class ProofObligation:
    obligation_id: str
    concepts: tuple[str, ...]
    aliases: tuple[str, ...] = ()
    numeric_anchors: tuple[str, ...] = ()
    identifiers: tuple[str, ...] = ()
    code_symbols: tuple[str, ...] = ()
    hashes: tuple[str, ...] = ()
    seed_repositories: tuple[str, ...] = ()
    authors: tuple[str, ...] = ()
    citations: tuple[str, ...] = ()

def _clean(xs: Iterable[str]) -> list[str]:
    out=[]
    for raw in xs:
        s=" ".join(str(raw or "").split())
        if s and s not in out:
            out.append(s)
    return out

def _numeric_variants(values: Iterable[str]) -> list[str]:
    out=[]
    for raw in _clean(values):
        vals=[raw]
        try:
            x=float(raw.rstrip("%"))
            if raw.endswith("%"):
                vals += [str(x/100.0)]
            elif 0 <= x <= 1:
                vals += [f"{x*100:g}%"]
            else:
                vals += [f"{x:g}"]
        except Exception:
            pass
        for v in vals:
            if v not in out:
                out.append(v)
    return out

def compile_channels(o: ProofObligation) -> dict:
    if not o.obligation_id or not _clean(o.concepts):
        return {"status":"FAIL_CLOSED","reason":"OBLIGATION_ID_AND_CONCEPT_REQUIRED"}

    concepts=_clean(o.concepts)
    aliases=_clean(o.aliases)
    identifiers=_clean(o.identifiers)
    symbols=_clean(o.code_symbols)
    hashes=_clean(o.hashes)
    numbers=_numeric_variants(o.numeric_anchors)
    seeds=_clean(o.seed_repositories)
    authors=_clean(o.authors)
    citations=_clean(o.citations)

    lexical=[]
    for x in concepts+aliases:
        lexical.append(f'"{x}"')

    multilingual=[]
    for x in aliases:
        if any(ord(ch) > 127 for ch in x):
            multilingual.append(x)

    invariant=identifiers+hashes+numbers
    structural=[]
    for s in symbols:
        structural += [s, f"symbol:{s}"]
    for ident in identifiers:
        if re.search(r"[A-Za-z_][A-Za-z0-9_\.:-]{2,}", ident):
            structural.append(ident)

    history=[]
    for seed in seeds:
        history += [
            f"repo:{seed} commits",
            f"repo:{seed} diffs",
            f"repo:{seed} tags releases deleted-files",
        ]

    graph=[]
    for seed in seeds:
        graph += [
            f"repo:{seed} forks",
            f"repo:{seed} dependencies dependents",
            f"repo:{seed} contributors related-repositories",
        ]
    graph += [f"author:{a}" for a in authors]
    graph += [f"citation:{c}" for c in citations]

    ecosystem=[]
    for ident in identifiers+concepts:
        ecosystem += [
            f"github:{ident}",
            f"huggingface:{ident}",
            f"pypi:{ident}",
            f"npm:{ident}",
            f"doi:{ident}",
            f"container:{ident}",
        ]

    payload={
        "LEXICAL":_clean(lexical),
        "MULTILINGUAL_SEED":_clean(multilingual),
        "INVARIANT":_clean(invariant),
        "STRUCTURAL_CODE":_clean(structural),
        "HISTORY":_clean(history),
        "GRAPH":_clean(graph),
        "ECOSYSTEM":_clean(ecosystem),
    }
    active=[k for k,v in payload.items() if v]

    # Lexical-only discovery is never sufficient for a saturation claim.
    nonlex=[k for k in active if k not in {"LEXICAL","MULTILINGUAL_SEED"}]
    return {
        "schema":"PROJECT_BRAIN_EVIDENCE_OMNIRETRIEVAL_PLAN_V1",
        "status":"COMPILED" if nonlex else "FAIL_CLOSED",
        "obligation_id":o.obligation_id,
        "channels":payload,
        "active_channels":active,
        "nonlexical_channel_count":len(nonlex),
        "lexical_only_saturation_forbidden":True,
        "terminal_authority":False,
        "acceptance_credit_delta":0,
    }

def saturation_verdict(plan: dict, rounds: Sequence[dict], *, required_zero_rounds: int=2) -> dict:
    if plan.get("status")!="COMPILED":
        return {"status":"FAIL_CLOSED","reason":"PLAN_NOT_COMPILED"}
    if required_zero_rounds < 1:
        return {"status":"FAIL_CLOSED","reason":"INVALID_ZERO_ROUND_REQUIREMENT"}
    active=set(plan.get("active_channels") or [])
    nonlex={x for x in active if x not in {"LEXICAL","MULTILINGUAL_SEED"}}
    if not nonlex:
        return {"status":"FAIL_CLOSED","reason":"NO_NONLEXICAL_CHANNEL"}

    consecutive={c:0 for c in active}
    observed={c:False for c in active}
    for r in rounds:
        c=r.get("channel")
        if c not in active:
            continue
        observed[c]=True
        n=r.get("new_acceptance_relevant_artifacts")
        if not isinstance(n,int) or isinstance(n,bool) or n<0:
            return {"status":"FAIL_CLOSED","reason":"INVALID_ROUND_COUNT"}
        consecutive[c]=consecutive[c]+1 if n==0 else 0

    missing=sorted(c for c in active if not observed[c])
    unsaturated=sorted(c for c in active if consecutive[c] < required_zero_rounds)
    ok=not missing and not unsaturated
    return {
        "schema":"PROJECT_BRAIN_EVIDENCE_OMNIRETRIEVAL_SATURATION_V1",
        "status":"ACCESSIBLE_SOURCE_FIXED_POINT" if ok else "OPEN",
        "missing_channels":missing,
        "unsaturated_channels":unsaturated,
        "required_consecutive_zero_rounds":required_zero_rounds,
        "claims_all_information_in_existense":False,
        "terminal_authority":False,
        "acceptance_credit_delta":0,
    }
