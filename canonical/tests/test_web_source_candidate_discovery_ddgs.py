#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
PATH = ROOT / "canonical/runtime/bound_capabilities/web_source_candidate_discovery_ddgs.py"


def load():
    spec = importlib.util.spec_from_file_location("source_discovery", PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class SourceCandidateDiscoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def fake(self, query, n):
        self.assertLessEqual(n, 12)
        return [
            {
                "title": "Official API documentation",
                "href": "https://docs.example.edu/reference/api#section",
                "body": "Technical reference for the requested system",
            },
            {
                "title": "Government technical report",
                "href": "https://agency.gov/research/report?id=7",
                "body": "Primary technical publication",
            },
            {
                "title": "Duplicate",
                "href": "https://agency.gov/research/report?id=7#fragment",
                "body": "Same resource",
            },
            {"title": "Bad", "href": "file:///etc/passwd", "body": ""},
            {"title": "Private", "href": "http://127.0.0.1/x", "body": ""},
        ]

    def test_deterministic_candidate_normalization_and_no_authority_claim(self):
        out = self.m.discover(
            "Determine whether system behavior differs between two conditions",
            max_results=8,
            searcher=self.fake,
        )
        self.assertEqual(out["status"], "SOURCE_CANDIDATES_DISCOVERED")
        self.assertFalse(out["authority_claim_made"])
        self.assertEqual(out["invented_source_urls"], [])
        self.assertEqual(out["invented_facts"], [])
        self.assertEqual(out["model_dependency_count"], 0)
        self.assertEqual(out["incremental_spend_usd"], 0)
        urls = [x["url"] for x in out["candidates"]]
        self.assertEqual(len(urls), len(set(urls)))
        self.assertTrue(all(u.startswith(("https://", "http://")) for u in urls))
        self.assertTrue(any("GOVERNMENT_DOMAIN" in x["authority_signals"] for x in out["candidates"]))
        self.assertTrue(any("ACADEMIC_DOMAIN" in x["authority_signals"] for x in out["candidates"]))
        self.assertTrue(all(x["authority_status"] == "CANDIDATE_UNVERIFIED" for x in out["candidates"]))

    def test_query_plan_is_generic_and_preserves_original_objective(self):
        goal = "Assess whether measured output changed after an intervention"
        out = self.m.discover(goal, searcher=self.fake)
        self.assertEqual(out["query_plan"][0]["query"], goal)
        self.assertEqual(out["query_plan"][0]["kind"], "OBJECTIVE_VERBATIM")
        self.assertIn("official primary source documentation", out["query_plan"][1]["query"])

    def test_fail_closed_empty_and_no_candidates(self):
        with self.assertRaisesRegex(self.m.SourceDiscoveryError, "OBJECTIVE_REQUIRED"):
            self.m.discover("", searcher=self.fake)
        with self.assertRaisesRegex(self.m.SourceDiscoveryError, "NO_SOURCE_CANDIDATES"):
            self.m.discover("Determine whether x differs", searcher=lambda q, n: [])

    def test_rejects_private_and_non_http_urls(self):
        rows = [
            {"title": "x", "href": "http://10.1.2.3/a"},
            {"title": "y", "href": "javascript:alert(1)"},
            {"title": "z", "href": "https://public.example.org/a"},
        ]
        out = self.m.discover("Compare two measurements", searcher=lambda q, n: rows)
        self.assertEqual({x["host"] for x in out["candidates"]}, {"public.example.org"})

    def test_run_writes_bounded_output(self):
        out = self.m.discover("Estimate a physical quantity", searcher=self.fake)
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            p = root / "out.json"
            import json
            p.write_text(json.dumps(out, sort_keys=True), encoding="utf-8")
            self.assertTrue(p.is_file())
            self.assertIn("SOURCE_CANDIDATES_DISCOVERED", p.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
