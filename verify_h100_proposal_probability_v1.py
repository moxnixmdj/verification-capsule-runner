#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SUBJECT = ROOT / "subject" / "h100_proposal_probability_v1"
FIXED_RUNTIME = SUBJECT / "canonical/runtime/h100_proposal_probability_estimator_v1.py"
FIXED_TESTS = SUBJECT / "canonical/tests/test_h100_proposal_probability_estimator_v1.py"
FIXED_GOV = SUBJECT / "canonical/governance/H100_PROPOSAL_PROBABILITY_ESTIMATOR_CANDIDATE_V1.json"
ANY_RUNTIME = SUBJECT / "canonical/runtime/h100_anytime_proposal_confidence_v1.py"
ANY_TESTS = SUBJECT / "canonical/tests/test_h100_anytime_proposal_confidence_v1.py"
ANY_GOV = SUBJECT / "canonical/governance/H100_ANYTIME_PROPOSAL_CONFIDENCE_CANDIDATE_V1.json"

EXPECTED = {
    FIXED_RUNTIME: "ca0d56ac568639009a7b2c2c90ae1d17840d3676",
    FIXED_TESTS: "2e48403e2ad949f4f89399fc57b993f78b908da3",
    FIXED_GOV: "00e6f226f8c46ed423db1edc63106322b8fd833f",
    ANY_RUNTIME: "f8e4bf51f758c7c4c89c5e5d899d8f7e756c767f",
    ANY_TESTS: "03384f1c71d5211d06ae3194b820884d3ae04d82",
    ANY_GOV: "845c03bb4e903943de6a725255ccaf7d23b10b81",
}


def require(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, "IMPORT_SPEC_FAILED:" + name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_fixed(m) -> None:
    for n in (1, 2, 3, 5, 10, 25):
        for s in range(n + 1):
            lo = m.clopper_pearson_lower(s, n)
            require(0.0 <= lo <= s / n + 1e-15, f"FIXED_BOUND_RANGE:{s}:{n}:{lo}")
            if 0 < s < n:
                tail = sum(math.comb(n, k) * lo**k * (1-lo)**(n-k) for k in range(s, n+1))
                require(abs(tail - 0.05) < 1e-9, f"FIXED_TAIL_NOT_EXACT:{s}:{n}:{tail}")
    require(m.clopper_pearson_lower(0, 50) == 0.0, "ZERO_SUCCESS_LOWER_NONZERO")
    require(m.n95_from_lower_bound(0.0) is None, "ZERO_LOWER_N95_FINITE")


def verify_anytime(m) -> None:
    partial = sum(1.0 / (t * (t + 1)) for t in range(1, 1_000_000))
    expected = 1.0 - 1.0 / 1_000_000
    require(abs(partial - expected) < 1e-12, "SPENDING_TELESCOPE_FAILED")

    for n in (1, 2, 3, 5, 10, 25, 50):
        for s in range(n + 1):
            lo = m.lower_bound(s, n)
            hi = m.upper_bound(s, n)
            require(0.0 <= lo <= s/n + 1e-15, f"ANY_LOWER_RANGE:{s}:{n}:{lo}")
            require(s/n - 1e-15 <= hi <= 1.0, f"ANY_UPPER_RANGE:{s}:{n}:{hi}")
            a = (0.05/2.0)/(n*(n+1))
            if 0 < s < n:
                tail = sum(math.comb(n,k)*lo**k*(1-lo)**(n-k) for k in range(s,n+1))
                cdf = sum(math.comb(n,k)*hi**k*(1-hi)**(n-k) for k in range(0,s+1))
                require(abs(tail-a) < 1e-9, f"ANY_LOWER_NOT_EXACT:{s}:{n}:{tail}:{a}")
                require(abs(cdf-a) < 1e-9, f"ANY_UPPER_NOT_EXACT:{s}:{n}:{cdf}:{a}")

    viable = m.sequence([True]*120, viability_p=0.20)
    require(viable["status"] == "VIABLE", "ALL_SUCCESS_DID_NOT_STOP_VIABLE")
    futile = m.sequence([False]*120, viability_p=0.20)
    require(futile["status"] == "FUTILITY", "ALL_FAILURE_DID_NOT_STOP_FUTILE")

    mixed = m.sequence([True]*50 + [False]*200, viability_p=0.10)
    require(mixed["status"] == "VIABLE", "FIRST_CROSSING_REWRITTEN")
    crossings = [x for x in mixed["trace"] if x["decision_if_first_crossing"] != "NONE"]
    require(len(crossings) == 1, "FIRST_CROSSING_COUNT_INVALID")


def verify_governance() -> None:
    fixed = json.loads(FIXED_GOV.read_text())
    anytime = json.loads(ANY_GOV.read_text())
    require(fixed["exact_bound_components"]["canonical/runtime/h100_proposal_probability_estimator_v1.py"] == EXPECTED[FIXED_RUNTIME], "FIXED_RUNTIME_BINDING_MISMATCH")
    require(fixed["exact_bound_components"]["canonical/tests/test_h100_proposal_probability_estimator_v1.py"] == EXPECTED[FIXED_TESTS], "FIXED_TEST_BINDING_MISMATCH")
    require(anytime["exact_bound_components"]["canonical/runtime/h100_anytime_proposal_confidence_v1.py"] == EXPECTED[ANY_RUNTIME], "ANY_RUNTIME_BINDING_MISMATCH")
    require(anytime["exact_bound_components"]["canonical/tests/test_h100_anytime_proposal_confidence_v1.py"] == EXPECTED[ANY_TESTS], "ANY_TEST_BINDING_MISMATCH")
    for doc in (fixed, anytime):
        require(doc["authority"]["execution"] is False, "EXECUTION_AUTHORITY_TRUE")
        require(doc["authority"]["promotion"] is False, "PROMOTION_AUTHORITY_TRUE")
        require(doc["authority"]["fresh_reality"] is False, "FRESH_REALITY_AUTHORITY_TRUE")
        require(doc["independent_verification_required"] is True, "INDEPENDENT_VERIFICATION_NOT_REQUIRED")


def main() -> None:
    for path, expected in EXPECTED.items():
        actual = git_blob_sha(path)
        require(actual == expected, f"EXACT_BLOB_MISMATCH:{path.name}:{actual}:{expected}")
    verify_governance()
    fixed = load_module(FIXED_RUNTIME, "fixed_subject")
    anytime = load_module(ANY_RUNTIME, "anytime_subject")
    verify_fixed(fixed)
    verify_anytime(anytime)
    print(json.dumps({
        "status": "INDEPENDENT_ADVERSARIAL_PASS",
        "exact_subject_blobs": True,
        "fixed_sample_exact_cp": "PASS",
        "anytime_alpha_spending_identity": "PASS",
        "anytime_exact_cp_each_time": "PASS",
        "first_crossing_immutability": "PASS",
        "terminal_cases_consumed": 0,
        "acceptance_credit_delta": 0
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
