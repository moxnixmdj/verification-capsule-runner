#!/usr/bin/env python3
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SUBJECT = ROOT / "subject" / "h100_expression_tree_v1"
RUNTIME = SUBJECT / "canonical" / "runtime" / "h100_expression_tree_symbolic_regression_v1.py"
TESTS = SUBJECT / "canonical" / "tests" / "test_h100_expression_tree_symbolic_regression_v1.py"
GOVERNANCE = SUBJECT / "canonical" / "governance" / "H100_EXPRESSION_TREE_SYMBOLIC_REGRESSION_CANDIDATE_V1.json"

EXPECTED_BLOBS = {
    RUNTIME: "14e8f11c73e5fc0439016dbcd5b5a5a8d2c46490",
    TESTS: "c6285bb2bb5be1c65995a226df1761667a69d8e4",
    GOVERNANCE: "96ccb6e3dca11d0119c52c973a633098a424baa9",
}

ALLOWED_IMPORT_ROOTS = {"__future__", "math", "typing"}
BANNED_CALL_NAMES = {
    "open", "eval", "exec", "compile", "__import__", "input",
}
BANNED_ATTRIBUTE_ROOTS = {
    "os", "sys", "subprocess", "socket", "urllib", "requests", "http",
    "pathlib", "shutil", "pickle", "marshal", "torch", "tensorflow",
    "jax", "random", "secrets",
}


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def import_subject():
    spec = importlib.util.spec_from_file_location("h100_expression_tree_subject", RUNTIME)
    require(spec is not None and spec.loader is not None, "SUBJECT_IMPORT_SPEC_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def audit_ast() -> None:
    tree = ast.parse(RUNTIME.read_text())
    imports = set()
    banned = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                imports.add(root)
                if root not in ALLOWED_IMPORT_ROOTS:
                    banned.append("IMPORT:" + alias.name)
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".", 1)[0]
            imports.add(root)
            if root not in ALLOWED_IMPORT_ROOTS:
                banned.append("IMPORT_FROM:" + str(node.module))
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in BANNED_CALL_NAMES:
                banned.append("CALL:" + node.func.id)
            if isinstance(node.func, ast.Attribute):
                base = node.func.value
                while isinstance(base, ast.Attribute):
                    base = base.value
                if isinstance(base, ast.Name) and base.id in BANNED_ATTRIBUTE_ROOTS:
                    banned.append("ATTR_CALL:" + base.id + "." + node.func.attr)
    require(not banned, "ESCAPE_HATCH_OR_UNAPPROVED_IMPORT:" + ",".join(sorted(set(banned))))
    require(imports <= ALLOWED_IMPORT_ROOTS, "IMPORT_ALLOWLIST_FAILED")


def rows1(fn):
    xs = [-5, -3.5, -2.2, -1.1, -0.4, 0.0, 0.3, 0.9, 1.7, 2.8, 4.2, 5.5]
    return [{"x": x, "y": fn(x)} for x in xs]


def test_fresh_nested_semantics(m) -> None:
    sat = lambda z: z / (1 + abs(z))
    rows = rows1(lambda x: -1.25 + 0.7 * sat(sat(x)))
    out = m.discover(rows, target="y")
    require(out["status"] == "EXACT_CANDIDATE_FOUND", "FRESH_NESTED_SATURATION_NOT_FOUND")
    for x in (-4.4, -1.75, -0.13, 0.18, 1.33, 3.9):
        got = m.predict(out["best_candidate"], {"x": x})
        want = -1.25 + 0.7 * sat(sat(x))
        require(abs(got - want) <= 1e-7, f"FRESH_NESTED_HELDOUT_MISMATCH:{x}:{got}:{want}")


def test_fresh_cross_variable_semantics(m) -> None:
    pairs = [
        (-4.0, -1.5), (-3.0, 2.0), (-2.0, 4.0), (-1.0, -3.0),
        (0.0, 1.0), (1.0, 0.0), (2.0, -2.0), (3.0, 3.0),
        (4.0, -4.0), (5.0, 1.5), (6.0, -0.5), (7.0, 2.5),
    ]
    rows = []
    for x, z in pairs:
        y = 1.1 + 2.2 * (x / (1 + abs(z))) - 0.6 * (z / (1 + abs(x)))
        rows.append({"u": x, "v": z, "y": y})
    out = m.discover(rows, target="y")
    require(out["status"] == "EXACT_CANDIDATE_FOUND", "FRESH_CROSS_VARIABLE_NOT_FOUND")
    held = [(-2.6, 0.7), (0.4, -1.3), (3.3, 1.8), (8.1, -2.2)]
    for x, z in held:
        got = m.predict(out["best_candidate"], {"u": x, "v": z})
        want = 1.1 + 2.2 * (x / (1 + abs(z))) - 0.6 * (z / (1 + abs(x)))
        require(abs(got - want) <= 1e-7, f"FRESH_CROSS_HELDOUT_MISMATCH:{x}:{z}:{got}:{want}")


