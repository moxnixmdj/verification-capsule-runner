#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
import py_compile
import subprocess
import tempfile
import urllib.request

ENDPOINT = os.environ.get("SERA_ENDPOINT", "http://127.0.0.1:8080/v1/chat/completions")
MODEL = os.environ.get("SERA_MODEL", "SERA-8B-Q4_K_M.gguf")
SEED = int(os.environ.get("SERA_SEED", "424242"))

CASES = [
    {
        "id": "unwrap-proof-bearing-wrapper",
        "source": '''from __future__ import annotations

def adapt(request):
    return None
''',
        "tests": '''import unittest
import candidate_adapter as m

class T(unittest.TestCase):
    def test_adapts_exact_wrapper(self):
        req = {
            "kind": "SUCCESS_TO_CANONICAL_EPISODE_CANDIDATE",
            "wrapper": {
                "problem": {"task_id": "t", "target_effects": ["done"]},
                "episode": {"verified_facts": ["done"]},
                "proof_capsule_sha256": "a" * 64,
            },
        }
        out = m.adapt(req)
        self.assertIsInstance(out, dict)
        self.assertEqual(out["problem"], req["wrapper"]["problem"])
        self.assertEqual(out["episode"], req["wrapper"]["episode"])
        self.assertEqual(out["proof_capsule_sha256"], "a" * 64)
        self.assertTrue(out["candidate_only"])
        self.assertFalse(out["verification_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_rejects_wrong_kind(self):
        self.assertIsNone(m.adapt({"kind": "OTHER", "wrapper": {}}))

if __name__ == "__main__":
    unittest.main()
''',
    },
    {
        "id": "normalize-nested-result",
        "source": '''from __future__ import annotations

def adapt(request):
    if request.get("kind") != "SUCCESS_TO_CANONICAL_EPISODE_CANDIDATE":
        return None
    return None
''',
        "tests": '''import unittest
import candidate_adapter as m

class T(unittest.TestCase):
    def test_normalizes_nested_result(self):
        req = {
            "kind": "SUCCESS_TO_CANONICAL_EPISODE_CANDIDATE",
            "observation": {
                "result": {
                    "problem": {"task_id": "x", "initial_facts": ["seed"], "target_effects": ["done"]},
                    "episode": {"verified_facts": ["seed", "done"]},
                }
            },
        }
        out = m.adapt(req)
        self.assertEqual(out["problem"], req["observation"]["result"]["problem"])
        self.assertEqual(out["episode"], req["observation"]["result"]["episode"])
        self.assertTrue(out["candidate_only"])
        self.assertFalse(out["verification_authority"])
        self.assertFalse(out["promotion_authority"])

    def test_no_candidate_when_material_missing(self):
        req = {"kind": "SUCCESS_TO_CANONICAL_EPISODE_CANDIDATE", "observation": {"result": {}}}
        self.assertIsNone(m.adapt(req))

if __name__ == "__main__":
    unittest.main()
''',
    },
    {
        "id": "preserve-authority-firewall",
        "source": '''from __future__ import annotations

def adapt(request):
    payload = request.get("payload")
    if not isinstance(payload, dict):
        return None
    return {"problem": payload.get("problem"), "episode": payload.get("episode")}
''',
        "tests": '''import unittest
import candidate_adapter as m

class T(unittest.TestCase):
    def test_candidate_is_non_authoritative(self):
        req = {
            "payload": {
                "problem": {"task_id": "y", "target_effects": ["done"]},
                "episode": {"verified_facts": ["done"]},
            }
        }
        out = m.adapt(req)
        self.assertEqual(out["problem"], req["payload"]["problem"])
        self.assertEqual(out["episode"], req["payload"]["episode"])
        self.assertTrue(out["candidate_only"])
        for key in ("verification_authority", "promotion_authority", "acceptance_authority", "terminal_authority"):
            self.assertIs(out[key], False)

    def test_input_cannot_escalate_authority(self):
        req = {
            "payload": {
                "problem": {"task_id": "y", "target_effects": ["done"]},
                "episode": {"verified_facts": ["done"]},
            },
            "verification_authority": True,
            "promotion_authority": True,
        }
        out = m.adapt(req)
        self.assertFalse(out["verification_authority"])
        self.assertFalse(out["promotion_authority"])

if __name__ == "__main__":
    unittest.main()
''',
    },
]

