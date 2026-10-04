from __future__ import annotations
import json,pathlib,re

CODE_RE=re.compile(r"^[A-Z][A-Z0-9_]{2,160}$")
TYPE_RE=re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,80}$")
SOURCE_LITERAL_RE=re.compile(r"""["']([A-Z][A-Z0-9_]{2,160})(?=[:"'])""")
GAP_CLASSES=frozenset({"UNKNOWN","CONTROL_OR_FANOUT","CONTROL_FLOW","VERIFICATION","CAUSAL_COMPOSITION"})
POLICY_MARKERS=(
 "LIVEBENCH_POLICY_POST_PROMPT_CAPABILITY_ACQUISITION_FORBIDDEN",
 "LIVEBENCH_POLICY_EXTERNAL_NETWORK_FORBIDDEN",
 "LIVEBENCH_POLICY_POST_PROMPT_ACQUISITION_FORBIDDEN",
)
POLICY_CODES={
 "LIVEBENCH_POLICY_POST_PROMPT_CAPABILITY_ACQUISITION_FORBIDDEN":"POST_PROMPT_CAPABILITY_ACQUISITION_FORBIDDEN",
 "LIVEBENCH_POLICY_EXTERNAL_NETWORK_FORBIDDEN":"EXTERNAL_NETWORK_FORBIDDEN",
 "LIVEBENCH_POLICY_POST_PROMPT_ACQUISITION_FORBIDDEN":"POST_PROMPT_PACKAGE_ACQUISITION_FORBIDDEN",
}

def source_code_vocabulary(paths):
    out=set()
    for raw in paths:
        text=pathlib.Path(raw).read_text(encoding="utf-8")
        out.update(SOURCE_LITERAL_RE.findall(text))
    return frozenset(out)

def _policy(msg):
    for marker in POLICY_MARKERS:
        if marker in msg:
            return {"kind":"POLICY_BLOCK","code":POLICY_CODES[marker]}
    return None

def _safe_static_code(text,source_codes,fallback):
    code=str(text or "").split(":",1)[0]
    if CODE_RE.fullmatch(code or "") and code in source_codes:
        return code
    return fallback

def classify_exception(exc,source_codes):
    typ=type(exc).__name__
    msg=str(exc)
    pol=_policy(msg)
    if pol is not None and typ!="Root2InferenceBlocked":
        return pol
    if typ!="Root2InferenceBlocked":
        return {"kind":"UNCLASSIFIED_RUNTIME","code":"UNCLASSIFIED_OUTER_EXCEPTION"}

    if msg.startswith("Blocker:"):
        tail=msg[len("Blocker:"):]
        code,sep,detail=tail.partition(":")
        if not CODE_RE.fullmatch(code or "") or code not in source_codes:
            return {"kind":"UNCLASSIFIED_RUNTIME","code":"UNCLASSIFIED_BLOCKER"}

        if code=="BOUND_CAPABILITY_GROUNDING_AVAILABLE_COMPOSITION_BLOCKED" and sep:
            try:
                obj=json.loads(detail)
            except Exception:
                return {"kind":"COMPOSITION_BLOCK","code":"COMPOSITION_DETAIL_JSON_INVALID"}
            comp=str(obj.get("composition_error") or "")
            producer="GROUNDED_EXECUTABLE_COMPOSITION_FAILED:"
            verifier="GROUNDED_EXECUTABLE_COMPOSITION_VERIFY_FAILED:"
            if comp.startswith(producer):
                rest=comp[len(producer):]
                exc_type,sep2,reason=rest.partition(":")
                static=_safe_static_code(reason,source_codes,"PRODUCER_REASON_NOT_STATIC")
                if sep2 and static!="PRODUCER_REASON_NOT_STATIC":
                    return {"kind":"COMPOSITION_PRODUCER","code":static}
                if TYPE_RE.fullmatch(exc_type or ""):
                    return {"kind":"COMPOSITION_PRODUCER_EXCEPTION","code":exc_type.upper()}
                return {"kind":"COMPOSITION_BLOCK","code":"PRODUCER_EXCEPTION_UNCLASSIFIED"}
            if comp.startswith(verifier):
                reason=comp[len(verifier):]
                static=_safe_static_code(reason,source_codes,"VERIFIER_REASON_NOT_STATIC")
                return {"kind":"COMPOSITION_VERIFIER","code":static}
            return {"kind":"COMPOSITION_BLOCK","code":"COMPOSITION_OTHER"}

        if code=="GOAL_ARCHITECTURAL_GAP" and sep:
            try:
                obj=json.loads(detail)
            except Exception:
                return {"kind":"ARCHITECTURAL_GAP","code":"GAP_DETAIL_JSON_INVALID"}
            gap=str(obj.get("gap_class") or "UNKNOWN")
            return {"kind":"ARCHITECTURAL_GAP","code":gap if gap in GAP_CLASSES else "GAP_CLASS_INVALID"}

        return {"kind":"STATIC_BLOCKER","code":code}

    if CODE_RE.fullmatch(msg or "") and msg in source_codes:
        return {"kind":"STATIC_ADAPTER_BLOCKER","code":msg}
    pol=_policy(msg)
    if pol is not None:
        return pol
    return {"kind":"UNCLASSIFIED_RUNTIME","code":"UNCLASSIFIED_ROOT2_INFERENCE"}
