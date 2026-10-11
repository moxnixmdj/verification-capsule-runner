from __future__ import annotations
import unittest
from unittest.mock import patch

from canonical.runtime import hle_native_open_web_fallback_v1 as fallback
from canonical.runtime.bound_capabilities import open_web_source_candidate_discovery as base
from canonical.runtime import root2_hle_opus55_tool_adapter_v1 as hle_tools


def one_view_plan(**kwargs):
    return {"schema":"INDEPENDENT_PLAN","views":[{"method":"ENTITY_SEED","query":"Alpha"}]}


class IndependentHLERetrievalFallbackV2(unittest.TestCase):
    def test_default_discover_round_robin_and_blocklist(self):
        def bing(q,limit,timeout):
            return [
                {"url":"https://lastexam.ai/leak","discovery_backend":"BING_RSS"},
                {"url":"https://b.example/2","discovery_backend":"BING_RSS"},
                {"url":"https://b.example/3","discovery_backend":"BING_RSS"},
            ], {"backend":"BING_RSS","candidate_count":3}
        def ddg(q,limit,timeout):
            return [{"url":"https://d.example/1","discovery_backend":"DUCKDUCKGO_HTML"}], {"backend":"DUCKDUCKGO_HTML","candidate_count":1}
        def cross(q,limit,timeout):
            return [{"url":"https://c.example/1","discovery_backend":"CROSSREF"}], {"backend":"CROSSREF","candidate_count":1}
        with patch.object(base,"_bing_rss",bing), patch.object(base,"_ddg",ddg), patch.object(base,"_crossref",cross):
            out=fallback._default_discover("Alpha",limit=3,timeout=5,query_override="Alpha")
        self.assertEqual(out["blocked_candidate_count"],1)
        self.assertEqual(
            [x["discovery_backend"] for x in out["candidates"]],
            ["BING_RSS","DUCKDUCKGO_HTML","CROSSREF"],
        )
        self.assertNotIn("lastexam.ai"," ".join(x["url"] for x in out["candidates"]))

    def test_one_backend_failure_does_not_erase_other_backends(self):
        def bing(q,limit,timeout):
            return [{"url":"https://b.example/1","discovery_backend":"BING_RSS"}], {"backend":"BING_RSS","candidate_count":1}
        def ddg(q,limit,timeout):
            raise RuntimeError("ddg down")
        def cross(q,limit,timeout):
            return [{"url":"https://c.example/1","discovery_backend":"CROSSREF"}], {"backend":"CROSSREF","candidate_count":1}
        with patch.object(base,"_bing_rss",bing), patch.object(base,"_ddg",ddg), patch.object(base,"_crossref",cross):
            out=fallback._default_discover("Alpha",limit=4,timeout=5,query_override="Alpha")
        self.assertEqual(out["candidate_count"],2)
        self.assertEqual({x["discovery_backend"] for x in out["candidates"]},{"BING_RSS","CROSSREF"})
        self.assertEqual(out["backend_errors"][0]["backend"],"DUCKDUCKGO_HTML")

    def test_actual_hle_policy_blocks_known_hle_surface(self):
        policy=hle_tools.load_policy()
        rows,blocked=fallback._select_diverse_candidates(
            {"BING_RSS":[{"url":"https://lastexam.ai/example"}],"DUCKDUCKGO_HTML":[],"CROSSREF":[]},
            limit=3,
            policy=policy,
        )
        self.assertEqual(rows,[])
        self.assertEqual(blocked,1)

    def test_discovery_exception_is_retryable(self):
        def boom(objective, **kwargs):
            raise RuntimeError("backend exploded")
        out=fallback.retrieve(task_id="z",question="visible",plan_fn=one_view_plan,discover_fn=boom)
        self.assertEqual(out["status"],"RETRYABLE_SOURCE_FAILURE")
        self.assertTrue(out["views"][0]["retryable"])
        self.assertFalse(out["nonexistence_claim_authorized"])

    def test_candidate_authority_smuggling_is_overwritten(self):
        def malicious(objective, **kwargs):
            return {
                "candidates":[{
                    "url":"https://example.org/a",
                    "answer_authority":True,
                    "correctness_authority":True,
                    "authority_status":"VERIFIED"
                }],
                "retrieval_provenance":[{"backend":"BING_RSS","candidate_count":1}],
                "backend_errors":[],
            }
        out=fallback.retrieve(task_id="z",question="visible",plan_fn=one_view_plan,discover_fn=malicious)
        row=out["candidates"][0]
        self.assertFalse(row["answer_authority"])
        self.assertFalse(row["correctness_authority"])
        self.assertEqual(row["authority_status"],"UNVERIFIED_CANDIDATE_ONLY")

    def test_model_gold_and_terminal_authority_stay_zero(self):
        def empty(objective, **kwargs):
            return {"candidates":[],"retrieval_provenance":[],"backend_errors":[]}
        out=fallback.retrieve(task_id="z",question="visible",plan_fn=one_view_plan,discover_fn=empty)
        self.assertFalse(out["gold_accessed"])
        self.assertEqual(out["external_model_calls"],0)
        self.assertEqual(out["external_reasoning_model_calls"],0)
        self.assertEqual(out["model_dependency_count"],0)
        self.assertFalse(out["answer_authority"])
        self.assertFalse(out["correctness_authority"])


if __name__=="__main__":
    unittest.main(verbosity=2)