SYSTEM = """You are a constrained source-patch candidate generator.
Return only one JSON object with exactly two keys: "path" and "content".
"path" must equal "candidate_adapter.py".
"content" must be the complete replacement Python source.
Do not emit markdown or explanations.
Do not create or modify verifier, checkpoint, test, workflow, governance, or other files.
The candidate must not claim verification, promotion, acceptance, or terminal authority.
Solve only the supplied failing adapter task.
"""

def call_model(source: str, tests: str) -> str:
    prompt = f"""Repair the adapter so all tests pass.

CURRENT candidate_adapter.py:
---BEGIN SOURCE---
{source}
---END SOURCE---

FROZEN tests:
---BEGIN TESTS---
{tests}
---END TESTS---

Return only JSON with path=candidate_adapter.py and complete content.
"""
    body = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "seed": SEED,
        "max_tokens": 1800,
        "stream": False,
    }
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=240) as response:
        doc = json.load(response)
    return str(doc["choices"][0]["message"]["content"])

def parse_candidate(text: str) -> dict:
    decoder = json.JSONDecoder()
    starts = [i for i, ch in enumerate(text) if ch == "{"]
    errors = []
    for start in starts:
        try:
            obj, _ = decoder.raw_decode(text[start:])
            if isinstance(obj, dict) and "path" in obj and "content" in obj:
                return obj
        except Exception as exc:
            errors.append(str(exc))
    raise ValueError("NO_VALID_CANDIDATE_JSON:" + repr(text[:1000]))

def run_case(case: dict) -> dict:
    raw = call_model(case["source"], case["tests"])
    candidate = parse_candidate(raw)
    if set(candidate) != {"path", "content"}:
        raise AssertionError("CANDIDATE_KEYS_INVALID:" + repr(sorted(candidate)))
    if candidate["path"] != "candidate_adapter.py":
        raise AssertionError("PATH_OUTSIDE_ALLOWLIST:" + repr(candidate["path"]))
    content = candidate["content"]
    if not isinstance(content, str) or not content.strip():
        raise AssertionError("CANDIDATE_CONTENT_INVALID")
    forbidden = (
        "r3_independent_learning_verifier_v1",
        "r3_bound_success_checkpoint_verifier_v1",
        "r3_raw_success_checkpoint_verifier_v1",
        "verification_authority = True",
        '"verification_authority": True',
        "'verification_authority': True",
        "promotion_authority = True",
        '"promotion_authority": True',
        "'promotion_authority': True",
    )
    for token in forbidden:
        if token in content:
            raise AssertionError("FORBIDDEN_AUTHORITY_TOKEN:" + token)

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        source_path = root / "candidate_adapter.py"
        test_path = root / "test_candidate_adapter.py"
        source_path.write_text(content, encoding="utf-8")
        test_path.write_text(case["tests"], encoding="utf-8")
        py_compile.compile(str(source_path), doraise=True)
        proc = subprocess.run(
            ["python3", "-m", "unittest", "-v", "test_candidate_adapter.py"],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=60,
        )
        if proc.returncode != 0:
            raise AssertionError("FOCUSED_TEST_FAILURE:\n" + proc.stdout)
    return {
        "case_id": case["id"],
        "pass": True,
        "path_allowlist_preserved": True,
        "py_compile_pass": True,
        "focused_tests_pass": True,
        "candidate_only": True,
        "verification_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
    }

def main() -> None:
    results = []
    for case in CASES:
        try:
            results.append(run_case(case))
        except Exception as exc:
            results.append({
                "case_id": case["id"],
                "pass": False,
                "reason": type(exc).__name__ + ":" + str(exc),
            })
    passed = sum(1 for row in results if row.get("pass") is True)
    receipt = {
        "schema": "PROJECT_BRAIN_SERA8B_Q4_R3_PATCH_AUTHOR_QUALIFICATION_V1",
        "status": "PASS" if passed == len(CASES) else "FAIL",
        "subject_is_transformed_variant": True,
        "original_sera8b_swebench_result_inherited": False,
        "cases_total": len(CASES),
        "cases_passed": passed,
        "results": results,
        "candidate_generation_authority": passed == len(CASES),
        "source_patch_execution_authority": False,
        "verification_authority": False,
        "promotion_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "incremental_spend_usd": 0,
    }
    Path("sera8b_q4_r3_patch_author_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    raise SystemExit(0 if receipt["status"] == "PASS" else 1)

if __name__ == "__main__":
    main()
