from __future__ import annotations

import json
import pathlib
import re

CODE_RE = re.compile(r"^[A-Z][A-Z0-9_]{2,160}$")
SOURCE_LITERAL_RE = re.compile(r"""["']([A-Z][A-Z0-9_]{2,160})(?=[:"'])""")
POLICY_MARKERS = (
    "LIVEBENCH_POLICY_POST_PROMPT_CAPABILITY_ACQUISITION_FORBIDDEN",
    "LIVEBENCH_POLICY_EXTERNAL_NETWORK_FORBIDDEN",
    "LIVEBENCH_POLICY_POST_PROMPT_ACQUISITION_FORBIDDEN",
)
OUTER_COMPOSITION = "BOUND_CAPABILITY_GROUNDING_AVAILABLE_COMPOSITION_BLOCKED"
ARCH_GAP = "GOAL_ARCHITECTURAL_GAP"


def source_code_vocabulary(paths):
    out = set(POLICY_MARKERS)
    for raw in paths:
        text = pathlib.Path(raw).read_text(encoding="utf-8")
        out.update(SOURCE_LITERAL_RE.findall(text))
    return frozenset(out)


def _safe_json_tail(tail: str):
    try:
        obj = json.loads(tail)
    except Exception:
        return None
    return obj if isinstance(obj, dict) else None


def _first_source_code(text: str, source_codes):
    for token in re.findall(r"[A-Z][A-Z0-9_]{2,160}", str(text or "")):
        if token in source_codes:
            return token
    return None


def classify_exception(exc, source_codes):
    typ = type(exc).__name__
    msg = str(exc)

    # Preserve exact precommitted policy class instead of collapsing all policy
    # failures into one bucket. No prompt/response text is emitted.
    for marker in POLICY_MARKERS:
        if marker in msg:
            return {"kind": "POLICY_BLOCK", "code": marker}

    if typ != "Root2InferenceBlocked":
        return {"kind": "UNCLASSIFIED_RUNTIME", "code": "UNCLASSIFIED_OUTER_EXCEPTION"}

    if not msg.startswith("Blocker:"):
        if CODE_RE.fullmatch(msg or "") and msg in source_codes:
            return {"kind": "STATIC_ADAPTER_BLOCKER", "code": msg}
        return {"kind": "UNCLASSIFIED_RUNTIME", "code": "UNCLASSIFIED_ROOT2_INFERENCE"}

    tail = msg[len("Blocker:"):]
    outer, sep, detail = tail.partition(":")
    if not CODE_RE.fullmatch(outer or "") or outer not in source_codes:
        return {"kind": "UNCLASSIFIED_RUNTIME", "code": "UNCLASSIFIED_BLOCKER"}

    # The V7 bucket proved local verified grounding existed. V8 exposes only
    # the nested static composition error code, validated against frozen source
    # vocabulary. It never emits the JSON detail, task, prompt, or response.
    if outer == OUTER_COMPOSITION and sep:
        obj = _safe_json_tail(detail)
        if obj is None:
            return {"kind": "UNCLASSIFIED_RUNTIME", "code": "COMPOSITION_DETAIL_INVALID"}
        nested = _first_source_code(obj.get("composition_error"), source_codes)
        if nested is None:
            return {"kind": "UNCLASSIFIED_RUNTIME", "code": "COMPOSITION_SUBCODE_UNCLASSIFIED"}
        return {"kind": "COMPOSITION_SUBBLOCKER", "code": nested}

    # GOAL_ARCHITECTURAL_GAP already records a finite architectural gap_class.
    # Emit that source-validated class only.
    if outer == ARCH_GAP and sep:
        obj = _safe_json_tail(detail)
        if obj is None:
            return {"kind": "UNCLASSIFIED_RUNTIME", "code": "ARCH_GAP_DETAIL_INVALID"}
        gap = str(obj.get("gap_class") or "")
        if CODE_RE.fullmatch(gap) and gap in source_codes:
            return {"kind": "ARCHITECTURAL_GAP", "code": gap}
        return {"kind": "UNCLASSIFIED_RUNTIME", "code": "ARCH_GAP_CLASS_UNCLASSIFIED"}

    return {"kind": "STATIC_BLOCKER", "code": outer}
