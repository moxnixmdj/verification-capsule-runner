import unittest
from cad_t0_multiplex_scorer import public_case,score_case

REF_GRAPH={"views":{"front":["edge-a"],"top":["edge-b"]},"features":[{"id":"H1","kind":"hole"}]}
REF_METRICS={
  "watertight":True,
  "volume":100.0,
  "surface_area":250.0,
  "principal_inertia":[10.0,20.0,30.0],
  "euler_number":2,
  "curvature_signature":{"flat":8,"curved":2},
}
TOLS={
  "watertight":{"abs":0,"rel":0},
  "volume":{"abs":0.01,"rel":1e-6},
  "surface_area":{"abs":0.01,"rel":1e-6},
  "principal_inertia":{"abs":0.01,"rel":1e-6},
  "euler_number":{"abs":0,"rel":0},
  "curvature_signature":{"abs":0,"rel":0},
}

def identifiable_case():
    return {
      "case_id":"CAD-T0-X",
      "drawing":"visible-only",
      "_oracle":{
        "reference_constraint_graph":REF_GRAPH,
        "identifiable":True,
        "reference_geometry_metrics":dict(REF_METRICS),
        "required_geometry_metrics":list(REF_METRICS),
        "metric_tolerances":{k:dict(v) for k,v in TOLS.items()},
      }
    }

def good_candidate():
    return {"status":"SOLID","constraint_graph":REF_GRAPH}

def good_observation():
    return {
      "candidate_solid_valid":True,
      "geometry_class_covered":True,
      "candidate_geometry_metrics":REF_METRICS,
      "end_to_end_final_geometry_correct":True,
      "cross_stage_state_loss":False,
      "failure_localization_consistent":True,
    }

class Tests(unittest.TestCase):
    def test_public_case_strips_hidden_oracle(self):
        p=public_case(identifiable_case())
        self.assertNotIn("_oracle",p)

    def test_identifiable_good_case_passes_all_three_lanes(self):
        out=score_case(identifiable_case(),good_candidate(),good_observation())
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["lane_A_m1a_pass"])
        self.assertTrue(out["lane_B_m1b_pass"])
        self.assertTrue(out["lane_C_composition_pass"])

    def test_graph_mutation_fails_lane_a(self):
        c=good_candidate()
        c["constraint_graph"]={"views":{},"features":[]}
        out=score_case(identifiable_case(),c,good_observation())
        self.assertFalse(out["pass"])
        self.assertIn("LANE_A_CONSTRAINT_GRAPH_MISMATCH",out["errors"])

    def test_wrong_global_geometry_fails_even_when_local_graph_is_right(self):
        obs=good_observation()
        obs["candidate_geometry_metrics"]={**REF_METRICS,"volume":130.0}
        out=score_case(identifiable_case(),good_candidate(),obs)
        self.assertFalse(out["pass"])
        self.assertIn("LANE_B_METRIC_MISMATCH:volume",out["errors"])

    def test_nonidentifiable_requires_independent_witness_validation(self):
        case={
          "case_id":"CAD-T0-A",
          "_oracle":{"reference_constraint_graph":REF_GRAPH,"identifiable":False}
        }
        cand={"status":"NONIDENTIFIABLE","constraint_graph":REF_GRAPH}
        obs={
          "ambiguity_witness_valid":True,
          "end_to_end_final_geometry_correct":True,
          "cross_stage_state_loss":False,
          "failure_localization_consistent":True,
        }
        self.assertTrue(score_case(case,cand,obs)["pass"])
        obs["ambiguity_witness_valid"]=False
        self.assertFalse(score_case(case,cand,obs)["pass"])

    def test_candidate_hidden_oracle_leak_fails_closed(self):
        cand=good_candidate()
        cand["_oracle"]={"cheat":True}
        out=score_case(identifiable_case(),cand,good_observation())
        self.assertFalse(out["pass"])
        self.assertTrue(any(x.startswith("CANDIDATE_HIDDEN_FIELD_LEAK") for x in out["errors"]))

    def test_numeric_metric_without_frozen_tolerance_fails_closed(self):
        case=identifiable_case()
        del case["_oracle"]["metric_tolerances"]["volume"]
        out=score_case(case,good_candidate(),good_observation())
        self.assertFalse(out["pass"])
        self.assertIn("LANE_B_METRIC_TOLERANCE_INVALID:volume",out["errors"])

if __name__=="__main__":
    unittest.main()


# --- exact Brain CAD post-freeze population/oracle adapter verification ---
import hashlib
from pathlib import Path
from cad_t0_geometry_population import (
    FAMILIES as CAD_POP_FAMILIES,
    SLOT_COUNT as CAD_POP_SLOT_COUNT,
    derive_seed as cad_derive_seed,
    generate_case as cad_generate_case,
    generate_post_freeze as cad_generate_post_freeze,
    public_case as cad_population_public_case,
)
from cad_t0_oracle_adapter import (
    measure_result as cad_measure_result,
    observe_candidate as cad_observe_candidate,
    validate_ambiguity_witness as cad_validate_ambiguity_witness,
)

def _git_blob_sha(path):
    data=Path(path).read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode("ascii")+b"\0"+data).hexdigest()

class _CadBB:
    xlen=10.0; ylen=20.0; zlen=30.0

class _CadShape:
    def BoundingBox(self): return _CadBB()
    def Volume(self): return 6000.0
    def Area(self): return 2200.0
    def Faces(self): return [0]*6
    def Edges(self): return [0]*12
    def Vertices(self): return [0]*8

class _CadSolids:
    def vals(self): return [_CadShape()]

class _CadResult:
    def solids(self): return _CadSolids()
    def val(self): return _CadShape()

