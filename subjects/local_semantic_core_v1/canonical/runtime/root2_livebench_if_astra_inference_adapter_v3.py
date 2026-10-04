"""Verification-only API-compatible V3 fallback stub.

This is NOT a Brain subject. It exists only to load and exercise the exact V4
subject without importing the full historical Astra runtime closure.
"""
from __future__ import annotations
from collections.abc import Mapping
from types import SimpleNamespace

class Root2InferenceBlocked(RuntimeError):
    pass

BENCHMARK_ID = "LIVEBENCH_IF_2026_06_25"

def _instruction(request):
    if not isinstance(request, Mapping):
        raise Root2InferenceBlocked("REQUEST_MAPPING_REQUIRED")
    if str(request.get("benchmark_id") or "") != BENCHMARK_ID:
        raise Root2InferenceBlocked("BENCHMARK_ID_MISMATCH")
    allowed = request.get("allowed_tools")
    if allowed not in (None, [], ()):
        raise Root2InferenceBlocked("LIVEBENCH_IF_EXTERNAL_TOOLS_FORBIDDEN")
    payload = request.get("task_payload")
    if isinstance(payload, str):
        instruction = payload
    elif isinstance(payload, Mapping):
        instruction = payload.get("instruction") or payload.get("prompt") or payload.get("text")
    else:
        instruction = None
    instruction = str(instruction or "").strip()
    if not instruction:
        raise Root2InferenceBlocked("INSTRUCTION_REQUIRED")
    return instruction

fallback_v2 = SimpleNamespace(_instruction=_instruction)

def infer(request):
    _instruction(request)
    return {"status": "FALLBACK_V3"}
