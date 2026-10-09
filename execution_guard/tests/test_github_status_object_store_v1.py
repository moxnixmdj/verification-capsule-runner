from __future__ import annotations

import json
import re
import unittest
from urllib.parse import parse_qs, urlparse

from execution_guard.github_status_object_store_v1 import (
    SerializedStatusObjectStore,
    StatusObjectStoreError,
)


class FakeStatusAPI:
    def __init__(self):
        self.rows = []
        self.fail_manifest = False

    def request(self, method, path, payload=None):
        if method == "POST" and "/statuses/" in path:
            if (
                self.fail_manifest
                and isinstance(payload, dict)
                and str(payload.get("context", "")).endswith("/m")
            ):
                return 500, {"message": "synthetic"}, {}
            self.rows.insert(
                0,
                {
                    "context": payload["context"],
                    "description": payload["description"],
                    "state": payload["state"],
                },
            )
            return 201, {"id": len(self.rows)}, {}
        if method == "GET" and "/statuses" in path:
            query = parse_qs(urlparse(path).query)
            page = int(query.get("page", ["1"])[0])
            per_page = int(query.get("per_page", ["100"])[0])
            start = (page - 1) * per_page
            return 200, self.rows[start : start + per_page], {}
        raise AssertionError((method, path, payload))


class StatusObjectStoreTests(unittest.TestCase):
    def setUp(self):
        self.api = FakeStatusAPI()
        self.store = SerializedStatusObjectStore(
            self.api.request,
            "owner/repo",
            "a" * 40,
            "terminal-test",
        )
        self.value = {
            "schema": "TEST",
            "logical_attempt_id": "b" * 64,
            "sequence": 7,
            "payload": {"x": "y" * 400},
        }

    def test_round_trip(self):
        self.assertTrue(self.store.create("k", self.value))
        self.assertEqual(self.store.read("k"), self.value)

    def test_exact_existing_returns_false(self):
        self.assertTrue(self.store.create("k", self.value))
        self.assertFalse(self.store.create("k", self.value))
        self.assertEqual(self.store.read("k"), self.value)

    def test_partial_chunks_without_manifest_are_absent(self):
        self.api.fail_manifest = True
        with self.assertRaisesRegex(StatusObjectStoreError, "STATUS_WRITE_FAILED"):
            self.store.create("k", self.value)
        self.assertIsNone(self.store.read("k"))

    def test_manifest_with_missing_chunk_fails_closed(self):
        self.store.create("k", self.value)
        prefix = self.store._prefix("k")
        self.api.rows = [
            row
            for row in self.api.rows
            if row.get("context") != prefix + "/c000"
        ]
        with self.assertRaisesRegex(StatusObjectStoreError, "CHUNK_0_MISSING"):
            self.store.read("k")

    def test_conflicting_duplicate_chunk_fails_closed(self):
        self.store.create("k", self.value)
        context = self.store._chunk_context("k", 0)
        self.api.rows.insert(
            0, {"context": context, "description": "C1:CONFLICT", "state": "success"}
        )
        with self.assertRaisesRegex(StatusObjectStoreError, "CHUNK_0_CONFLICT"):
            self.store.read("k")

    def test_identical_duplicate_chunk_is_tolerated(self):
        self.store.create("k", self.value)
        context = self.store._chunk_context("k", 0)
        original = next(x for x in self.api.rows if x["context"] == context)
        self.api.rows.insert(0, json.loads(json.dumps(original)))
        self.assertEqual(self.store.read("k"), self.value)

    def test_conflicting_manifest_fails_closed(self):
        self.store.create("k", self.value)
        context = self.store._manifest_context("k")
        self.api.rows.insert(
            0,
            {
                "context": context,
                "description": "M1:" + "0" * 64 + ":1:2:2",
                "state": "success",
            },
        )
        with self.assertRaisesRegex(StatusObjectStoreError, "MANIFEST_CONFLICT"):
            self.store.read("k")

    def test_pagination_over_one_hundred_statuses(self):
        for i in range(130):
            self.api.rows.append(
                {
                    "context": "other/" + str(i),
                    "description": "x",
                    "state": "success",
                }
            )
        self.assertTrue(self.store.create("k", self.value))
        self.assertEqual(self.store.read("k"), self.value)

    def test_contexts_and_descriptions_respect_limits(self):
        self.store.create("k", self.value)
        self.assertTrue(all(len(x["context"]) <= 100 for x in self.api.rows))
        self.assertTrue(all(len(x["description"]) <= 140 for x in self.api.rows))

    def test_noncanonical_types_rejected(self):
        with self.assertRaisesRegex(StatusObjectStoreError, "OBJECT_DICT_REQUIRED"):
            self.store.create("k", ["x"])

    def test_corrupt_payload_hash_fails_closed(self):
        self.store.create("k", self.value)
        manifest_context = self.store._manifest_context("k")
        row = next(x for x in self.api.rows if x["context"] == manifest_context)
        parts = row["description"].split(":")
        parts[1] = "f" * 64
        row["description"] = ":".join(parts)
        with self.assertRaisesRegex(StatusObjectStoreError, "OBJECT_SHA256_MISMATCH"):
            self.store.read("k")


if __name__ == "__main__":
    unittest.main(verbosity=2)
