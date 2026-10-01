import json, pathlib, unittest, sys
ROOT=pathlib.Path(__file__).parent
sys.path.insert(0, str(pathlib.Path(__file__).parents[2]))
from session_bridge.acceptance_contract import validate_acceptance_payload

class Rank19StageBStatic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract=json.loads((ROOT/"SATB_AUDIO_TRANSCRIPTION_RANK19_STAGE_B_CONTRACT_V1.json").read_text())
        cls.sources=json.loads((ROOT/"SATB_AUDIO_TRANSCRIPTION_RANK19_STAGE_B_SOURCE_ACCOUNTING_V1.json").read_text())

    def test_exact_required_behavioral_fields(self):
        b=self.contract["behavioral_contract"]
        for k in ("behavior_id","inputs","environment_state","allowed_information",
                  "required_output_or_action","success_condition","failure_condition",
                  "terminal_consequence","verification_route","dependency_boundary","scope"):
            self.assertTrue(str(b.get(k,"")).strip(), k)

    def test_requirement_set_is_complete_and_unique(self):
        ids=[r["id"] for r in self.contract["normalized_requirements"]]
        expected={
          "R_OUTPUT","R_MUSICXML31","R_FOUR_PARTS","R_CLEFS","R_SOUNDING_PITCH",
          "R_TIME","R_GRID","R_DURATIONS","R_FRESH_ATTACK","R_BAR_SPLIT",
          "R_VOICE_COUNT","R_NONCROSS","R_PITCH","R_KEY_CHANGE","R_KEY_ALL_PARTS",
          "R_CHROMATIC","R_SPELLING","R_MEASURES","R_FINAL_BARLINE","R_NO_REPEATS",
          "R_SOURCE_BOUNDARY"
        }
        self.assertEqual(set(ids), expected)
        self.assertEqual(len(ids), len(set(ids)))

    def test_requirement_dependencies_close(self):
        reqs=self.contract["normalized_requirements"]
        ids={r["id"] for r in reqs}
        for r in reqs:
            for d in r.get("dependencies",[]):
                self.assertIn(d, ids, (r["id"],d))
            self.assertTrue(r.get("clauses"), r["id"])
            self.assertTrue(r.get("scenarios"), r["id"])
            self.assertTrue(r.get("must_detect_failure_modes"), r["id"])

    def test_every_failure_mode_has_independent_oracle(self):
        reqs={r["id"]:set(r.get("must_detect_failure_modes",[])) for r in self.contract["normalized_requirements"]}
        covered={k:set() for k in reqs}
        for o in self.contract["independent_acceptance"]["oracles"]:
            self.assertFalse(o.get("derived_from_builder_output"), o["id"])
            self.assertNotIn(o.get("provenance"), {"builder_derived","same_implementation","same_formula","same_semantic_interpretation"})
            for rid in o["covers"]:
                self.assertIn(rid, reqs)
                covered[rid].update(o.get("detects",[]))
        for rid,modes in reqs.items():
            self.assertTrue(modes <= covered[rid], (rid, sorted(modes-covered[rid])))

    def test_source_accounting_is_allowlisted_and_clean(self):
        self.assertTrue(self.sources["complete"])
        self.assertEqual(self.sources.get("forbidden_sources_read"), [])
        allowed_prefixes=(
          "tasks/satb-audio-transcription/instruction.md",
          "tasks/satb-audio-transcription/task.toml",
          "tasks/satb-audio-transcription/environment/"
        )
        for s in self.sources["task_sources"]:
            self.assertTrue(s["path"].startswith(allowed_prefixes), s["path"])
        self.assertFalse(self.sources["task_audio_analyzed"])
        self.assertFalse(self.sources["solution_read"])
        self.assertFalse(self.sources["readme_read"])
        self.assertFalse(self.sources["tests_read"])
        self.assertFalse(self.sources["hidden_verifier_read"])
        self.assertFalse(self.sources["task_specific_repository_search_after_exposure"])
        self.assertFalse(self.sources["task_specific_external_search"])

    def test_stage_c_still_forbidden(self):
        self.assertFalse(self.contract["task_execution_authorized"])
        b=self.contract["source_boundary"]
        self.assertTrue(b["instruction_read"])
        self.assertFalse(b["task_audio_analyzed"])
        self.assertFalse(b["solution_read"])
        self.assertFalse(b["readme_read"])
        self.assertFalse(b["tests_read"])
        self.assertFalse(b["hidden_verifier_read"])
        self.assertFalse(b["task_specific_repository_search_after_exposure"])
        self.assertFalse(b["task_specific_external_search"])

if __name__=="__main__":
    unittest.main(verbosity=2)
