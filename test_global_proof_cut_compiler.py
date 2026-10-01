import copy
import hashlib
import json
import unittest

import global_proof_cut_compiler as g


def cost_model():
    return {
        "status":"FROZEN",
        "information_unit":"PREDECLARED_NEW_TERMINAL_DISTINCTION_UNIT",
        "parallel_wall_clock_aggregation":"MAX_CRITICAL_PATH",
        "bundle_internal_dependencies_included":True,
        "note":"Exact only relative to this frozen declared cost model.",
    }


def freeze_for(obligations, actions, **overrides):
    normalized_obligations, obligation_errors=g._normalize_obligations(obligations)
    assert obligation_errors == []
    known={x["id"] for x in normalized_obligations}
    normalized_actions, action_errors=g._normalize_actions(actions, known)
    assert action_errors == []
    base={
        "schema":g.FREEZE_SCHEMA,
        "status":"FROZEN",
        "evidence_saturation_complete":True,
        "discovery_frontier_frozen":True,
        "candidate_universe_complete_relative_to_freeze":True,
        "invalidated_by_new_candidate":False,
        "evidence_saturation_receipt_sha256":"a"*64,
        "obligation_graph_sha256":g.canonical_hash(normalized_obligations),
        "candidate_universe_sha256":g.canonical_hash(normalized_actions),
        "cost_model_sha256":g.canonical_hash(cost_model()),
    }
    base.update(overrides)
    return base


def action(i,covers,bits=1,depth=1,wall=1):
    return {
        "id":i,"covers":covers,"new_reality_units":bits,
        "dependency_depth":depth,"critical_path_wall_clock_units":wall,
        "admissible":True,"bundle_complete":True,
    }


def payload(obligations, actions, **freeze_overrides):
    return {
        "schema":g.SCHEMA,
        "obligations":obligations,
        "candidate_actions":actions,
        "cost_model":cost_model(),
        "freeze":freeze_for(obligations,actions,**freeze_overrides),
    }


class GlobalCutTests(unittest.TestCase):
    def setUp(self):
        self.obs=[
            {"id":"A","status":"OPEN","terminal_necessary":True},
            {"id":"B","status":"OPEN","terminal_necessary":True},
            {"id":"C","status":"OPEN","terminal_necessary":True},
        ]

    def test_depth_precedes_fewer_reality_bits(self):
        actions=[
            action("AB",["A","B"],bits=1,depth=1,wall=1),
            action("C",["C"],bits=1,depth=1,wall=1),
            action("ALL_DEEP",["A","B","C"],bits=1,depth=2,wall=1),
        ]
        out=g.compile_cut(payload(self.obs,actions))
        self.assertTrue(out["exact"])
        self.assertEqual(out["max_dependency_depth"],1)
        self.assertEqual(out["selected_actions"],["AB","C"])
        self.assertEqual(out["total_new_reality_units"],2.0)
        self.assertEqual(out["parallel_critical_path_wall_clock_units"],1.0)

    def test_within_same_depth_minimize_new_bits_then_wallclock(self):
        actions=[
            action("A1",["A"],bits=1,depth=1,wall=5),
            action("BC1",["B","C"],bits=1,depth=1,wall=5),
            action("ABC2",["A","B","C"],bits=2,depth=1,wall=2),
            action("ABC2_SLOW",["A","B","C"],bits=2,depth=1,wall=20),
        ]
        out=g.compile_cut(payload(self.obs,actions))
        self.assertTrue(out["exact"])
        # A1+BC1 and ABC2 tie at 2 bits; ABC2 wins on wall clock.
        self.assertEqual(out["selected_actions"],["ABC2"])
        self.assertEqual(out["total_new_reality_units"],2.0)
        self.assertEqual(out["total_critical_path_wall_clock_units"],2.0)

    def test_dominance_deletes_strictly_worse_action(self):
        actions=[
            action("GOOD",["A","B"],bits=1,depth=1,wall=1),
            action("BAD",["A"],bits=2,depth=2,wall=2),
            action("C",["C"],bits=1,depth=1,wall=1),
        ]
        out=g.compile_cut(payload(self.obs,actions))
        self.assertTrue(out["exact"])
        self.assertIn({"deleted":"BAD","dominated_by":"GOOD"},out["dominance_deletions"])

    def test_missing_obligation_coverage_fails_closed(self):
        actions=[action("A",["A"]),action("B",["B"])]
        out=g.compile_cut(payload(self.obs,actions))
        self.assertFalse(out["exact"])
        self.assertEqual(out["status"],"GRAPH_INCOMPLETE")
        self.assertEqual(out["missing_obligations"],["C"])

    def test_new_candidate_invalidates_freeze(self):
        actions=[action("ALL",["A","B","C"])]
        out=g.compile_cut(payload(self.obs,actions,invalidated_by_new_candidate=True))
        self.assertFalse(out["exact"])
        self.assertIn("FROZEN_UNIVERSE_INVALIDATED_BY_NEW_CANDIDATE",out["errors"])

    def test_cost_model_hash_mismatch_fails_closed(self):
        actions=[action("ALL",["A","B","C"])]
        out=g.compile_cut(payload(self.obs,actions,cost_model_sha256="0"*64))
        self.assertFalse(out["exact"])
        self.assertIn("COST_MODEL_HASH_MISMATCH",out["errors"])

    def test_hash_mismatch_fails_closed(self):
        actions=[action("ALL",["A","B","C"])]
        out=g.compile_cut(payload(self.obs,actions,candidate_universe_sha256="0"*64))
        self.assertFalse(out["exact"])
        self.assertIn("CANDIDATE_UNIVERSE_HASH_MISMATCH",out["errors"])

    def test_closed_obligation_needs_no_action(self):
        obs=[
            {"id":"A","status":"CLOSED","terminal_necessary":True},
            {"id":"B","status":"OPEN","terminal_necessary":True},
        ]
        actions=[action("B",["B"])]
        out=g.compile_cut(payload(obs,actions))
        self.assertTrue(out["exact"])
        self.assertEqual(out["open_obligations"],["B"])
        self.assertEqual(out["selected_actions"],["B"])


if __name__=="__main__":
    unittest.main()
