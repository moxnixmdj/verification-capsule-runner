#!/usr/bin/env python3
"""Independent exact-byte verifier for the repaired Unknown-Domain production lease."""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LEASE_PATH = ROOT / "canonical/governance/UNKNOWN_DOMAIN_DIRECT_EXECUTION_LEASE_V1.json"
EXPECTED_LEASE_GIT_BLOB = "049997c1d8ebdb4c07017a2864055109f7238876"
EXPECTED_WORKFLOW_BLOB = "a4315a0ee28ae82145594b7a9abbd00bae61ceb9"
EXPECTED_GENERATOR_V1_BLOB = "f974a4594c78e74693c7ba5a19f131dfa481b937"


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


raw = LEASE_PATH.read_bytes()
assert git_blob(raw) == EXPECTED_LEASE_GIT_BLOB
lease = json.loads(raw)
assert lease["schema"] == "PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_EXECUTION_LEASE_V1"
assert lease["status"].startswith(
    "FROZEN_ONE_USE_PRODUCTION_LEASE__ENTRYPOINT_AND_TRANSITIVE_DEPENDENCY_REPAIR_CANDIDATE"
)
components = lease["exact_components"]
assert components[".github/workflows/unknown-domain-direct-one-use-production.yml"] == EXPECTED_WORKFLOW_BLOB
assert components["canonical/runtime/unknown_domain_direct_hidden_generator_v1.py"] == EXPECTED_GENERATOR_V1_BLOB

for rel, expected in sorted(components.items()):
    path = ROOT / rel
    assert path.is_file(), rel
    got = git_blob(path.read_bytes())
    assert got == expected, (rel, got, expected)

missing = []
edges = []
component_paths = set(components)
for rel in sorted(component_paths):
    if not (rel.startswith("canonical/runtime/") and rel.endswith(".py")):
        continue
    tree = ast.parse((ROOT / rel).read_text(), filename=rel)
    for node in ast.walk(tree):
        modules = []
        if isinstance(node, ast.ImportFrom):
            if node.module == "canonical.runtime":
                modules.extend("canonical.runtime." + alias.name for alias in node.names)
            elif isinstance(node.module, str) and node.module.startswith("canonical.runtime."):
                modules.append(node.module)
        elif isinstance(node, ast.Import):
            modules.extend(
                alias.name for alias in node.names
                if alias.name.startswith("canonical.runtime.")
            )
        for module in modules:
            dep = module.replace(".", "/") + ".py"
            if (ROOT / dep).is_file():
                edges.append((rel, dep))
                if dep not in component_paths:
                    missing.append((rel, dep))

assert not missing, missing
sha256 = hashlib.sha256(raw).hexdigest()
print(json.dumps({
    "schema": "PROJECT_BRAIN_UNKNOWN_DOMAIN_REPAIRED_CANDIDATE_EXACT_VERIFICATION_V1",
    "status": "PASS",
    "execution_lease_git_blob_sha": EXPECTED_LEASE_GIT_BLOB,
    "execution_lease_sha256": sha256,
    "exact_component_count": len(components),
    "checked_local_dependency_edges": len(edges),
    "workflow_git_blob_sha": EXPECTED_WORKFLOW_BLOB,
    "generator_v1_git_blob_sha": EXPECTED_GENERATOR_V1_BLOB,
    "production_cases_consumed": 0,
    "incremental_spend_usd": 0,
}, sort_keys=True))
