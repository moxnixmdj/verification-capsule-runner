import json, unittest
from pathlib import Path
from session_bridge import acceptance_contract as runner_acceptance

ROOT=Path(__file__).resolve().parent
C=json.loads((ROOT/"satb_rank19_stage_b_contract.json").read_text())
S=json.loads((ROOT/"satb_rank19_stage_b_source_accounting.json").read_text())

EXPECTED={
 "R_OUTPUT","R_MUSICXML31","R_FOUR_PARTS","R_CLEFS","R_SOUNDING_PITCH","R_TIME","R_GRID",
 "R_DURATIONS","R_FRESH_ATTACK","R_BAR_SPLIT","R_VOICE_COUNT","R_NONCROSS","R_PITCH",
 "R_KEY_CHANGE","R_KEY_ALL_PARTS","R_CHROMATIC","R_SPELLING","R_MEASURES",
 "R_FINAL_BARLINE","R_NO_REPEATS","R_SOURCE_BOUNDARY"
}

class Rank19StageB(unittest.TestCase):
    def test_full_behavioral_contract_schema(self):
        req={
          "behavior_id","inputs","environment_state","allowed_information",
          "required_output_or_action","success_condition","failure_condition",
          "terminal_consequence","verification_route","dependency_boundary","scope"
        }
        b=C["behavioral_contract"]
        self.assertFalse(req-set(b))
        for k in req:
            self.assertIsInstance(b[k],str)
            self.assertTrue(b[k].strip(),k)

    def test_exact_live_runner_acceptance_schema(self):
        payload={
          "schema":"BRAIN_FAST_BURST_ACCEPTANCE_MODEL_V1",
          "session_id":"rank19-stageb-schema-check",
          "frozen_before_builder":True,
          "solution_tests_verifier_exposed":False,
          "behavioral_contract":C["behavioral_contract"],
          "requirements":[{
             "id":r["id"],"applicable":True,"statement":r["statement"],
             "source_basis":"official rank19 Stage-B allowlisted specification"
          } for r in C["normalized_requirements"]],
          "acceptance_checks":[{
             "id":"CHK_"+r["id"],"kind":"INVARIANT",
             "predicted_consequence":r["statement"],
             "evidence_basis":"official Stage-B specification plus independent score/audio oracle",
             "independence_class":"SPEC_DERIVED_INDEPENDENT_ORACLE",
             "covers_requirements":[r["id"]]
          } for r in C["normalized_requirements"]]
        }
        self.assertEqual(
          runner_acceptance.validate_acceptance_payload(payload,"rank19-stageb-schema-check"),
          []
        )

    def test_requirement_graph_complete(self):
        reqs=C["normalized_requirements"]
        ids=[r["id"] for r in reqs]
        self.assertEqual(set(ids),EXPECTED)
        self.assertEqual(len(ids),len(set(ids)))
        known=set(ids)
        for r in reqs:
            self.assertTrue(r["critical"],r["id"])
            self.assertFalse(r["open_questions"],r["id"])
            self.assertTrue(r["clauses"],r["id"])
            self.assertTrue(r["scenarios"],r["id"])
            self.assertTrue(r["must_detect_failure_modes"],r["id"])
            for d in r["dependencies"]:
                self.assertIn(d,known,(r["id"],d))

    def test_independent_oracle_coverage(self):
        req={r["id"]:r for r in C["normalized_requirements"]}
        oracles=C["independent_acceptance"]["oracles"]
        for rid,r in req.items():
            matches=[o for o in oracles if rid in o["covers"]]
            self.assertTrue(matches,rid)
            detected=set()
            for o in matches:
                self.assertFalse(o["derived_from_builder_output"])
                self.assertNotEqual(o["provenance"],"builder_derived")
                detected.update(o["detects"])
            self.assertFalse(set(r["must_detect_failure_modes"])-detected,rid)

    def test_major_mutants_present(self):
        expected={
          "DELETE_OUTPUT","INVALID_XML","DELETE_PART","SWAP_ALTO_TENOR","TENOR_OCTAVE_SHIFT",
          "CHANGE_METER","SHIFT_NOTE_BY_QUARTER_EIGHTH_GRID","ILLEGAL_DURATION",
          "MERGE_TWO_ATTACKS","UNSPLIT_BARLINE_SUSTAIN","VOICE_CROSSING",
          "PITCH_SEMITONE_ERROR","OCTAVE_ERROR","FALSE_KEY_CHANGE_ON_CHROMATIC",
          "REMOVE_REAL_KEY_CHANGE_FROM_ONE_PART","DELETE_MEASURE_FROM_ONE_PART",
          "WRONG_FINAL_BARLINE","ADD_REPEAT"
        }
        self.assertFalse(expected-set(C["verifier_mutants"]))

    def test_source_boundary(self):
        self.assertEqual(S["forbidden_sources_read"],[])
        self.assertTrue(S["complete"])
        for k in (
          "task_audio_analyzed","solution_read","readme_read","tests_read",
          "hidden_verifier_read","task_specific_repository_search_after_exposure",
          "task_specific_external_search"
        ):
            self.assertFalse(S[k],k)
        self.assertFalse(C["task_execution_authorized"])
        sb=C["source_boundary"]
        self.assertFalse(sb["task_audio_analyzed"])
        self.assertFalse(sb["solution_read"])
        self.assertFalse(sb["tests_read"])
        self.assertFalse(sb["hidden_verifier_read"])

    def test_pinned_general_mechanisms_and_resources(self):
        f=C["feasibility"]
        a=f["acoustic_candidate"]
        n=f["notation_candidate"]
        self.assertEqual(a["repo"],"spotify/basic-pitch")
        self.assertEqual(a["revision"],"fa5997af0a8210982619003269994a1be25eddf3")
        self.assertEqual(a["license"],"Apache-2.0")
        self.assertIn("ONNX",a["preferred_runtime"])
        self.assertEqual(n["repo"],"cuthbertLab/music21")
        self.assertEqual(n["revision"],"55d2d4cd80a1998e35b397a9326791bde976d495")
        self.assertEqual(n["license"],"BSD-3-Clause")
        self.assertIn("CPU-only",f["resource_envelope"])

    def test_unknowns_are_explicit_not_hidden(self):
        u="\n".join(C["semantic_consensus"]["explicit_unknowns"])
        for s in ("tempo/eighth-grid","measure count","modulation boundaries","Basic Pitch"):
            self.assertIn(s,u)

if __name__=="__main__":
    unittest.main(verbosity=2)
