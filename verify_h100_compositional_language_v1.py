from __future__ import annotations

import ast
import hashlib
from pathlib import Path

from canonical.runtime.h100_zero_learned_compositional_language_v1 import (
    compile_compositional_roles,
)

ROOT = Path(__file__).resolve().parent
EXPECTED = {
    "canonical/governance/H100_ZERO_LEARNED_COMPOSITIONAL_LANGUAGE_PREEXPOSURE_V1.json":
        "2d2af5020bc30bc322d4285b54c0d979a5c0b882",
    "canonical/governance/H100_ZERO_LEARNED_COMPOSITIONAL_LANGUAGE_CANDIDATE_V1.json":
        "786b487b9d55a02de970d0092e3c879d44acab9a",
    "canonical/runtime/h100_zero_learned_compositional_language_v1.py":
        "fd5f16e4ac4187a98f7824b68879871a82eece6a",
    "canonical/tests/test_h100_zero_learned_compositional_language_v1.py":
        "1c5095eca2ecd43eca0940662b69f5de8fb3cc19",
}
ALLOWED_IMPORT_ROOTS = {"__future__", "re", "dataclasses", "typing"}


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def verify_exact_blobs() -> None:
    for rel, expected in EXPECTED.items():
        data = (ROOT / rel).read_bytes()
        got = git_blob_sha(data)
        assert got == expected, (rel, got, expected)


def verify_runtime_dependency_surface() -> None:
    path = ROOT / "canonical/runtime/h100_zero_learned_compositional_language_v1.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                roots.add(node.module.split(".")[0])
    assert roots <= ALLOWED_IMPORT_ROOTS, roots


def check(text: str, status: str, inputs: list[str], target: str | None) -> None:
    out = compile_compositional_roles(text)
    assert out["status"] == status, (text, out)
    assert out["inputs"] == inputs, (text, out)
    assert out["target"] == target, (text, out)
    assert out["persistent_learned_bytes"] == 0
    assert out["external_frontier_model_calls"] == 0
    assert out["external_learned_capability_calls"] == 0


def verify_fresh_challenges() -> None:
    cases = [
        (
            "u and v are variables. The former predicts z. z is the response.",
            "ROLES_IDENTIFIED", ["u"], "z",
        ),
        (
            "a and b are variables. They predict c. c is the response.",
            "ROLES_IDENTIFIED", ["a", "b"], "c",
        ),
        (
            "a is the response. b is not the response. c predicts a.",
            "ROLES_IDENTIFIED", ["c"], "a",
        ),
        (
            "m and n are predictors. The former is not a predictor. y is the response.",
            "ABSTAIN_CONTRADICTION", [], None,
        ),
        (
            "m and n are variables. The latter is the response. The former affects it.",
            "ROLES_IDENTIFIED", ["m"], "n",
        ),
    ]
    for case in cases:
        check(*case)


if __name__ == "__main__":
    verify_exact_blobs()
    verify_runtime_dependency_surface()
    verify_fresh_challenges()
    print("PASS exact blobs, dependency surface, and 5 fresh compositional challenges")
