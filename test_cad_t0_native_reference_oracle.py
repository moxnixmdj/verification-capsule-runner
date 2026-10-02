from __future__ import annotations
import unittest
from canonical.runtime.cad_t0_geometry_population import FAMILIES, derive_seed, generate_case, public_case
from canonical.runtime.cad_t0_oracle_adapter import prepare_hidden_case, validate_ambiguity_witness

class NativeReferenceTests(unittest.TestCase):
    def test_all_declared_geometry_families_have_independent_oracle_path(self):
        for slot, family in enumerate(FAMILIES):
            case=generate_case(derive_seed("prewave-commitment","prewave-beacon",f"CAD_T0_GEOMETRY_V1::slot::{slot}"),slot)
            self.assertNotIn("_oracle", public_case(case))
            self.assertEqual(case["_oracle"]["family"], family)
            if case["_oracle"]["identifiable"]:
                prepared=prepare_hidden_case(case)
                metrics=prepared["_oracle"].get("reference_geometry_metrics")
                self.assertIsInstance(metrics,dict)
                self.assertGreater(metrics["volume"],0)
                self.assertGreater(metrics["surface_area"],0)
                self.assertEqual(len(metrics["bbox"]),3)
                self.assertTrue(all(x>0 for x in metrics["bbox"]))
            else:
                self.assertNotIn("reference_geometry_metrics",case["_oracle"])
                good={"status":"NONIDENTIFIABLE","ambiguity_witness":{
                    "parameter":case["_oracle"]["ambiguity_parameter"],
                    "alternatives":case["_oracle"]["consistent_alternatives"],
                }}
                self.assertTrue(validate_ambiguity_witness(case,good))

if __name__=="__main__":
    unittest.main(verbosity=2)
