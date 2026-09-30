#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
P=ROOT/"canonical/runtime/astra_runtime.py"

def load():
    s=importlib.util.spec_from_file_location("astra_runtime_research_route_test",P)
    m=importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m

class BroadResearchRuntimeRoutingTests(unittest.TestCase):
    def test_broad_decomposition_blocks_package_acquisition(self):
        m=load()
        goal="Assess whether a generic technical claim is supported by published evidence"
        mission={"mission_id":"NONPARENT-ROUTING-REGRESSION","goal":goal}
        step={"adapter":"goal","goal_ref":"goal","allow_optional_model_planner":False}

        m._run_verified_capability_proposal=lambda *a,**k: None
        m._run_capability_planned_goal=lambda *a,**k: None
        m._run_model_independent_goal=lambda *a,**k: None
        def compile_fail(_goal):
            raise m.Blocker("GOAL_COMPILATION_FAILED:GOAL_COMPILATION_NO_VERIFIED_CAPABILITY_MATCH")
        m._compile_plain_goal=compile_fail
        m._write_goal_gap_classification=lambda *a,**k: (
            m.EVID_DIR/"NONPARENT-ROUTING-REGRESSION__GAP.json",
            {"gap_class":"CAPABILITY_CANDIDATE"},
        )
        broad={
            "status":"DECOMPOSED","objective":goal,
            "roles":[{"role":"SOURCE_DISCOVERY","status":"REQUIRES_GROUNDING"}],
        }
        m._ground_plain_goal_to_bound_capabilities=lambda *a,**k: (
            m.EVID_DIR/"NONPARENT-ROUTING-REGRESSION__GROUNDING.json",
            {
                "grounded_clause_count":0,
                "broad_objective_decomposition":broad,
                "unresolved_clause_indexes":[0],
            },
        )
        m._run_open_research_source_frontend=lambda *a,**k: (
            m.EVID_DIR/"NONPARENT-ROUTING-REGRESSION__SOURCE_FRONTEND.json",
            {
                "status":"SOURCE_FRONTEND_READY",
                "provenance_verified_candidate_count":3,
                "next_required_capability":"MODEL_INDEPENDENT_SOURCE_AUTHORITY_PRIMARY_EVIDENCE_AND_RELEVANCE_VERIFICATION",
            },
        )
        m._load_auto_capability_acquisition=lambda: (_ for _ in ()).throw(
            AssertionError("PACKAGE_ACQUISITION_MUST_NOT_RUN")
        )

        with self.assertRaises(m.Blocker) as cm:
            m._run_goal_unstamped(step,mission)
        text=str(cm.exception)
        self.assertIn("OPEN_ENDED_RESEARCH_SOURCE_FRONTEND_READY",text)
        self.assertIn('"capability_acquisition_attempted": false',text)
        self.assertNotIn("PACKAGE_ACQUISITION_MUST_NOT_RUN",text)

if __name__=="__main__":
    unittest.main(verbosity=2)