class CadPopulationOracleExactBrainTests(unittest.TestCase):
    def test_exact_brain_blobs(self):
        self.assertEqual(
            _git_blob_sha("independent/cad_t0_geometry_population.py"),
            "64ca276410e2c1dbcd55cfad057e3eec0709790a",
        )
        self.assertEqual(
            _git_blob_sha("independent/cad_t0_oracle_adapter.py"),
            "a6e76e1865b9bd9829dbbcf38886486636f76e8a",
        )

    def test_post_freeze_population_is_deterministic_and_beacon_bound(self):
        a=cad_generate_post_freeze("commitment-x","beacon-a")
        b=cad_generate_post_freeze("commitment-x","beacon-a")
        c=cad_generate_post_freeze("commitment-x","beacon-b")
        self.assertEqual(a,b)
        self.assertNotEqual(a,c)
        self.assertEqual(len(a),CAD_POP_SLOT_COUNT)

    def test_population_covers_declared_family_cycle(self):
        seen={
            cad_generate_case(
                cad_derive_seed("commitment","beacon",f"CAD_T0_GEOMETRY_V1::slot::{i}"),i
            )["_oracle"]["family"]
            for i in range(len(CAD_POP_FAMILIES))
        }
        self.assertEqual(seen,set(CAD_POP_FAMILIES))

    def test_public_projection_strips_hidden_reference_contract(self):
        case=cad_generate_case(
            cad_derive_seed("commitment","beacon","CAD_T0_GEOMETRY_V1::slot::0"),0
        )
        public=cad_population_public_case(case)
        self.assertNotIn("_oracle",public)
        self.assertNotIn("reference_geometry_contract",str(public))
        self.assertNotIn("reference_constraint_graph",str(public))

    def test_evaluator_measures_real_result_interface_not_candidate_metrics(self):
        measured=cad_measure_result(_CadResult())
        self.assertEqual(measured["volume"],6000.0)
        self.assertEqual(measured["surface_area"],2200.0)
        self.assertEqual(measured["bbox"],[10.0,20.0,30.0])
        self.assertEqual(measured["topology_counts"],{"faces":6,"edges":12,"vertices":8})
        case={"_oracle":{
            "identifiable":True,
            "reference_constraint_graph":{"x":1},
            "reference_geometry_metrics":{
                "volume":6000.0,"surface_area":2200.0,"bbox":[10.0,20.0,30.0],
                "topology_counts":{"faces":6,"edges":12,"vertices":8},
            },
            "required_geometry_metrics":["volume","surface_area","bbox","topology_counts"],
            "metric_tolerances":{
                "volume":{"abs":0.05,"rel":1e-7},
                "surface_area":{"abs":0.05,"rel":1e-7},
                "bbox":{"abs":0.01,"rel":1e-7},
                "topology_counts":{"abs":0,"rel":0},
            },
        }}
        candidate={
            "status":"SOLID",
            "constraint_graph":{"x":1},
            "candidate_geometry_metrics":{"volume":1.0},
        }
        obs=cad_observe_candidate(case,candidate,_CadResult())
        self.assertTrue(obs["candidate_solid_valid"])
        self.assertTrue(obs["end_to_end_final_geometry_correct"])
        self.assertEqual(obs["candidate_geometry_metrics"]["volume"],6000.0)

    def test_constructive_nonidentifiability_witness_fails_closed(self):
        case={"_oracle":{"identifiable":False,"ambiguity_parameter":"depth_mm"}}
        good={"status":"NONIDENTIFIABLE","ambiguity_witness":{"parameter":"depth_mm","alternatives":[10,20]}}
        bad={"status":"NONIDENTIFIABLE","ambiguity_witness":{"parameter":"depth_mm","alternatives":[10,10]}}
        self.assertTrue(cad_validate_ambiguity_witness(case,good))
        self.assertFalse(cad_validate_ambiguity_witness(case,bad))


import tempfile
import cad_t0_post_refreeze_composition_guard_v2 as cad_v2_guard

class CadPostRefreezeCompositionExactBrainTests(unittest.TestCase):
    def test_exact_guard_and_authority_blobs(self):
        expected={
            "independent/cad_t0_post_refreeze_composition_guard_v2.py":"46ce4df48c96a46415710d0fd9caec8d66435a78",
            "independent/cad_t0_candidate_freeze_v2.json":"039056ad65c1721d871d378ff0497fc461ab4df2",
            "independent/cad_t0_post_refreeze_binding_v2.json":"7a6f04e08587ff5471ab406c04ab8acd76cc16eb",
            "independent/m1a_positioned_ocr_bridge_receipt.json":"949612638affa5891fe74517ad6b83371a783f69",
            "independent/cad_t0_population_oracle_receipt.json":"d27aece637d10e46bff72b762f5743d5048c7af0",
        }
        for p,sha in expected.items():
            self.assertEqual(_git_blob_sha(p),sha,p)

    def test_exact_post_refreeze_composition_guard_passes(self):
        mirrors={
            "independent/cad_t0_candidate_freeze_v2.json":cad_v2_guard.FREEZE,
            "independent/cad_t0_post_refreeze_binding_v2.json":cad_v2_guard.BINDING,
            "independent/m1a_positioned_ocr_bridge_receipt.json":cad_v2_guard.OCR_RECEIPT,
            "independent/cad_t0_population_oracle_receipt.json":cad_v2_guard.POP_RECEIPT,
        }
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            for src,dst in mirrors.items():
                target=root/dst
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(Path(src).read_bytes())
            out=cad_v2_guard.evaluate(root)
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["prewave_route_ready_for_promotion_law"])
        self.assertFalse(out["execution_authority"])
        self.assertEqual(out["terminal_results_observed"],0)
        self.assertEqual(out["fresh_terminal_evidence_consumed"],0)
