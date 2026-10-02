from __future__ import annotations
import hashlib
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parent
EXPECTED={
  "canonical/governance/CAD_T0_CANDIDATE_FREEZE_V2.json": "039056ad65c1721d871d378ff0497fc461ab4df2",
  "canonical/governance/CAD_T0_POST_REFREEZE_BINDING_V2.json": "7a6f04e08587ff5471ab406c04ab8acd76cc16eb",
  "canonical/verification/M1A_POSITIONED_OCR_TSV_BRIDGE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json": "949612638affa5891fe74517ad6b83371a783f69",
  "canonical/verification/CAD_T0_POPULATION_ORACLE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json": "d27aece637d10e46bff72b762f5743d5048c7af0",
  "canonical/runtime/cad_t0_post_refreeze_composition_guard_v2.py": "46ce4df48c96a46415710d0fd9caec8d66435a78",
  "canonical/tests/test_cad_t0_post_refreeze_composition_guard_v2.py": "2fd7f4270e5284497e34a3aeb454a892a06ad42c",
  "canonical/runtime/bound_capabilities/image_ocr_tesseract_positioned.py": "19f3087489ce7f6f935fc7baaebdc8cd672f4b62",
  "canonical/runtime/bound_capabilities/image_ocr_tesseract.py": "45714d7a0160802d986042910da1c4c6462676e5",
  "canonical/tests/test_image_ocr_tesseract_positioned.py": "b427dd6c5772aee65ebe69530659b40acf0042f1",
  "canonical/governance/M1A_POSITIONED_OCR_TSV_BRIDGE_V1.json": "c220792eaf113b1683bcb82a59811da50db32dbf",
  "canonical/governance/M1A_COMPLETE_ACTION_BUNDLE_V2.json": "65f4dc24c398c1f49cffde5711776074fc9f89ff",
  "canonical/governance/M1B_COMPLETE_ACTION_BUNDLE_V2.json": "4e2fde88553a4f9b01ac7c55750c3bc2d393ac15",
  "canonical/governance/M1_MULTIPLEXED_MATCHED_GEOMETRY_PROOF_BUNDLE_V1.json": "e9aaef8a7786a19ae265c6fedde04a4a1ecee4b1",
  "canonical/governance/CAD_T0_MULTIPLEX_TERMINAL_BINDING_V1.json": "b196acadd2f735a7db2d802b5f8f24c01d2445a3",
  "canonical/governance/CAD_T0_EVALUATOR_OBSERVATION_SCHEMA_V1.json": "2bc87504a54c76003f715be9a52c6e635c8991a6",
  "canonical/runtime/cad_t0_geometry_population.py": "64ca276410e2c1dbcd55cfad057e3eec0709790a",
  "canonical/runtime/cad_t0_oracle_adapter.py": "a6e76e1865b9bd9829dbbcf38886486636f76e8a",
  "canonical/runtime/cad_t0_multiplex_scorer.py": "89833581dc4ac67498753feb94e2ff69bad3b7f1",
  "canonical/tests/test_cad_t0_geometry_population_and_oracle.py": "ea98ceda53c8e4a09d72b19bcb4aaaf5874098a5"
}
def blob(p:Path)->str:
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode("ascii")+b"\0"+b).hexdigest()
class ExactBrainBlobBindingTests(unittest.TestCase):
    def test_exact_brain_blobs(self):
        for rel,sha in EXPECTED.items():
            p=ROOT/rel
            self.assertTrue(p.is_file(),rel)
            self.assertEqual(blob(p),sha,rel)
if __name__=="__main__":
    unittest.main(verbosity=2)
