from __future__ import annotations
import hashlib
import importlib
import json
from pathlib import Path

EXPECTED = {
  "canonical/governance/ROOT1_MEANING_SENSITIVE_OWNERSHIP_GATE_V1.json": "1323e66bcad9c3ba994c19ca765076a2e87605d2",
  "canonical/runtime/root1_meaning_sensitive_ownership_gate_v1.py": "791e8349a56404d558f78be5bb86eec39b2a9f17",
  "canonical/tests/test_root1_meaning_sensitive_ownership_gate_v1.py": "f6220cea98ca72f6d4c53e988ce15ec96f3d9d1b",
  "canonical/action_intents/2026-10-04_ROOT1_MEANING_SENSITIVE_OWNERSHIP_GATE_V1.json": "252e28be941f7ac036876da52512c548906c7303",
  "canonical/governance/LIVEBENCH_ROOT1_QWEN38_4B_SEMANTIC_SEED_PRECOMMIT_V1.json": "49dad45f14b4afa81799cc0e3dcb18293ab2fca9",
  "canonical/runtime/instruction_constraint_compiler_v1.py": "a4a3f87f827bd6f0f85fe70c77a1de5aa3237c6f",
  "canonical/runtime/seed_preserving_instruction_postprocessor_v1.py": "8cdb308941dbd6711279cbd1d505aca6aabdd376",
  "canonical/runtime/seed_preserving_instruction_postprocessor_v2.py": "b766cefd5e7f23d2533ff49d1c259eb83a0a53f0"
}

def blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def verify_blobs() -> None:
    for path, expected in EXPECTED.items():
        data = Path(path).read_bytes()
        actual = blob_sha(data)
        assert actual == expected, (path, actual, expected)

def verify_governance() -> None:
    gate = json.loads(Path("canonical/governance/ROOT1_MEANING_SENSITIVE_OWNERSHIP_GATE_V1.json").read_text())
    assert gate["independent_verification_required"] is True
    assert gate["accounting"]["incremental_spend_usd"] == 0
    assert gate["accounting"]["terminal_cases_consumed"] == 0
    assert gate["accounting"]["ownership_credit_delta"] == 0
    assert gate["authority"] == {
        "execution": False,
        "promotion": False,
        "fresh_reality": False,
        "acceptance": False,
        "ownership": False,
    }
    rule = gate["pass_rule"]
    assert "8_OF_8" in rule["seed_semantic_suite"]
    assert "8_OF_8" in rule["brain_composed_suite"]
    assert "AT_LEAST_2_CASES" in rule["materiality"]
    assert "7_OR_8_CASES" in rule["provider_already_capable_verdict"]

def verify_candidate_tests() -> list[str]:
    mod = importlib.import_module("canonical.tests.test_root1_meaning_sensitive_ownership_gate_v1")
    names = sorted(n for n in dir(mod) if n.startswith("test_"))
    assert len(names) == 4, names
    for name in names:
        getattr(mod, name)()
    return names

def main() -> dict:
    verify_blobs()
    verify_governance()
    tests = verify_candidate_tests()
    return {
        "schema": "PROJECT_BRAIN_ROOT1_MEANING_SENSITIVE_OWNERSHIP_GATE_INDEPENDENT_VERIFIER_V1",
        "status": "PASS",
        "exact_blob_identity": True,
        "candidate_tests_passed": tests,
        "provider_already_capable_rejection_verified": True,
        "semantic_inadequacy_rejection_verified": True,
        "multi_effect_brain_rescue_verified": True,
        "zero_credit_verified": True,
        "fresh_reality_authority": False,
    }

if __name__ == "__main__":
    print(json.dumps(main(), sort_keys=True))
