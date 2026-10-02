from __future__ import annotations
import hashlib, json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parent
EXPECTED={
  "canonical/governance/CAD_T0_POST_REFREEZE_BINDING_V2.json": "6bee667b4ae9a23e311a3d7b2d804f24310a5b49",
  "canonical/governance/CAD_T0_CANDIDATE_FREEZE_V2.json": "039056ad65c1721d871d378ff0497fc461ab4df2",
  "canonical/runtime/cad_t0_geometry_population.py": "64ca276410e2c1dbcd55cfad057e3eec0709790a",
  "canonical/runtime/cad_t0_oracle_adapter.py": "a6e76e1865b9bd9829dbbcf38886486636f76e8a",
  "canonical/runtime/cad_t0_multiplex_scorer.py": "89833581dc4ac67498753feb94e2ff69bad3b7f1",
  "canonical/governance/CAD_T0_EVALUATOR_OBSERVATION_SCHEMA_V1.json": "2bc87504a54c76003f715be9a52c6e635c8991a6",
  "canonical/verification/M1A_POSITIONED_OCR_TSV_BRIDGE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json": "949612638affa5891fe74517ad6b83371a783f69"
}

def git_blob(path:Path)->str:
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode("ascii")+b"\0"+data).hexdigest()

class CADPostRefreezeV2Tests(unittest.TestCase):
    def test_exact_brain_blobs(self):
        for rel,sha in EXPECTED.items():
            p=ROOT/rel
            self.assertTrue(p.is_file(),rel)
            self.assertEqual(git_blob(p),sha,rel)

    def test_binding_is_fail_closed_prewave_only(self):
        b=json.loads((ROOT/"canonical/governance/CAD_T0_POST_REFREEZE_BINDING_V2.json").read_text())
        freeze=json.loads((ROOT/"canonical/governance/CAD_T0_CANDIDATE_FREEZE_V2.json").read_text())
        self.assertEqual(b["behavior_id"],"CAD_DRAWING_TO_GLOBAL_SOLID_TOPOLOGY_AND_ENVELOPE_001")
        self.assertEqual(b["candidate_freeze"]["blob_sha"],EXPECTED["canonical/governance/CAD_T0_CANDIDATE_FREEZE_V2.json"])
        self.assertEqual(b["population"]["generator_blob_sha"],EXPECTED["canonical/runtime/cad_t0_geometry_population.py"])
        self.assertEqual(b["evaluator"]["oracle_adapter_blob_sha"],EXPECTED["canonical/runtime/cad_t0_oracle_adapter.py"])
        self.assertEqual(b["evaluator"]["scorer_blob_sha"],EXPECTED["canonical/runtime/cad_t0_multiplex_scorer.py"])
        self.assertEqual(b["evaluator"]["observation_schema_blob_sha"],EXPECTED["canonical/governance/CAD_T0_EVALUATOR_OBSERVATION_SCHEMA_V1.json"])
        self.assertEqual(b["ocr_bridge"]["verification_blob_sha"],EXPECTED["canonical/verification/M1A_POSITIONED_OCR_TSV_BRIDGE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"])
        self.assertFalse(b["population"]["post_freeze_beacon_known"])
        self.assertFalse(b["population"]["case_replacement"])
        self.assertFalse(b["population"]["adaptive_selection"])
        self.assertFalse(b["population"]["tuning_replay"])
        self.assertFalse(b["population"]["external_spent_task_used_for_promotion"])
        self.assertFalse(b["evaluator"]["hidden_reference_candidate_visible"])
        self.assertFalse(b["evaluator"]["candidate_self_reported_metrics_authoritative"])
        self.assertEqual(b["terminal_results_observed"],0)
        self.assertEqual(b["fresh_terminal_evidence_consumed"],0)
        self.assertFalse(b["execution_authority"])
        self.assertFalse(b["promotion_authority"])
        self.assertEqual(freeze["terminal_results_observed"],0)
        self.assertEqual(freeze["fresh_terminal_evidence_consumed"],0)
        self.assertFalse(freeze["contamination_state"]["prior_spent_task_reuse_for_promotion"])
        self.assertFalse(freeze["contamination_state"]["fresh_generated_population_selected"])
        self.assertFalse(freeze["contamination_state"]["post_freeze_beacon_known"])

if __name__=="__main__":
    unittest.main(verbosity=2)
