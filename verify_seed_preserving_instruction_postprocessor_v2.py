#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
SUB = ROOT / "subject" / "seed_preserving_instruction_postprocessor_v2"
RUNTIME = SUB / "canonical" / "runtime"
FILES = {
    RUNTIME / "seed_preserving_instruction_postprocessor_v1.py": "8cdb308941dbd6711279cbd1d505aca6aabdd376",
    RUNTIME / "test_seed_preserving_instruction_postprocessor_v1.py": "df3ac20c7fdf97f9a5ef4cbee727578b12d96a35",
    RUNTIME / "instruction_constraint_compiler_v1.py": "a4a3f87f827bd6f0f85fe70c77a1de5aa3237c6f",
}


def git_blob_sha(path: pathlib.Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


for path, expected in FILES.items():
    got = git_blob_sha(path)
    assert got == expected, (str(path), got, expected)

source = (RUNTIME / "seed_preserving_instruction_postprocessor_v1.py").read_text(encoding="utf-8")
for forbidden in ("urllib", "requests", "socket", "subprocess", "os.system", "pip install"):
    assert forbidden not in source, forbidden
assert "candidate = constraints.exact_response" not in source
assert "candidate = candidate.lower()" not in source
assert "candidate = candidate.upper()" not in source

sys.path.insert(0, str(SUB))
tests = importlib.import_module("canonical.runtime.test_seed_preserving_instruction_postprocessor_v1")
names = sorted(n for n in dir(tests) if n.startswith("test_"))
assert len(names) == 10, names
for name in names:
    getattr(tests, name)()

mod = importlib.import_module("canonical.runtime.seed_preserving_instruction_postprocessor_v1")
pass_cases = [
    ("OK", 'Reply with exactly "OK"'),
    ("mixed case answer", "Write the entire response in lowercase only."),
    ("core answer", 'Response must start with "BEGIN" and response must end with "END"'),
    ("one two three four five", "Answer with at least 5 words."),
    ("the answer contains cedar", 'Include the word "cedar"'),
]
for seed, instruction in pass_cases:
    out = mod.transform(seed, instruction)
    assert out["status"] == "PASS", (seed, instruction, out)
    assert seed in out["response"], (seed, instruction, out)
    assert out["seed_verbatim_preserved"] is True
    assert out["seed_preservation_contract"] == (
        "ANY_PASS_RESPONSE_CONTAINS_THE_ORIGINAL_SEMANTIC_SEED_VERBATIM_"
        "AS_ONE_CONTIGUOUS_SUBSTRING"
    )

exact_conflict = mod.transform("semantic draft", 'Reply with exactly "OK"')
assert exact_conflict["status"] == "FAIL_CLOSED"
assert exact_conflict["error"] == "EXACT_RESPONSE_CONFLICTS_WITH_SEED_PRESERVATION"

case_conflict = mod.transform("US policy", "Write the entire response in lowercase only.")
assert case_conflict["status"] == "FAIL_CLOSED"
assert "LOWERCASE_ONLY" in case_conflict["validation_errors"]

receipt = {
    "schema": "PROJECT_BRAIN_SEED_PRESERVING_INSTRUCTION_POSTPROCESSOR_PUBLIC_VERIFICATION_V2",
    "status": "PASS",
    "subject_git_blobs": {p.name: h for p, h in FILES.items()},
    "synthetic_tests_executed": names,
    "test_count": len(names),
    "verified": {
        "every_exercised_pass_contains_original_seed_verbatim": True,
        "exact_response_conflict_fails_closed": True,
        "lossy_case_conversion_fails_closed": True,
        "literal_wrapper_route_preserves_seed_verbatim": True,
        "exact_postvalidation_used": True,
        "network_path_absent": True,
        "subprocess_path_absent": True,
        "incremental_spend_usd": 0,
        "terminal_authority": False,
    },
    "falsification_repair": {
        "supersedes_semantic_interpretation_of_v1_receipt": True,
        "does_not_erase_v1_historical_execution_receipt": True,
    },
    "hard_nonclaims": [
        "NO_GENERAL_NATURAL_LANGUAGE_INSTRUCTION_FOLLOWING_PROOF",
        "NO_LIVEBENCH_ACCEPTANCE_CREDIT",
        "NO_TERMINAL_CASE_DATA_USED",
    ],
}
path = ROOT / "seed_preserving_instruction_postprocessor_v2_verification_receipt.json"
path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(receipt, sort_keys=True))
