#!/usr/bin/env python3
from __future__ import annotations
import pathlib, subprocess, unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
FRONT=ROOT/"canonical/runtime/bound_capabilities/open_research_source_frontend.py"
ASTRA=ROOT/"canonical/runtime/astra_runtime.py"

class BridgeClosure(unittest.TestCase):
    def test_exact_blobs(self):
        expected={
            str(FRONT):"703ce5fd82324cc44f262dbafde6e744c8eee0df",
            str(ASTRA):"5d419ff7c52e8e3785a696a82f243f7318998b85",
        }
        for p,sha in expected.items():
            got=subprocess.check_output(["git","hash-object",p],text=True).strip()
            self.assertEqual(got,sha,(p,got,sha))

    def test_astra_frontier_precedes_any_package_acquisition(self):
        s=ASTRA.read_text()
        marker='OPEN_ENDED_RESEARCH_SOURCE_IDENTITY_READY__'
        acquisition='_load_auto_capability_acquisition()'
        i=s.index(marker)
        j=s.index(acquisition,i)
        self.assertLess(i,j)
        window=s[i-2200:j]
        self.assertIn('PRIMARY_SOURCE_RELEVANCE_VERIFICATION_REQUIRED',window)
        self.assertIn('"capability_acquisition_attempted":False',window)
        self.assertIn('authority_identity_verified_candidate_count',window)

    def test_old_overbroad_ready_label_removed_from_identity_path(self):
        s=ASTRA.read_text()
        self.assertIn('AUTHORITY_IDENTITY_PRIMARY_SOURCE_RELEVANCE_VERIFICATION_REQUIRED',s)
        self.assertIn('PRIMARY_SOURCE_RELEVANCE_VERIFICATION_REQUIRED',s)

if __name__=="__main__": unittest.main(verbosity=2)
