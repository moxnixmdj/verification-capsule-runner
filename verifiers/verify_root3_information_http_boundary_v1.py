#!/usr/bin/env python3
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import pathlib
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
CAP = ROOT / "capsules" / "root3_information_http_boundary_v1"
RUNTIME = CAP / "canonical/runtime/astra_runtime.py"
TESTS = CAP / "canonical/tests/test_astra_external_information_http_boundary_v1.py"
GOV = CAP / "canonical/governance/ROOT3_EXTERNAL_INFORMATION_HTTP_EFFECT_BOUNDARY_20261005_V1.json"
EXPECTED_KINDS = {
    "urlopen",
    "http_get",
    "planner",
    "package_name_search",
    "python_source_tree",
    "pypi_wheel_closure",
}


def git_blob_sha(path: pathlib.Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def load_runtime():
    spec = importlib.util.spec_from_file_location("independent_astra_runtime", RUNTIME)
    if spec is None or spec.loader is None:
        raise RuntimeError("RUNTIME_SPEC_FAILED")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def literal_bridge_call_kinds(tree: ast.AST) -> set[str]:
    out = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        if isinstance(fn, ast.Name) and fn.id == "_external_tool_bridge":
            if not node.args or not isinstance(node.args[0], ast.Constant) or not isinstance(node.args[0].value, str):
                raise AssertionError("NONLITERAL_EXTERNAL_TOOL_BRIDGE_CALL")
            out.add(node.args[0].value)
    return out


def declared_bridge_kinds(tree: ast.Module) -> set[str]:
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(t, ast.Name) and t.id == "_EXTERNAL_TOOL_BRIDGE_KINDS" for t in node.targets):
            continue
        value = node.value
        if not (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Name)
            and value.func.id == "frozenset"
            and len(value.args) == 1
            and isinstance(value.args[0], ast.Set)
        ):
            raise AssertionError("BRIDGE_KIND_REGISTRY_NOT_LITERAL_FROZENSET")
        vals = set()
        for item in value.args[0].elts:
            if not isinstance(item, ast.Constant) or not isinstance(item.value, str):
                raise AssertionError("BRIDGE_KIND_REGISTRY_NONLITERAL")
            vals.add(item.value)
        return vals
    raise AssertionError("BRIDGE_KIND_REGISTRY_MISSING")


def expect_blocker(rt, pattern: str, fn) -> None:
    try:
        fn()
    except rt.Blocker as exc:
        if pattern not in str(exc):
            raise AssertionError(f"WRONG_BLOCKER:{pattern}:{exc}") from exc
    else:
        raise AssertionError("EXPECTED_BLOCKER_NOT_RAISED:" + pattern)


def main() -> int:
    gov = json.loads(GOV.read_text())
    assert gov["subject"]["runtime_git_blob_sha"] == git_blob_sha(RUNTIME)
    assert gov["subject"]["tests_git_blob_sha"] == git_blob_sha(TESTS)

    source = RUNTIME.read_text()
    tree = ast.parse(source)
    declared = declared_bridge_kinds(tree)
    calls = literal_bridge_call_kinds(tree)
    assert declared == EXPECTED_KINDS, (declared, EXPECTED_KINDS)
    assert calls == EXPECTED_KINDS, (calls, EXPECTED_KINDS)

    pos_unknown = source.index('if raw_kind not in _EXTERNAL_TOOL_BRIDGE_KINDS:')
    pos_context = source.index('if _ACTIVE_CONTINUOUS_OBS_CONTEXT is None or _ACTIVE_CONTINUOUS_OBS_MODULE is None:')
    pos_method = source.index('if method not in {"GET","HEAD"}:')
    pos_body = source.index('if request_payload.get("data_b64") is not None:')
    assert pos_unknown < pos_context
    assert pos_method < pos_context
    assert pos_body < pos_context

    rt = load_runtime()
    expect_blocker(
        rt,
        "EXTERNAL_INFORMATION_HTTP_METHOD_FORBIDDEN:POST",
        lambda: rt._bridge_aware_urlopen(
            urllib.request.Request("https://example.invalid/", data=b"x=1"),
            timeout=1,
        ),
    )
    expect_blocker(
        rt,
        "EXTERNAL_INFORMATION_HTTP_METHOD_FORBIDDEN:DELETE",
        lambda: rt._authorize_external_information(
            "urlopen",
            {"url": "https://example.invalid/", "method": "DELETE", "data_b64": None},
        ),
    )
    expect_blocker(
        rt,
        "EXTERNAL_INFORMATION_HTTP_BODY_FORBIDDEN",
        lambda: rt._authorize_external_information(
            "urlopen",
            {"url": "https://example.invalid/", "method": "GET", "data_b64": "eA=="},
        ),
    )
    expect_blocker(
        rt,
        "EXTERNAL_TOOL_KIND_UNREGISTERED:arbitrary_tool",
        lambda: rt._authorize_external_information("arbitrary_tool", {}),
    )
    expect_blocker(
        rt,
        "CONTINUOUS_OBS_INFORMATION_CONTEXT_NOT_BOUND",
        lambda: rt._authorize_external_information(
            "urlopen",
            {"url": "https://example.invalid/", "method": "GET", "data_b64": None},
        ),
    )

    result = {
        "schema": "PROJECT_BRAIN_ROOT3_EXTERNAL_INFORMATION_HTTP_EFFECT_BOUNDARY_INDEPENDENT_VERIFICATION_V1",
        "status": "PASS__EXACT_BYTES__CLOSED_BRIDGE_KIND_UNIVERSE__MUTATING_HTTP_REJECTED_BEFORE_INFORMATION_AUTHORITY_OR_TRANSPORT",
        "runtime_git_blob_sha": git_blob_sha(RUNTIME),
        "tests_git_blob_sha": git_blob_sha(TESTS),
        "declared_bridge_kinds": sorted(declared),
        "literal_bridge_call_kinds": sorted(calls),
        "checks": {
            "exact_runtime_blob_bound": True,
            "exact_tests_blob_bound": True,
            "bridge_kind_registry_exactly_equals_current_literal_call_universe": True,
            "unregistered_kind_rejected_before_obs_or_transport": True,
            "post_rejected_at_bridge_aware_urlopen": True,
            "delete_rejected": True,
            "get_with_body_rejected": True,
            "read_only_get_still_requires_obs": True,
            "semantic_checks_precede_obs_and_transport": True,
        },
        "hard_nonclaims": [
            "NO_CLAIM_WHOLE_EXTERNAL_PROCESS_EFFECT_TOTALITY",
            "NO_ROOT3_ACCEPTANCE_OR_OWNERSHIP_CREDIT",
        ],
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
