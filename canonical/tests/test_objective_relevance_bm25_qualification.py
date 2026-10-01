#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, pathlib, subprocess, sys, unittest
from rank_bm25 import BM25Okapi

ROOT=pathlib.Path(__file__).resolve().parents[2]
P=ROOT/"canonical/runtime/bound_capabilities/objective_relevance_bm25.py"
EXPECTED_BLOB="95d2b6bac6f6ffb5db97526407fcd22cbcc6c790"

def load():
    s=importlib.util.spec_from_file_location("candidate_relevance",P)
    m=importlib.util.module_from_spec(s); sys.modules[s.name]=m; s.loader.exec_module(m); return m

class Qualification(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.m=load()

    def test_exact_candidate_blob(self):
        got=subprocess.check_output(["git","hash-object",str(P)],text=True).strip()
        self.assertEqual(got,EXPECTED_BLOB)

    def independent_top(self,objective,candidates):
        q=self.m._tokens(objective)
        docs=[self.m._tokens(self.m._candidate_text(c)) for c in candidates]
        oracle=BM25Okapi(docs,k1=1.5,b=0.75)
        scores=list(oracle.get_scores(q))
        return max(range(len(scores)),key=lambda i:(scores[i],-i)),scores

    def test_fresh_cross_domain_top_choice_matches_independent_bm25(self):
        cases=[
          (
            "Determine the orbital circularization delta-v for an Earth launch trajectory reaching 400 km apogee",
            [
              {"title":"Garden irrigation systems","snippet":"water pumps and soil moisture"},
              {"title":"Orbital mechanics launch trajectory circularization","snippet":"perigee apogee velocity delta-v Earth orbit 400 km"},
              {"title":"Aircraft airport operations","snippet":"runway schedules and baggage"}
            ],1
          ),
          (
            "Determine whether SQLite online backup remains consistent while the source database is modified concurrently",
            [
              {"title":"SQLite Online Backup API","snippet":"backup destination source database transactions concurrent changes consistency"},
              {"title":"SQL formatting tutorial","snippet":"indentation query style"},
              {"title":"Cloud photo backup","snippet":"mobile images storage"}
            ],0
          ),
          (
            "Compare atmospheric carbon dioxide growth at Mauna Loa across two decades",
            [
              {"title":"Volcano tourism","snippet":"Mauna Loa hiking summit trails"},
              {"title":"Atmospheric CO2 trends at Mauna Loa","snippet":"carbon dioxide monthly observations growth rate atmosphere decade"},
              {"title":"Marine carbon","snippet":"ocean carbonate chemistry"}
            ],1
          )
        ]
        for objective,candidates,expected in cases:
            out=self.m.rank(objective,candidates)
            self.assertEqual(out["status"],"LEXICAL_RELEVANCE_RANKED",out)
            oracle_top,scores=self.independent_top(objective,candidates)
            self.assertEqual(out["top_candidate_original_index"],expected,(out,scores))
            self.assertEqual(oracle_top,expected,(objective,scores))
            self.assertEqual(out["top_candidate_original_index"],oracle_top)
            self.assertEqual(out["model_dependency_count"],0)
            self.assertEqual(out["incremental_spend_usd"],0)
            self.assertEqual(out["primary_source_status"],"UNVERIFIED")
            self.assertEqual(out["semantic_entailment_status"],"UNVERIFIED")

    def test_no_overlap_remains_unresolved(self):
        out=self.m.rank("quantum entanglement Bell photon",[
          {"title":"banana bread","snippet":"flour butter sugar"},
          {"title":"football table","snippet":"league points match"},
        ])
        self.assertEqual(out["status"],"RELEVANCE_UNRESOLVED",out)
        self.assertFalse(out.get("output_verified",False))

if __name__=="__main__": unittest.main(verbosity=2)
