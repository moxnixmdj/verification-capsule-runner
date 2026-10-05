#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SUB = ROOT / "subject" / "root2_18_content_address_repair"
OUT = ROOT / "root2_18_content_address_repair_receipt.json"

EXPECTED = {
    "activation": ("ACTIVATION.json", "44265094d5827769560cdddef77f500a9b404d0a"),
    "subject": ("SUBJECT.json", "82612b803c1d47eeb8888cf99a00c14a1bea54e1"),
    "verification": ("VERIFICATION.json", "e26b2ec473f457660fad73721052720a39c0090f"),
}

def blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def load(name: str):
    filename, expected = EXPECTED[name]
    path = SUB / filename
    got = blob(path)
    assert got == expected, (name, got, expected)
    return json.loads(path.read_text(encoding="utf-8"))

def main() -> int:
    activation = load("activation")
    subject = load("subject")
    verification = load("verification")

    assert activation["subject_git_blob_sha"] == EXPECTED["subject"][1]
    assert activation["verification_git_blob_sha"] == EXPECTED["verification"][1]
    assert "PENDING" not in activation["verification_git_blob_sha"]

    assert verification["subject_git_blob_sha"] == EXPECTED["subject"][1]
    assert verification["status"].startswith("PASS__EXACT_18_SET_AND_ROUTE_REUSE_RECOMPUTED")
    assert verification["checks"]["proved_atomic_14"] is True
    assert verification["checks"]["unresolved_atomic_24"] is True
    assert verification["checks"]["partition_15_6_3"] is True
    assert verification["checks"]["root2_touching_18"] is True
    assert verification["checks"]["exact_set_equal"] is True
    assert verification["checks"]["missing_routes_0"] is True
    assert verification["checks"]["extra_routes_0"] is True

    assert subject["exact_state"]["proved_atomic"] == 14
    assert subject["exact_state"]["unresolved_atomic"] == 24
    assert subject["exact_state"]["root2_touching"] == 18
    assert len(subject["predicates"]) == 18

    assert activation["scheduling_authority"] is True
    assert activation["execution_authority"] is False
    assert activation["promotion_authority"] is False
    assert activation["fresh_reality_authority"] is False
    assert activation["acceptance_credit_delta"] == 0

    receipt = {
        "schema": "PROJECT_BRAIN_ROOT2_18_CONTENT_ADDRESS_REPAIR_INDEPENDENT_VERIFICATION_V1",
        "status": "PASS__EXACT_SUBJECT_AND_VERIFICATION_CONTENT_ADDRESSES_BOUND__NO_PLACEHOLDER__ZERO_CREDIT",
        "subject_blobs": {k: v[1] for k, v in EXPECTED.items()},
        "verified": {
            "activation_subject_link_exact": True,
            "activation_verification_link_exact": True,
            "placeholder_absent": True,
            "verification_receipt_pass": True,
            "exact_root2_touching": 18,
            "proved_atomic": 14,
            "unresolved_atomic": 24,
            "route_drift": 0,
        },
        "authority": {
            "scheduling": True,
            "execution": False,
            "promotion": False,
            "fresh_reality": False,
        },
        "accounting": {
            "incremental_spend_usd": 0,
            "new_reality_units_consumed": 0,
            "terminal_cases_consumed": 0,
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        },
    }
    OUT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
