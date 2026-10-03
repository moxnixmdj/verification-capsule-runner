"""Independent-verifier shim for the existing planner boundary only."""
import json
def _planner_post(prompt, timeout_s=20):
    raise RuntimeError("VERIFIER_MUST_PATCH_PLANNER")
def _extract_json_object(text):
    return json.loads(text)
