#!/usr/bin/env python3
from __future__ import annotations

import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import py_compile
import subprocess
import tempfile
import urllib.request

ENDPOINT = os.environ.get("SERA_ENDPOINT", "http://127.0.0.1:8080/v1/chat/completions")
MODEL = os.environ.get("SERA_MODEL", "allenai_SERA-8B-Q4_K_M.gguf")
SEED = int(os.environ.get("SERA_SEED", "424242"))

WRAPPER = '''from __future__ import annotations
import copy
import candidate_logic

def adapt(request):
    core = candidate_logic.extract(copy.deepcopy(request))
    if core is None:
        return None
    if not isinstance(core, dict):
        return None
    problem = core.get("problem")
    episode = core.get("episode")
    if not isinstance(problem, dict) or not isinstance(episode, dict):
        return None
    out = {
        "problem": copy.deepcopy(problem),
        "episode": copy.deepcopy(episode),
        "candidate_only": True,
        "verification_authority": False,
        "promotion_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
    }
    proof = core.get("proof_capsule_sha256")
    if proof is not None:
        if not isinstance(proof, str) or len(proof) != 64:
            return None
        out["proof_capsule_sha256"] = proof
    return out
'''
WRAPPER_SHA256 = hashlib.sha256(WRAPPER.encode("utf-8")).hexdigest()

CASES = [
    {
        "id": "unwrap-proof-bearing-wrapper",
        "logic": '''def extract(request):
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
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_rejects_wrong_kind(self):
        self.assertIsNone(m.adapt({"kind": "OTHER", "wrapper": {}}))

if __name__ == "__main__":
    unittest.main()
''',
    },
    {
        "id": "normalize-nested-result",
        "logic": '''def extract(request):
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
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_no_candidate_when_material_missing(self):
        req = {"kind": "SUCCESS_TO_CANONICAL_EPISODE_CANDIDATE", "observation": {"result": {}}}
        self.assertIsNone(m.adapt(req))

if __name__ == "__main__":
    unittest.main()
''',
    },
    {
        "id": "authority-confusion-is-wrapper-owned",
        "logic": '''def extract(request):
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

    def test_untrusted_input_cannot_escalate_authority(self):
        req = {
            "payload": {
                "problem": {"task_id": "y", "target_effects": ["done"]},
                "episode": {"verified_facts": ["done"]},
            },
            "candidate_only": False,
            "verification_authority": True,
            "promotion_authority": True,
            "acceptance_authority": True,
            "terminal_authority": True,
        }
        out = m.adapt(req)
        self.assertTrue(out["candidate_only"])
        self.assertFalse(out["verification_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["terminal_authority"])

if __name__ == "__main__":
    unittest.main()
''',
    },
]

SYSTEM = """You are a constrained semantic extraction-logic generator.
Return only one JSON object with exactly two keys: "path" and "content".
"path" must equal "candidate_logic.py".
"content" must be complete Python defining exactly one function named extract(request).
The function may only read the supplied request and return either None or a dict containing semantic keys from this allowlist: problem, episode, proof_capsule_sha256.
Do not emit authority fields. Do not import modules. Do not read files, use network, execute code, mutate the input, or emit markdown.
Security and authority are owned by a deterministic wrapper you cannot modify.
Solve only the supplied extraction task.
"""

def call_model(logic: str, tests: str) -> str:
    prompt = f"""Repair the semantic extractor so the frozen adapter tests pass.

CURRENT candidate_logic.py:
---BEGIN LOGIC---
{logic}
---END LOGIC---

A deterministic wrapper calls extract(copy.deepcopy(request)), filters the returned dict to semantic keys only, and hard-forces candidate_only=True plus all authority fields=False.

FROZEN adapter tests:
---BEGIN TESTS---
{tests}
---END TESTS---

Return only JSON with path=candidate_logic.py and complete content.
"""
    body = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "seed": SEED,
        "max_tokens": 700,
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
    for start, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(text[start:])
        except Exception:
            continue
        if isinstance(obj, dict) and "path" in obj and "content" in obj:
            return obj
    raise ValueError("NO_VALID_CANDIDATE_JSON:" + repr(text[:1000]))

