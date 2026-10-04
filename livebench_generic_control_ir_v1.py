#!/usr/bin/env python3
"""Generic fail-closed control-structure IR parser.

This module parses control syntax only. It never selects capabilities, never
executes actions, and never grants authority. Every leaf action remains an
opaque clause that a separate verified compiler must accept before lowering.
"""
from __future__ import annotations
import dataclasses,re
from typing import Any

SCHEMA="PROJECT_BRAIN_GENERIC_CONTROL_IR_V1"

class ControlParseError(ValueError):
    pass

@dataclasses.dataclass(frozen=True)
class Node:
    kind:str
    value:Any

def _norm(text:str)->str:
    return " ".join(str(text or "").strip().split())

def _split_otherwise(text:str)->tuple[str,str]|None:
    m=re.match(r"^if\s+(.+?),\s*(.+?)\s*,?\s*otherwise\s+(.+)$",_norm(text),re.I)
    if not m:
        return None
    cond,yes,no=(x.strip(" ,.;:") for x in m.groups())
    if not all((cond,yes,no)):
        return None
    return cond,yes,no

def _split_for_each(text:str)->tuple[str,str,str]|None:
    m=re.match(
        r"^(?:for\s+each|for\s+every)\s+([A-Za-z_][A-Za-z0-9_-]*)"
        r"(?:\s+in\s+(.+?))?,\s*(.+)$",
        _norm(text),re.I
    )
    if not m:
        return None
    var,source,body=m.groups()
    source=(source or "__RUNTIME_COLLECTION__").strip(" ,.;:")
    body=body.strip(" ,.;:")
    if not body:
        return None
    return var.lower(),source,body

def _split_repeat(text:str)->tuple[int,str]|None:
    patterns=(
        r"^repeat\s+(.+?)\s+(?:up\s+to|no\s+more\s+than)\s+(\d+)\s+times$",
        r"^(?:up\s+to|no\s+more\s+than)\s+(\d+)\s+times,\s*(.+)$",
    )
    t=_norm(text)
    m=re.match(patterns[0],t,re.I)
    if m:
        body,n=m.group(1),m.group(2)
    else:
        m=re.match(patterns[1],t,re.I)
        if not m:
            return None
        n,body=m.group(1),m.group(2)
    count=int(n)
    if count<1 or count>64:
        raise ControlParseError("REPEAT_BOUND_OUT_OF_RANGE")
    return count,body.strip(" ,.;:")

def parse(text:str,*,depth:int=0)->dict[str,Any]:
    if depth>8:
        raise ControlParseError("CONTROL_NESTING_LIMIT_EXCEEDED")
    t=_norm(text)
    if not t:
        raise ControlParseError("EMPTY_CONTROL_TEXT")

    loop=_split_for_each(t)
    if loop is not None:
        var,source,body=loop
        child=parse(body,depth=depth+1)
        return {
            "schema":SCHEMA,
            "kind":"FOR_EACH",
            "variable":var,
            "source":source,
            "body":child,
            "execution_authority":False,
        }

    branch=_split_otherwise(t)
    if branch is not None:
        cond,yes,no=branch
        return {
            "schema":SCHEMA,
            "kind":"IF_ELSE",
            "condition":{"kind":"OPAQUE_CONDITION","text":cond},
            "then":parse(yes,depth=depth+1),
            "else":parse(no,depth=depth+1),
            "execution_authority":False,
        }

    repeat=_split_repeat(t)
    if repeat is not None:
        count,body=repeat
        return {
            "schema":SCHEMA,
            "kind":"BOUNDED_REPEAT",
            "max_iterations":count,
            "body":parse(body,depth=depth+1),
            "execution_authority":False,
        }

    if re.match(r"^(?:if|otherwise|for\s+each|for\s+every|repeat\b|up\s+to\b|no\s+more\s+than\b)",t,re.I):
        raise ControlParseError("UNPARSED_CONTROL_SHAPE")

    return {
        "schema":SCHEMA,
        "kind":"LEAF",
        "text":t,
        "requires_independent_leaf_compilation":True,
        "execution_authority":False,
    }

def collect_leaves(node:dict[str,Any])->list[str]:
    kind=node.get("kind")
    if kind=="LEAF":
        return [str(node["text"])]
    if kind=="FOR_EACH" or kind=="BOUNDED_REPEAT":
        return collect_leaves(node["body"])
    if kind=="IF_ELSE":
        return collect_leaves(node["then"])+collect_leaves(node["else"])
    raise ControlParseError("UNKNOWN_NODE_KIND")

def validate_fail_closed(node:dict[str,Any])->bool:
    if node.get("execution_authority") is not False:
        return False
    leaves=collect_leaves(node)
    return bool(leaves) and all(isinstance(x,str) and bool(x.strip()) for x in leaves)
