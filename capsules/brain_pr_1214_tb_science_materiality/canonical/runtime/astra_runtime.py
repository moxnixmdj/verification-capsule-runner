"""Independent-verifier shim for fixed planner proposal tests."""
import json
def _planner_post(prompt, timeout_s=20):
    raise RuntimeError("VERIFIER_MUST_PATCH_PLANNER")
def _extract_json_object(text):
    return json.loads(text)
