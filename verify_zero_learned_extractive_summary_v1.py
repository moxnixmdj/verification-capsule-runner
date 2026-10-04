#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXPECTED = {
    "canonical/runtime/zero_learned_extractive_summary_v1.py": "395cc40c0340e4e433c57e759f8187deaaa02981",
    "canonical/tests/test_zero_learned_extractive_summary_v1.py": "fd5ea18092d3cecbdd74044ab33645d938de3ff3",
    "canonical/governance/LIVEBENCH_ZERO_LEARNED_EXTRACTIVE_SUMMARY_CANDIDATE_V1.json": "4283d6b19f86b919d85ab12bad6e971a05517039",
}

def blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def load_module():
    path = ROOT / "canonical/runtime/zero_learned_extractive_summary_v1.py"
    spec = importlib.util.spec_from_file_location("summary_subject", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("IMPORT_SPEC_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def verify_pass(source: str, out: dict) -> None:
    assert out["status"] == "PASS", out
    assert out["persistent_learned_bytes"] == 0
    assert out["external_frontier_model_calls"] == 0
    assert out["external_learned_capability_calls"] == 0
    assert out["terminal_cases_used"] == 0
    assert out["terminal_authority"] is False
    assert len(out["response"].encode("utf-8")) < len(source.encode("utf-8"))
    pieces = []
    last_end = -1
    for row in out["proof"]:
        a, b = row["source_start"], row["source_end"]
        assert 0 <= a < b <= len(source)
        assert a >= last_end
        span = source[a:b]
        assert span == row["source_span"]
        assert hashlib.sha256(span.encode("utf-8")).hexdigest() == row["source_span_sha256"]
        pieces.append(span)
        last_end = b
    assert out["response"] == " ".join(pieces)
    assert all(piece in source for piece in pieces)

def main() -> int:
    for rel, expected in EXPECTED.items():
        actual = blob_sha((ROOT / rel).read_bytes())
        assert actual == expected, (rel, actual, expected)

    candidate = json.loads(
        (ROOT / "canonical/governance/LIVEBENCH_ZERO_LEARNED_EXTRACTIVE_SUMMARY_CANDIDATE_V1.json").read_text()
    )
    assert candidate["target_effect"] == "text.summarize.faithful_extractive_bounded"
    assert candidate["accounting"]["persistent_learned_bytes"] == 0
    assert candidate["accounting"]["terminal_cases_consumed"] == 0

    m = load_module()

    adversarial = [
        (
            "Mercury is the closest planet to the Sun. "
            "Mercury has a heavily cratered surface. "
            "The planet completes an orbit in about eighty-eight Earth days. "
            "Extreme temperatures occur between day and night."
        ),
        (
            'The engineer wrote, "The valve is closed." '
            "A pressure sensor then reported a stable reading. "
            "The maintenance log recorded the inspection. "
            "A second inspection is scheduled tomorrow."
        ),
        (
            "Alpha systems store records locally! "
            "Beta systems replicate records remotely? "
            "Replication improves recovery after a local failure. "
            "Operators still need tested restoration procedures."
        ),
        (
            "Battery storage can shift solar energy into evening demand. "
            "Battery storage can also reduce renewable curtailment. "
            "Transmission constraints affect both storage and generation. "
            "Market rules influence how storage is dispatched."
        ),
    ]
    for source in adversarial:
        out = m.summarize(source, compression_ratio=0.4, max_sentences=2)
        verify_pass(source, out)

    # Exhaustive deterministic structural stress over bounded synthetic documents.
    checked = 0
    for n in range(2, 9):
        source = " ".join(
            f"Topic{k} supports sharedterm with evidence number {k}."
            for k in range(1, n + 1)
        )
        for ratio in (0.2, 0.35, 0.5, 0.75):
            for cap in (1, 2, 3):
                out1 = m.summarize(source, compression_ratio=ratio, max_sentences=cap)
                out2 = m.summarize(source, compression_ratio=ratio, max_sentences=cap)
                assert out1 == out2
                verify_pass(source, out1)
                checked += 1

    single = m.summarize("Only one meaningful sentence is available.")
    assert single["status"] == "FAIL_CLOSED"
    assert single["response"] is None

    receipt = {
        "schema": "PROJECT_BRAIN_ZERO_LEARNED_EXTRACTIVE_SUMMARY_INDEPENDENT_VERIFICATION_V1",
        "status": "PASS",
        "exact_subject_blobs": True,
        "adversarial_documents_verified": len(adversarial),
        "bounded_structural_cases_verified": checked,
        "verified_properties": [
            "STRICT_BYTE_COMPRESSION_ON_PASS",
            "EVERY_OUTPUT_SENTENCE_RECOMPUTES_TO_EXACT_SOURCE_SPAN",
            "SOURCE_SPAN_ORDER_PRESERVED",
            "SOURCE_SPAN_SHA256_RECOMPUTED",
            "DETERMINISTIC_REPLAY",
            "ZERO_PERSISTENT_LEARNED_BYTES",
            "ZERO_EXTERNAL_LEARNED_OR_FRONTIER_PROVIDER_CALLS",
            "SINGLE_SENTENCE_SOURCE_FAILS_CLOSED",
        ],
        "hard_nonclaims": [
            "NO_ABSTRACTIVE_SUMMARIZATION_CLAIM",
            "NO_COMPLETE_SALIENCE_OR_COVERAGE_GUARANTEE",
            "NO_OPUS_5_5_PARITY_CLAIM",
            "NO_LIVEBENCH_ACCEPTANCE_CREDIT",
        ],
        "accounting": {
            "incremental_spend_usd": 0,
            "terminal_cases_consumed": 0,
            "acceptance_credit_delta": 0,
        },
    }
    Path("zero_learned_extractive_summary_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
