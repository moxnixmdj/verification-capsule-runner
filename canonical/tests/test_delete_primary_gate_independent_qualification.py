#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, pathlib, subprocess, unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
FRONT=ROOT/"canonical/runtime/bound_capabilities/open_research_source_frontend.py"
ASTRA=ROOT/"canonical/runtime/astra_runtime.py"

EXPECTED_FRONT="45d916650eeed8a5abf00a1934bdfb5b4304f3c4"
EXPECTED_ASTRA="353d7fe43331e61cf24b778ecdab0b6831caa73b"

def load_front():
    s=importlib.util.spec_from_file_location("front",FRONT)
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

class Discovery:
    @staticmethod
    def discover(objective,limit=12,timeout=15):
        return {"status":"CANDIDATES_DISCOVERED","candidates":[{"url":"https://research.example.edu/evidence","title":"Evidence"}]}
class Provenance:
    @staticmethod
    def verify(candidate,timeout=15):
        return {"status":"RETRIEVAL_PROVENANCE_VERIFIED","final_url":candidate["url"],"final_host":"research.example.edu"}
class ROR:
    @staticmethod
    def bind_candidate(candidate,timeout=15):
        return {"status":"AUTHORITY_IDENTITY_VERIFIED","matched_domain":"research.example.edu"}

class Qualification(unittest.TestCase):
    def test_exact_runtime_blobs(self):
        self.assertEqual(subprocess.check_output(["git","hash-object",str(FRONT)],text=True).strip(),EXPECTED_FRONT)
        self.assertEqual(subprocess.check_output(["git","hash-object",str(ASTRA)],text=True).strip(),EXPECTED_ASTRA)

    def test_frontend_identity_path_has_relevance_only_as_universal_semantic_gate(self):
        m=load_front(); old=m._load_sibling
        try:
            m._load_sibling=lambda name:{
                "open_web_source_candidate_discovery":Discovery,
                "source_candidate_provenance_verify":Provenance,
                "source_authority_binding_ror":ROR,
            }[name]
            objective="Assess whether documented evidence supports the technical objective"
            d={"status":"DECOMPOSED","objective":objective,"question_shape":"ASSESS","roles":[{"role":"SOURCE_DISCOVERY"}]}
            x=m.run(objective,d,limit=3,timeout=5)
            self.assertEqual(x["status"],"SOURCE_FRONTEND_READY",x)
            self.assertEqual(x["authority_identity_verified_candidate_count"],1,x)
            self.assertFalse(x["primary_source_gate_required"],x)
            self.assertFalse(x["primary_source_claims_made"],x)
            self.assertFalse(x["relevance_claims_made"],x)
            self.assertEqual(x["next_required_capability"],"MODEL_INDEPENDENT_OBJECTIVE_RELEVANCE_VERIFICATION_V1",x)
            self.assertEqual(x["role_progress"]["EVIDENCE_ACQUISITION"],"BLOCKED_ON_OBJECTIVE_RELEVANCE_VERIFICATION",x)
        finally:
            m._load_sibling=old

    def test_astra_fail_closed_boundary_moves_without_package_fallthrough(self):
        s=ASTRA.read_text()
        i=s.index("OPEN_ENDED_RESEARCH_SOURCE_IDENTITY_READY__")
        j=s.index("_load_auto_capability_acquisition()",i)
        window=s[i-2500:j]
        self.assertIn("OBJECTIVE_RELEVANCE_VERIFICATION_REQUIRED",window)
        self.assertNotIn("PRIMARY_SOURCE_RELEVANCE_VERIFICATION_REQUIRED",window)
        self.assertIn('"capability_acquisition_attempted":False',window)

if __name__=="__main__": unittest.main(verbosity=2)