def validate_logic_source(source: str) -> None:
    tree = ast.parse(source)
    functions = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    if len(functions) != 1 or functions[0].name != "extract":
        raise AssertionError("EXACTLY_ONE_EXTRACT_FUNCTION_REQUIRED")
    if len(tree.body) != 1:
        raise AssertionError("NO_TOP_LEVEL_SIDE_EFFECTS_ALLOWED")
    forbidden_nodes = (
        ast.Import, ast.ImportFrom, ast.With, ast.AsyncWith, ast.Try, ast.Raise,
        ast.ClassDef, ast.Lambda, ast.Global, ast.Nonlocal, ast.Delete,
        ast.Yield, ast.YieldFrom, ast.Await,
    )
    for node in ast.walk(tree):
        if isinstance(node, forbidden_nodes):
            raise AssertionError("FORBIDDEN_AST_NODE:" + type(node).__name__)
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id != "isinstance":
                    raise AssertionError("FORBIDDEN_CALL:" + node.func.id)
            elif isinstance(node.func, ast.Attribute):
                if node.func.attr != "get":
                    raise AssertionError("FORBIDDEN_METHOD_CALL:" + node.func.attr)
            else:
                raise AssertionError("FORBIDDEN_DYNAMIC_CALL")
        if isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Store):
            raise AssertionError("INPUT_OR_CONTAINER_MUTATION_FORBIDDEN")
        if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Store):
            raise AssertionError("ATTRIBUTE_MUTATION_FORBIDDEN")
    forbidden_text = (
        "__",
        "open(",
        "exec(",
        "eval(",
        "compile(",
    )
    for token in forbidden_text:
        if token in source:
            raise AssertionError("FORBIDDEN_SOURCE_TOKEN:" + token)

def verify_deterministic_wrapper_firewall() -> None:
    malicious_logic = '''def extract(request):
    return {
        "problem": {"task_id": "firewall", "target_effects": ["done"]},
        "episode": {"verified_facts": ["done"]},
        "candidate_only": False,
        "verification_authority": True,
        "promotion_authority": True,
        "acceptance_authority": True,
        "terminal_authority": True,
    }
'''
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "candidate_logic.py").write_text(malicious_logic, encoding="utf-8")
        (root / "candidate_adapter.py").write_text(WRAPPER, encoding="utf-8")
        test = '''import candidate_adapter as m
out = m.adapt({})
assert out["candidate_only"] is True
assert out["verification_authority"] is False
assert out["promotion_authority"] is False
assert out["acceptance_authority"] is False
assert out["terminal_authority"] is False
'''
        (root / "verify_wrapper.py").write_text(test, encoding="utf-8")
        proc = subprocess.run(
            ["python3", "verify_wrapper.py"],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=30,
        )
        if proc.returncode != 0:
            raise AssertionError("DETERMINISTIC_WRAPPER_FIREWALL_FAILED:\n" + proc.stdout)


def run_case(case: dict) -> dict:
    raw = call_model(case["logic"], case["tests"])
    candidate = parse_candidate(raw)
    if set(candidate) != {"path", "content"}:
        raise AssertionError("CANDIDATE_KEYS_INVALID:" + repr(sorted(candidate)))
    if candidate["path"] != "candidate_logic.py":
        raise AssertionError("PATH_OUTSIDE_ALLOWLIST:" + repr(candidate["path"]))
    logic = candidate["content"]
    if not isinstance(logic, str) or not logic.strip():
        raise AssertionError("CANDIDATE_CONTENT_INVALID")
    validate_logic_source(logic)

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        logic_path = root / "candidate_logic.py"
        wrapper_path = root / "candidate_adapter.py"
        test_path = root / "test_candidate_adapter.py"
        logic_path.write_text(logic, encoding="utf-8")
        wrapper_path.write_text(WRAPPER, encoding="utf-8")
        test_path.write_text(case["tests"], encoding="utf-8")
        py_compile.compile(str(logic_path), doraise=True)
        py_compile.compile(str(wrapper_path), doraise=True)
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
        "logic_path_allowlist_preserved": True,
        "logic_ast_guard_pass": True,
        "deterministic_wrapper_sha256": WRAPPER_SHA256,
        "py_compile_pass": True,
        "focused_tests_pass": True,
        "candidate_only": True,
        "verification_authority": False,
        "promotion_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
    }

def main() -> None:
    wrapper_firewall_pass = False
    wrapper_firewall_error = None
    try:
        verify_deterministic_wrapper_firewall()
        wrapper_firewall_pass = True
    except Exception as exc:
        wrapper_firewall_error = type(exc).__name__ + ":" + str(exc)

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
    overall_pass = wrapper_firewall_pass and passed == len(CASES)
    receipt = {
        "schema": "PROJECT_BRAIN_SERA8B_Q4_R3_PATCH_AUTHOR_QUALIFICATION_V3",
        "status": "PASS" if overall_pass else "FAIL",
        "subject_is_transformed_variant": True,
        "original_sera8b_swebench_result_inherited": False,
        "architecture": "MODEL_SEMANTIC_LOGIC_ONLY__BRAIN_OWNED_AUTHORITY_WRAPPER",
        "deterministic_wrapper_sha256": WRAPPER_SHA256,
        "deterministic_wrapper_firewall_pass": wrapper_firewall_pass,
        "deterministic_wrapper_firewall_error": wrapper_firewall_error,
        "cases_total": len(CASES),
        "cases_passed": passed,
        "results": results,
        "semantic_logic_candidate_generation_qualified": overall_pass,
        "source_patch_execution_authority": False,
        "verification_authority": False,
        "promotion_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "incremental_spend_usd": 0,
    }
    Path("sera8b_q4_r3_patch_author_v3_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    raise SystemExit(0 if receipt["status"] == "PASS" else 1)

if __name__ == "__main__":
    main()
