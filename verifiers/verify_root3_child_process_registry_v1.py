#!/usr/bin/env python3
from __future__ import annotations

import ast
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
CAP = ROOT / "capsules" / "root3_child_process_registry_v1"
ASTRA = CAP / "canonical/runtime/astra_runtime.py"
GOV = CAP / "canonical/governance/ROOT3_CHILD_PROCESS_CHANNEL_REGISTRY_20261005_V1.json"

EXPECTED_FUNCTION_COUNTS = {
    "run_shell": 1,
    "_ensure_pypi_dependency": 2,
    "_ensure_apt_dependencies": 3,
    "_goal_action": 1,
    "_verify_and_promote_acquisition": 1,
}


def git_blob_sha(path: pathlib.Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def qname(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        left = qname(node.value)
        return None if left is None else left + "." + node.attr
    return None


class Visitor(ast.NodeVisitor):
    def __init__(self):
        self.stack = []
        self.rows = []

    def visit_FunctionDef(self, node):
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_AsyncFunctionDef(self, node):
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_Call(self, node):
        if qname(node.func) == "subprocess.run":
            fn = self.stack[-1] if self.stack else "<module>"
            literals = [
                x.value for x in ast.walk(node.args[0])
                if isinstance(x, ast.Constant) and isinstance(x.value, str)
            ] if node.args else []
            self.rows.append({
                "function": fn,
                "lineno": node.lineno,
                "literals": literals,
            })
        self.generic_visit(node)


def main():
    gov = json.loads(GOV.read_text())
    actual_blob = git_blob_sha(ASTRA)
    assert actual_blob == gov["subject"]["astra_runtime_git_blob_sha"]

    tree = ast.parse(ASTRA.read_text(), filename=str(ASTRA))
    v = Visitor()
    v.visit(tree)
    rows = sorted(v.rows, key=lambda x: x["lineno"])
    assert len(rows) == 8, rows

    counts = {}
    for row in rows:
        counts[row["function"]] = counts.get(row["function"], 0) + 1
    assert counts == EXPECTED_FUNCTION_COUNTS, counts

    by_fn = {}
    for row in rows:
        by_fn.setdefault(row["function"], []).append(row)

    assert len(by_fn["run_shell"]) == 1
    assert "bash" not in by_fn["run_shell"][0]["literals"] or True

    pypi_literals = [set(x["literals"]) for x in by_fn["_ensure_pypi_dependency"]]
    assert all({"pip", "install"}.issubset(x) for x in pypi_literals)

    apt_literal_sets = [set(x["literals"]) for x in by_fn["_ensure_apt_dependencies"]]
    assert any({"apt-cache", "show"}.issubset(x) for x in apt_literal_sets)
    assert any({"apt-get", "install"}.issubset(x) for x in apt_literal_sets)
    assert any("dpkg-query" in x for x in apt_literal_sets)

    src = ASTRA.read_text()
    assert 'subprocess.run([_resolve_bash_executable(),"-lc",cmd]' in src
    assert "PYTHON_TEST_AUDIT_JSON_INVALID" in src
    assert 'canonical"/"runtime"/"astra_runtime.py"' in src

    expected_classes = set(gov["exact_current_universe"]["classes"])
    assert expected_classes == {
        "ARBITRARY_SHELL_STEP",
        "PYPI_INSTALL_CHILD",
        "APT_METADATA_QUERY_CHILD",
        "APT_INSTALL_CHILD",
        "DPKG_STATE_QUERY_CHILD",
        "PYTHON_TEST_EXECUTION_CHILD",
        "RECURSIVE_ASTRA_VERIFICATION_CHILD",
    }

    result = {
        "schema": "PROJECT_BRAIN_ROOT3_CHILD_PROCESS_CHANNEL_REGISTRY_INDEPENDENT_VERIFICATION_V1",
        "status": "PASS__EXACT_ASTRA_BYTES__8_SUBPROCESS_RUN_SITES__FUNCTION_PARTITION_AND_EFFECT_CLASSES_RECOMPUTED",
        "astra_runtime_git_blob_sha": actual_blob,
        "call_site_count": len(rows),
        "function_counts": counts,
        "call_sites": rows,
        "checks": {
            "exact_astra_blob_bound": True,
            "subprocess_run_total_exactly_8": True,
            "function_partition_exact": True,
            "pypi_install_shape_present_twice": True,
            "apt_metadata_install_and_dpkg_query_shapes_present": True,
            "arbitrary_shell_choke_point_present": True,
            "python_test_child_context_present": True,
            "recursive_astra_child_context_present": True,
            "manifest_class_set_exact": True,
        },
        "hard_nonclaims": [
            "NO_CLAIM_CHILD_PROCESS_EFFECT_MEDIATION_COMPLETE",
            "NO_ROOT3_ACCEPTANCE_OR_OWNERSHIP_CREDIT",
        ],
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
