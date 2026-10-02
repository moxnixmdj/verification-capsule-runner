from __future__ import annotations
import json,re,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def load(p): return json.loads((ROOT/p).read_text(encoding="utf-8"))
def slug(s): return re.sub(r"[^a-z0-9]+","_",s.lower()).strip("_")
class Tests(unittest.TestCase):
    def test_exact_current_unproved_matched_scope_target_set(self):
        n=load("canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_CANDIDATE_V1.json")
        r=load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json")
        e=load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json")
        proved={x["predicate_id"] for x in e["claims"] if x.get("state")=="PROVED"}
        expected={x["id"] for x in r["predicates"] if x["kind"] in {"MATCHED_NONINFERIORITY","MATCHED_SCOPE_AUDIT"} and x["id"] not in proved}
        got={x["predicate_id"] for x in n["targets"]}
        self.assertEqual(got,expected)
        self.assertNotIn("DELEGATION_TERMINAL_SUCCESS_NONINFERIOR",got)
        self.assertNotIn("TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR",got)
    def test_family_and_source_atoms_are_grounded(self):
        n=load("canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_CANDIDATE_V1.json")
        r=load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json")
        p=load("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json")
        rb={x["id"]:x for x in r["predicates"]}; pb={x["family"]:x for x in p["protocols"]}
        for t in n["targets"]:
            self.assertEqual(t["family"],rb[t["predicate_id"]]["family"])
            self.assertTrue(t["required_atoms"])
            fam=pb[t["family"]]
            dim_slugs={slug(x) for x in fam.get("task_dimensions",[])}
            metric_slugs={slug(x) for x in fam.get("primary_metrics",[])}
            for atom in t["required_atoms"]:
                prefix,val=atom.split(":",1)
                if prefix=="dimension": self.assertIn(val,dim_slugs)
                if prefix=="metric" and metric_slugs: self.assertIn(val,metric_slugs)
    def test_no_authority_smuggled_into_normalization(self):
        n=load("canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_CANDIDATE_V1.json")
        self.assertIn("INDEPENDENT_VERIFICATION_REQUIRED",n["status"])
        self.assertEqual(n["new_reality_units_consumed"],0)
        self.assertEqual(n["capability_credit_delta"],0); self.assertEqual(n["family_credit_delta"],0)
        self.assertFalse(n["execution_authority"]); self.assertFalse(n["promotion_authority"])
        omitted=set(n["omitted_on_purpose"])
        self.assertTrue({"NO_BRAIN_WITNESS_ATOMS","NO_SCOPE_RELATION","NO_VERIFIED_IMPLICATION_EDGES"} <= omitted)
if __name__=="__main__": unittest.main(verbosity=2)
