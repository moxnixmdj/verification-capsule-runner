from __future__ import annotations

import unittest

from canonical.runtime.harbor_science_evidence_frontier_v1 import (
    EvidenceFrontierError,
    EvidenceLedger,
    LATEST_RECORD_REFS,
    MAX_EVIDENCE_REQUESTS,
    TEXT_CHUNK_CHARS,
)


class EvidenceFrontierTests(unittest.TestCase):
    def test_long_nested_evidence_round_trips_losslessly(self):
        ledger = EvidenceLedger()
        text = "alpha-" + ("0123456789abcdef" * 2000) + "-omega"
        record = {
            "kind": "ACTION",
            "cycle": 2,
            "action_result": {
                "returncode": 0,
                "stdout": text,
                "stderr": "",
            },
            "verified_covers": ["R1", "R2"],
        }
        ref = ledger.add_record(record)
        self.assertEqual(ledger.reconstruct_record(ref), record)

    def test_large_text_is_chunked_but_not_truncated(self):
        ledger = EvidenceLedger()
        text = "x" * (TEXT_CHUNK_CHARS * 3 + 17)
        ref = ledger.add_record({"stdout": text})
        stored = ledger.get(ref)
        descriptor = stored["value"]["stdout"]
        self.assertNotIn("$inline_text", descriptor)
        manifest = ledger.get(descriptor["$evidence_text_ref"])
        self.assertEqual(manifest["type"], "text_manifest")
        self.assertEqual(len(manifest["chunk_refs"]), 4)
        for chunk_ref in manifest["chunk_refs"]:
            self.assertLessEqual(len(ledger.get(chunk_ref)["text"]), TEXT_CHUNK_CHARS)
        self.assertEqual(ledger.reconstruct_record(ref)["stdout"], text)

    def test_same_first_record_has_same_content_address(self):
        record = {"kind": "OBS", "stdout": "same"}
        self.assertEqual(
            EvidenceLedger().add_record(record),
            EvidenceLedger().add_record(record),
        )

    def test_manifest_is_complete_and_changes_after_append(self):
        ledger = EvidenceLedger()
        first = ledger.add_record({"kind": "A"})
        m1 = ledger.manifest_ref()
        second = ledger.add_record({"kind": "B"})
        m2 = ledger.manifest_ref()
        self.assertNotEqual(m1, m2)
        manifest = ledger.get(m2)
        self.assertEqual(manifest["record_count"], 2)
        self.assertEqual(manifest["record_refs"], [first, second])

    def test_prompt_index_is_constant_shape_and_manifest_reaches_all_records(self):
        ledger = EvidenceLedger()
        refs = [ledger.add_record({"kind": "OBS", "n": i}) for i in range(12)]
        index = ledger.prompt_index()
        self.assertEqual(set(index), {"record_count", "manifest_ref"})
        self.assertEqual(index["record_count"], 12)
        self.assertEqual(len(index["manifest_ref"]), 71)
        manifest = ledger.get(index["manifest_ref"])
        self.assertEqual(manifest["record_refs"], refs)
        self.assertEqual(
            ledger.expansion_candidates([]),
            refs[-LATEST_RECORD_REFS:],
        )

    def test_request_validation_rejects_unknown_duplicate_and_overflow(self):
        ledger = EvidenceLedger()
        ref = ledger.add_record({"kind": "OBS"})
        with self.assertRaisesRegex(EvidenceFrontierError, "UNKNOWN"):
            ledger.validate_requests(["sha256:" + "0" * 64])
        with self.assertRaisesRegex(EvidenceFrontierError, "DUPLICATE"):
            ledger.validate_requests([ref, ref])
        refs = []
        for i in range(MAX_EVIDENCE_REQUESTS + 1):
            refs.append(ledger.add_record({"kind": "OBS", "i": i}))
        with self.assertRaisesRegex(EvidenceFrontierError, "TOO_MANY"):
            ledger.validate_requests(refs)

    def test_expansion_priority_is_requested_then_latest_deduplicated(self):
        ledger = EvidenceLedger()
        refs = [ledger.add_record({"kind": "OBS", "n": i}) for i in range(8)]
        got = ledger.expansion_candidates([refs[0], refs[-1]])
        self.assertEqual(got[0], refs[0])
        self.assertEqual(got[1], refs[-1])
        self.assertEqual(len(got), len(set(got)))
        for ref in refs[-LATEST_RECORD_REFS:]:
            self.assertIn(ref, got)

    def test_object_tamper_is_detected(self):
        ledger = EvidenceLedger()
        ref = ledger.add_record({"kind": "OBS", "stdout": "safe"})
        ledger._objects[ref]["value"]["kind"]["$inline_text"] = "tampered"
        with self.assertRaisesRegex(EvidenceFrontierError, "INTEGRITY_MISMATCH"):
            ledger.get(ref)


if __name__ == "__main__":
    unittest.main(verbosity=2)
