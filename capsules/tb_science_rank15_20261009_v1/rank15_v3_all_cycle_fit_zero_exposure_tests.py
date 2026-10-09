from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from canonical.runtime import harbor_science_agent_v3 as agent
from canonical.runtime import harbor_science_planner_v3 as planner


LOGICAL_ID = "a" * 64


def expand_text_ref(store: dict[str, str], ref: str) -> str:
    obj = json.loads(store[ref])
    schema = obj.get("schema")
    if schema == "PROJECT_BRAIN_EVIDENCE_TEXT_CHUNK_V1":
        return obj["text"]
    if schema in {
        "PROJECT_BRAIN_EVIDENCE_REF_TREE_V1",
        "PROJECT_BRAIN_EVIDENCE_REF_TREE_PAGE_V1",
    }:
        return "".join(expand_text_ref(store, child) for child in obj["refs"])
    raise AssertionError(("unexpected evidence node", schema, ref))


class Rank15V3AllCycleFitTests(unittest.TestCase):
    def base_kwargs(self):
        return dict(
            goal="synthetic goal",
            requirements=["REQ_A", "REQ_B"],
            unresolved=["REQ_B"],
            raw_task_prompt_summary={"ordered_manifest_sha256": "b" * 64},
            declared_inputs=[],
            brain_deliverables={},
            logical_attempt_id=LOGICAL_ID,
            cycle=3,
        )

    def test_externalized_full_text_is_losslessly_reconstructible(self):
        store: dict[str, str] = {}
        text = "0123456789abcdef" * 2000
        compact = agent._externalize_string(store, text, label="synthetic.stdout")
        self.assertIsInstance(compact, dict)
        self.assertEqual(compact["sha256"], __import__("hashlib").sha256(text.encode()).hexdigest())
        self.assertEqual(compact["chars"], len(text))
        rebuilt = expand_text_ref(store, compact["chunk_tree_ref"])
        self.assertEqual(rebuilt, text)

    def test_catalog_prompt_shape_is_bounded_by_recent_window_plus_one_archive_root(self):
        store: dict[str, str] = {}
        catalog = []
        for i in range(1000):
            catalog.append({
                "ref": __import__("hashlib").sha256(f"e{i}".encode()).hexdigest(),
                "kind": "BRAIN_SELECTED_RESEARCH_ACTION",
                "cycle": i % agent.MAX_CYCLES,
                "action_id": ("A" + str(i))[:agent.EVIDENCE_ACTION_ID_PREVIEW_CHARS],
                "returncode": i % 3,
                "coverage_promoted": bool(i % 2),
            })
        ctx = agent._catalog_context(catalog, store)
        self.assertEqual(len(ctx["recent"]), agent.RECENT_EVIDENCE_CATALOG_ENTRIES)
        self.assertIsInstance(ctx["archive_root_ref"], str)
        self.assertEqual(len(ctx["archive_root_ref"]), 64)
        self.assertNotIn("archive_pages", ctx)
        self.assertLess(len(json.dumps(ctx, sort_keys=True)), 5000)

    def test_requirement_alias_view_is_bounded_and_round_trips_candidate_covers(self):
        store: dict[str, str] = {}
        requirements = [
            "LONG_REQUIREMENT_ALPHA",
            "LONG_REQUIREMENT_BETA",
        ]
        rows, unresolved = agent._requirement_prompt_view(
            requirements, ["LONG_REQUIREMENT_BETA"], store
        )
        self.assertEqual([r["id"] for r in rows], ["R01", "R02"])
        self.assertEqual(unresolved, ["R02"])
        self.assertTrue(all(len(r["label_preview"]) <= agent.REQUIREMENT_LABEL_PREVIEW_CHARS for r in rows))
        translated = agent._translate_candidate_covers_from_aliases(
            [{"action_id":"A1","covers":["R02"],"command":"echo x","verify_command":"test true"}],
            requirements,
        )
        self.assertEqual(translated[0]["covers"], ["LONG_REQUIREMENT_BETA"])

    def test_unknown_evidence_refs_are_rejected_without_becoming_requests(self):
        known, rejected = agent._normalize_evidence_requests(["f" * 64], {})
        self.assertEqual(known, [])
        self.assertEqual(rejected, ["f" * 64])

    def test_exact_token_packer_includes_fit_evidence_and_defers_overflow(self):
        store: dict[str, str] = {}
        catalog: list[dict] = []
        small = agent._put_evidence(store, {"kind":"small","text":"ok"})
        huge = agent._put_evidence(store, {"kind":"huge","text":"Z" * 30000})

        def fake_count(payload):
            prompt = payload["messages"][1]["content"]
            return len(prompt)

        with patch.object(planner, "count_input_tokens", side_effect=fake_count):
            prompt, meta = agent.build_fitting_science_planner_prompt(
                **self.base_kwargs(),
                evidence_store=store,
                evidence_catalog=catalog,
                requested_refs=[small, huge],
            )
        self.assertIn(small, meta["included_evidence_refs"])
        self.assertIn(huge, meta["deferred_evidence_refs"])
        self.assertLessEqual(meta["input_tokens"], meta["maximum_input_tokens"])
        self.assertIn(small, prompt)
        self.assertNotIn('"ref": "' + huge + '"', prompt)

    def test_same_state_same_pack_is_deterministic(self):
        store: dict[str, str] = {}
        catalog = [{
            "ref": "1" * 64,
            "kind": "OBS",
            "cycle": 1,
            "action_id": "A1",
            "returncode": 0,
            "coverage_promoted": True,
        }]
        evidence_ref = agent._put_evidence(store, {"kind":"detail","value":"same"})

        def fake_count(payload):
            return len(payload["messages"][1]["content"]) // 4 + 1

        kwargs = dict(
            **self.base_kwargs(),
            evidence_store=store,
            evidence_catalog=catalog,
            requested_refs=[evidence_ref],
        )
        with patch.object(planner, "count_input_tokens", side_effect=fake_count):
            p1, m1 = agent.build_fitting_science_planner_prompt(**kwargs)
            p2, m2 = agent.build_fitting_science_planner_prompt(**kwargs)
        self.assertEqual(p1, p2)
        self.assertEqual(m1, m2)

    def test_v3_tool_schema_has_bounded_evidence_requests(self):
        props = planner.TOOL["function"]["parameters"]["properties"]
        req = props["evidence_requests"]
        self.assertEqual(req["maxItems"], agent.MAX_EVIDENCE_REQUESTS)
        self.assertEqual(req["items"]["pattern"], "^[0-9a-f]{64}$")
        self.assertEqual(props["material_requirements"]["items"]["pattern"], "^[A-Za-z0-9_.:-]+$")
        self.assertEqual(
            props["candidates"]["items"]["properties"]["action_id"]["pattern"],
            "^[A-Za-z0-9_.:-]+$",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