def test_fail_closed_unseen_nonlinearity(m) -> None:
    xs = [-3.7, -3.0, -2.4, -1.8, -1.1, -0.45, 0.2, 0.75, 1.35, 2.05, 2.8, 3.55]
    rows = [{"x": x, "y": math.sin(1.37 * x) + 0.17 * math.cos(0.61 * x)} for x in xs]
    out = m.discover(rows, target="y", max_depth=2)
    require(out["status"] == "GRAMMAR_NOT_EXACT__EXPAND_OR_EXPERIMENT", "UNSEEN_NONLINEARITY_FALSE_EXACT")
    require(out["acceptance_credit_delta"] == 0, "FAIL_CLOSED_PATH_GRANTED_ACCEPTANCE_CREDIT")
    require(out["capability_credit_delta"] == 0, "FAIL_CLOSED_PATH_GRANTED_CAPABILITY_CREDIT")


def test_accounting_and_determinism(m) -> None:
    sat = lambda z: z / (1 + abs(z))
    rows = rows1(lambda x: 0.25 + 1.8 * x + 2.3 * sat(x))
    a = m.discover(rows, target="y")
    b = m.discover(rows, target="y")
    require(a == b, "REPLAY_NOT_DETERMINISTIC")
    for out in (a, b):
        require(out["persistent_learned_bytes"] == 0, "LEARNED_BYTES_NONZERO")
        require(out["external_frontier_model_calls"] == 0, "FRONTIER_CALL_NONZERO")
        require(out["external_learned_capability_calls"] == 0, "LEARNED_PROVIDER_CALL_NONZERO")
        require(out["dynamic_code_execution"] is False, "DYNAMIC_CODE_EXECUTION_TRUE")
        require(out["random_search"] is False, "RANDOM_SEARCH_TRUE")
        require(out["acceptance_credit_delta"] == 0, "ACCEPTANCE_CREDIT_NONZERO")
        require(out["family_credit_delta"] == 0, "FAMILY_CREDIT_NONZERO")
        require(out["capability_credit_delta"] == 0, "CAPABILITY_CREDIT_NONZERO")
        require(out["ownership_credit_delta"] == 0, "OWNERSHIP_CREDIT_NONZERO")
        require(out["execution_authority"] is False, "EXECUTION_AUTHORITY_TRUE")
        require(out["promotion_authority"] is False, "PROMOTION_AUTHORITY_TRUE")
        require(out["fresh_reality_authority"] is False, "FRESH_REALITY_AUTHORITY_TRUE")


def audit_governance() -> None:
    doc = json.loads(GOVERNANCE.read_text())
    require(doc["status"].startswith("CANDIDATE__"), "GOVERNANCE_NOT_CANDIDATE")
    bound = doc["exact_bound_components"]
    require(
        bound["canonical/runtime/h100_expression_tree_symbolic_regression_v1.py"] == EXPECTED_BLOBS[RUNTIME],
        "GOVERNANCE_RUNTIME_BLOB_MISMATCH",
    )
    require(
        bound["canonical/tests/test_h100_expression_tree_symbolic_regression_v1.py"] == EXPECTED_BLOBS[TESTS],
        "GOVERNANCE_TEST_BLOB_MISMATCH",
    )
    require(doc["authority"]["execution"] is False, "GOVERNANCE_EXECUTION_AUTHORITY_TRUE")
    require(doc["authority"]["promotion"] is False, "GOVERNANCE_PROMOTION_AUTHORITY_TRUE")
    require(doc["authority"]["fresh_reality"] is False, "GOVERNANCE_FRESH_REALITY_TRUE")
    require(doc["accounting"]["capability_credit_delta"] == 0, "GOVERNANCE_CAPABILITY_CREDIT_NONZERO")
    require(doc["accounting"]["acceptance_credit_delta"] == 0, "GOVERNANCE_ACCEPTANCE_CREDIT_NONZERO")
    require(doc["independent_verification_required"] is True, "GOVERNANCE_INDEPENDENT_VERIFICATION_NOT_REQUIRED")


def main() -> None:
    for path, expected in EXPECTED_BLOBS.items():
        actual = git_blob_sha(path)
        require(actual == expected, f"EXACT_BLOB_MISMATCH:{path.name}:{actual}:{expected}")
    audit_ast()
    audit_governance()
    m = import_subject()
    test_fresh_nested_semantics(m)
    test_fresh_cross_variable_semantics(m)
    test_fail_closed_unseen_nonlinearity(m)
    test_accounting_and_determinism(m)
    print(json.dumps({
        "status": "INDEPENDENT_ADVERSARIAL_PASS",
        "exact_subject_blobs": True,
        "ast_escape_hatch_audit": "PASS",
        "fresh_nested_semantics": "PASS",
        "fresh_cross_variable_semantics": "PASS",
        "unseen_nonlinearity_fail_closed": "PASS",
        "deterministic_replay": "PASS",
        "persistent_learned_bytes": 0,
        "external_learned_capability_calls": 0,
        "capability_credit_delta": 0,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
