from __future__ import annotations
import pathlib,re

CODE_RE=re.compile(r"^[A-Z][A-Z0-9_]{2,120}$")
SOURCE_LITERAL_RE=re.compile(r"""["']([A-Z][A-Z0-9_]{2,120})(?=[:"'])""")
POLICY_MARKERS=(
 "LIVEBENCH_POLICY_POST_PROMPT_CAPABILITY_ACQUISITION_FORBIDDEN",
 "LIVEBENCH_POLICY_EXTERNAL_NETWORK_FORBIDDEN",
 "LIVEBENCH_POLICY_POST_PROMPT_ACQUISITION_FORBIDDEN",
)
def source_code_vocabulary(paths):
    out=set()
    for raw in paths:
        p=pathlib.Path(raw)
        text=p.read_text(encoding="utf-8")
        out.update(SOURCE_LITERAL_RE.findall(text))
    return frozenset(out)

def classify_exception(exc,source_codes):
    typ=type(exc).__name__
    msg=str(exc)
    # The adapter wraps frozen-runtime Blocker exceptions as
    # Root2InferenceBlocked("Blocker:<STATIC_CODE>:<case-specific detail>").
    if typ=="Root2InferenceBlocked":
        if msg.startswith("Blocker:"):
            tail=msg[len("Blocker:"):]
            code=tail.split(":",1)[0]
            if CODE_RE.fullmatch(code or "") and code in source_codes:
                return {"kind":"STATIC_BLOCKER","code":code}
            return {"kind":"UNCLASSIFIED_RUNTIME","code":"UNCLASSIFIED_BLOCKER"}
        # Adapter-owned fixed codes have no detail suffix.
        if CODE_RE.fullmatch(msg or "") and msg in source_codes:
            return {"kind":"STATIC_ADAPTER_BLOCKER","code":msg}
        # Policy exceptions are intentionally recognized by precommitted marker only.
        if any(marker in msg for marker in POLICY_MARKERS):
            return {"kind":"POLICY_BLOCK","code":"POST_PROMPT_ACQUISITION_OR_NETWORK_FORBIDDEN"}
        return {"kind":"UNCLASSIFIED_RUNTIME","code":"UNCLASSIFIED_ROOT2_INFERENCE"}
    if any(marker in msg for marker in POLICY_MARKERS):
        return {"kind":"POLICY_BLOCK","code":"POST_PROMPT_ACQUISITION_OR_NETWORK_FORBIDDEN"}
    return {"kind":"UNCLASSIFIED_RUNTIME","code":"UNCLASSIFIED_OUTER_EXCEPTION"}
