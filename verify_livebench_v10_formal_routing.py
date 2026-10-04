#!/usr/bin/env python3
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent
EXPECTED = {
    "diagnose_livebench_replay72_v10_formal_routing.py": "56ea114d59f0309bc14ef0504a44bec1f808e876",
    "launch_livebench_v10_formal_routing_atomic.py": "2d3b9ad4e3f4f02af56f402733a8d8bb04ab79c0",
    "canonical/runtime/root2_livebench_if_astra_inference_adapter_v2.py": "dbc895a0e458e411aafd3c96e0ddc2c01e657375",
    "canonical/runtime/instruction_constraint_compiler_v1.py": "a4a3f87f827bd6f0f85fe70c77a1de5aa3237c6f",
    "diagnose_livebench_replay72_v8_structural.py": "bc5bfd7d791b1343cbcf4d09d8f41c6f73ed9f68",
    "livebench_v8_structural_classifier.py": "0c48d463989f8351e3b0a502a174b59ff391ffe8",
    "execute_livebench_if_replay72_v4_candidate.py": "2a57ce896ddbd6819246aab8b44d17a00f36b61e",
}
EPOCH = "a71f24f79df6b6be6e910efb1299776ac9fede9e78539577695d6e386fc2eb52"
CANDIDATE = "7d42814e46abda96eed0fb1929bef5a829bd2236"
WRAPPER = "56ea114d59f0309bc14ef0504a44bec1f808e876"
ACTIVATION_FILE = ROOT / "LIVEBENCH_V10_REPLAY72_ACTIVATION_V1.json"


def blob(path: pathlib.Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


for rel, want in EXPECTED.items():
    path = ROOT / rel
    if not path.is_file() or blob(path) != want:
        raise SystemExit("FAIL_CLOSED:BLOB_MISMATCH:" + rel)

wrapper_text = (ROOT / "diagnose_livebench_replay72_v10_formal_routing.py").read_text(encoding="utf-8")
launcher_text = (ROOT / "launch_livebench_v10_formal_routing_atomic.py").read_text(encoding="utf-8")
ast.parse(wrapper_text)
ast.parse(launcher_text)

checks = [
    "root2_livebench_if_astra_inference_adapter_v2 as adapter" in wrapper_text,
    "a4a3f87f827bd6f0f85fe70c77a1de5aa3237c6f" in wrapper_text,
    EPOCH in wrapper_text,
    EPOCH in launcher_text,
    'CLAIM_REF = "refs/heads/livebench-v10-claims/" + EPOCH_DIGEST' in launcher_text,
    'fail("ATOMIC_ONE_USE_CLAIM_ALREADY_EXISTS")' in launcher_text,
    "verify_exact_activation()" in launcher_text,
    "ACTIVATION_BLOB_DRIFT" in launcher_text,
    "ACTIVATION_LAUNCHER_MISMATCH" in launcher_text,
    "ACTIVATION_CASE73_MUST_BE_FALSE" in launcher_text,
]
if not all(checks):
    raise SystemExit("FAIL_CLOSED:CONTRACT")

if not (
    launcher_text.index("activation_blob = verify_exact_activation()")
    < launcher_text.index("atomic_claim()")
    < launcher_text.index("import diagnose_livebench_replay72_v10_formal_routing as diagnostic")
    < launcher_text.index("diagnostic.main(authorized=True, activation_blob=activation_blob)")
):
    raise SystemExit("FAIL_CLOSED:ORDER")

for forbidden in ("REPLAY_LIMIT=200",):
    if forbidden in wrapper_text or forbidden in launcher_text:
        raise SystemExit("FAIL_CLOSED:SCOPE_EXPANSION:" + forbidden)

spec = importlib.util.spec_from_file_location(
    "project_brain_livebench_v10_launcher",
    ROOT / "launch_livebench_v10_formal_routing_atomic.py",
)
if spec is None or spec.loader is None:
    raise SystemExit("FAIL_CLOSED:LAUNCHER_IMPORT")
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


def make_activation(**overrides):
    doc = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_V10_REPLAY72_ACTIVATION_V1",
        "target_predicate": "LIVEBENCH_IF_GE_65_7",
        "epoch_digest_sha256": EPOCH,
        "candidate_git_blob_sha": CANDIDATE,
        "wrapper_git_blob_sha": WRAPPER,
        "launcher_git_blob_sha": EXPECTED["launch_livebench_v10_formal_routing_atomic.py"],
        "replay_scope": {
            "already_exposed_prefix_only": True,
            "replay_prefix_limit": 72,
            "case_73_or_later": False,
        },
        "authority": {
            "replay72": True,
            "new_case_exposure": False,
            "fresh_reality": False,
            "promotion": False,
            "acceptance_credit": False,
        },
    }
    doc.update(overrides)
    return doc


def write_activation(doc):
    ACTIVATION_FILE.write_text(
        json.dumps(doc, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    os.environ["LIVEBENCH_V10_ACTIVATION_BLOB"] = blob(ACTIVATION_FILE)


try:
    valid = make_activation()
    write_activation(valid)
    observed = launcher.verify_exact_activation()
    if observed != os.environ["LIVEBENCH_V10_ACTIVATION_BLOB"]:
        raise SystemExit("FAIL_CLOSED:VALID_ACTIVATION_NOT_BOUND")

    os.environ["LIVEBENCH_V10_ACTIVATION_BLOB"] = "0" * 40
    try:
        launcher.verify_exact_activation()
    except SystemExit as exc:
        if "ACTIVATION_BLOB_DRIFT" not in str(exc):
            raise
    else:
        raise SystemExit("FAIL_CLOSED:WRONG_ACTIVATION_BLOB_ACCEPTED")

    wrong_epoch = make_activation(epoch_digest_sha256="f" * 64)
    write_activation(wrong_epoch)
    try:
        launcher.verify_exact_activation()
    except SystemExit as exc:
        if "ACTIVATION_EPOCH_MISMATCH" not in str(exc):
            raise
    else:
        raise SystemExit("FAIL_CLOSED:WRONG_EPOCH_ACCEPTED")

    bad_scope = make_activation(
        replay_scope={
            "already_exposed_prefix_only": True,
            "replay_prefix_limit": 72,
            "case_73_or_later": True,
        }
    )
    write_activation(bad_scope)
    try:
        launcher.verify_exact_activation()
    except SystemExit as exc:
        if "ACTIVATION_CASE73_MUST_BE_FALSE" not in str(exc):
            raise
    else:
        raise SystemExit("FAIL_CLOSED:CASE73_AUTHORITY_ACCEPTED")

    bad_authority = make_activation(
        authority={
            "replay72": True,
            "new_case_exposure": False,
            "fresh_reality": True,
            "promotion": False,
            "acceptance_credit": False,
        }
    )
    write_activation(bad_authority)
    try:
        launcher.verify_exact_activation()
    except SystemExit as exc:
        if "ACTIVATION_FORBIDDEN_AUTHORITY:fresh_reality" not in str(exc):
            raise
    else:
        raise SystemExit("FAIL_CLOSED:FRESH_REALITY_AUTHORITY_ACCEPTED")
finally:
    os.environ.pop("LIVEBENCH_V10_ACTIVATION_BLOB", None)
    try:
        ACTIVATION_FILE.unlink()
    except FileNotFoundError:
        pass

print("PASS:LIVEBENCH_V10_EXACT_ACTIVATION_WRAPPER_AND_ATOMIC_LAUNCHER_ZERO_CASE_VERIFICATION")
