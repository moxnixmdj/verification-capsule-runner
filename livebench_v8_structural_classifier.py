from __future__ import annotations
import json,pathlib,re

CODE_RE=re.compile(r"^[A-Z][A-Z0-9_]{2,160}$")
SOURCE_LITERAL_RE=re.compile(r"""["']([A-Z][A-Z0-9_]{2,160})(?=[:"'])""")
GAP_CLASSES={"UNKNOWN","CONTROL_OR_FANOUT","CONTROL_FLOW","VERIFICATION","CAUSAL_COMPOSITION","CAPABILITY_CANDIDATE"}
POLICY_MARKERS=(
 "LIVEBENCH_POLICY_POST_PROMPT_CAPABILITY_ACQUISITION_FORBIDDEN",
 "LIVEBENCH_POLICY_POST_PROMPT_ACQUISITION_FORBIDDEN",
)
NETWORK_MARKER="LIVEBENCH_POLICY_EXTERNAL_NETWORK_FORBIDDEN"

def source_code_vocabulary(paths):
    out=set()
    for raw in paths:
        p=pathlib.Path(raw)
        if not p.is_file():
            continue
        text=p.read_text(encoding="utf-8")
        out.update(SOURCE_LITERAL_RE.findall(text))
    return frozenset(out)

def _outer_blocker(msg):
    if not msg.startswith("Blocker:"):
        return None,None
    tail=msg[len("Blocker:"):]
    code,sep,detail=tail.partition(":")
    return code,(detail if sep else "")

def _safe_json(detail):
    if not detail or not detail.lstrip().startswith("{"):
        return None
    try:
        obj=json.loads(detail)
    except Exception:
        return None
    return obj if isinstance(obj,dict) else None

def _nested_static_code(text,source_codes):
    if not isinstance(text,str):
        return None
    found=[]
    for m in re.finditer(r"([A-Z][A-Z0-9_]{2,160})(?=[:\"' ,}]|$)",text):
        code=m.group(1)
        if code in source_codes:
            found.append(code)
    return found[-1] if found else None

def classify_exception(exc,source_codes):
    typ=type(exc).__name__
    msg=str(exc)

    if NETWORK_MARKER in msg:
        return {"kind":"POLICY_BLOCK","code":"EXTERNAL_NETWORK_FORBIDDEN"}
    if any(marker in msg for marker in POLICY_MARKERS) or "LiveBenchPostPromptAcquisitionForbidden" in msg:
        return {"kind":"POLICY_BLOCK","code":"POST_PROMPT_ACQUISITION_FORBIDDEN"}

    if typ=="Root2InferenceBlocked":
        code,detail=_outer_blocker(msg)
        if code=="BOUND_CAPABILITY_GROUNDING_AVAILABLE_COMPOSITION_BLOCKED":
            obj=_safe_json(detail)
            nested=_nested_static_code((obj or {}).get("composition_error"),source_codes)
            if nested:
                return {"kind":"COMPOSITION_BLOCK","code":nested}
            return {"kind":"COMPOSITION_BLOCK","code":"NESTED_CODE_UNAVAILABLE"}
        if code=="GOAL_ARCHITECTURAL_GAP":
            obj=_safe_json(detail)
            gap=str((obj or {}).get("gap_class") or "UNKNOWN")
            if gap not in GAP_CLASSES:
                gap="UNKNOWN"
            return {"kind":"ARCHITECTURAL_GAP","code":gap}
        if code and CODE_RE.fullmatch(code) and code in source_codes:
            return {"kind":"STATIC_BLOCKER","code":code}
        if CODE_RE.fullmatch(msg or "") and msg in source_codes:
            return {"kind":"STATIC_ADAPTER_BLOCKER","code":msg}
        return {"kind":"UNCLASSIFIED_RUNTIME","code":"UNCLASSIFIED_ROOT2_INFERENCE"}

    return {"kind":"UNCLASSIFIED_RUNTIME","code":"UNCLASSIFIED_OUTER_EXCEPTION"}
