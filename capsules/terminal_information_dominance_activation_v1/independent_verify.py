import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXPECTED = {
    "canonical/runtime/terminal_information_dominance_v1.py": "f10986bd09a7cc64a1fae3c6ea8e69b5655f2199",
    "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V3.json": "106139ff69616670993dbc6af324d8686747e8b1",
    "canonical/governance/TERMINAL_CERTIFICATE_CUT_ACTIVATION_V2.json": "01f6bc32d6661202d9a41b52d82e9ec56c8a660c",
    "canonical/tests/test_terminal_information_dominance_v1.py": "c934774d1d8c659522da85ba5bde5354d7890bfa",
    "canonical/verification/TERMINAL_INFORMATION_DOMINANCE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json": "cec05df1ef3633a10a1635a9a6d8e86f03130390",
    "canonical/governance/TERMINAL_CERTIFICATE_CUT_ACTIVATION_V3.json": "1f2fd63955e097c73235dcf67421a3a2f8b218b8",
    "canonical/governance/EXECUTION_FIRST_SELF_PROVING_OPTIMIZER_V1.json": "df37f0a93f6372df9f6a94f6dfef35384a238ba3",
    "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json": "e7866ae5c3dbcd4cf8caa44dff6017c887e93acf",
    "canonical/tests/test_terminal_information_dominance_activation_v1.py": "6eb0856c5763515d46cee2dc15ee2e4c3e06177e"
}

def git_blob_sha(rel):
    data=(ROOT/rel).read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()

for rel, expected in EXPECTED.items():
    actual=git_blob_sha(rel)
    assert actual == expected, (rel, actual, expected)

activation=json.loads((ROOT/"canonical/governance/TERMINAL_CERTIFICATE_CUT_ACTIVATION_V3.json").read_text())
optimizer=json.loads((ROOT/"canonical/governance/EXECUTION_FIRST_SELF_PROVING_OPTIMIZER_V1.json").read_text())
authority=json.loads((ROOT/"canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json").read_text())
receipt=json.loads((ROOT/"canonical/verification/TERMINAL_INFORMATION_DOMINANCE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json").read_text())

assert activation["frontier"]["git_blob_sha"] == EXPECTED["canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V3.json"]
assert activation["information_dominance"]["runtime_git_blob_sha"] == EXPECTED["canonical/runtime/terminal_information_dominance_v1.py"]
assert optimizer["reality_query_admission"]["terminal_certificate_cut_activation"] == "canonical/governance/TERMINAL_CERTIFICATE_CUT_ACTIVATION_V3.json"
assert optimizer["terminal_certificate_cut"]["frontier_git_blob_sha"] == EXPECTED["canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V3.json"]
assert authority["truth"]["opus55_acceptance"] == "2/19_PASS__17/19_OPEN"
assert authority["truth"]["achieved"] is False
assert receipt["capability_credit_delta"] == 0 and receipt["family_credit_delta"] == 0
assert activation["capability_credit_delta"] == 0 and activation["family_credit_delta"] == 0
assert activation["execution_authority"] is False and activation["promotion_authority"] is False

print("independent terminal information dominance activation verification: PASS")
