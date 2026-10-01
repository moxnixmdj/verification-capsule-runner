import hashlib, json, re, unittest
from pathlib import Path
from requirement_graph_kernel_v3 import compile_requirement_contract, requirement_mutation_score
from independent_acceptance_model_v3 import assess

ROOT=Path(__file__).resolve().parent
CONTRACT=json.loads((ROOT/"wdm_stage_b_v3.json").read_text())
RAW=(ROOT/"wdm_instruction.md").read_bytes()
TEXT=RAW.decode("utf-8")

def git_blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def source_units(text: str):
    text=text.replace("\r\n","\n").strip()
    return [x.strip() for x in re.split(r"\n[ \t]*\n+",text) if x.strip()]

class StageBV3(unittest.TestCase):
    def test_pinned_instruction_identity_and_block_accounting(self):
        self.assertEqual(git_blob_sha1(RAW),"ab7255e9b4cf9597e965e2fe385447e502c4e8f9")
        units=source_units(TEXT)
        self.assertEqual(len(units),12)
        acct=CONTRACT["source_accounting"]
        self.assertEqual(acct["instruction_blob_sha256"] if "instruction_blob_sha256" in acct else acct["instruction_blob_sha"],
                         "ab7255e9b4cf9597e965e2fe385447e502c4e8f9")
        rows=acct["units"]
        self.assertEqual([r["id"] for r in rows],[f"U{i:02d}" for i in range(1,13)])
        self.assertEqual(len({r["id"] for r in rows}),12)
        self.assertEqual(rows[0]["class"],"non_requirement")
        self.assertTrue(all(r["requirements"] for r in rows[1:]))

    def test_every_requirement_has_source_support(self):
        req_ids={r["id"] for r in CONTRACT["normalized_requirements"]}
        mapped=set()
        for row in CONTRACT["source_accounting"]["units"]:
            for rid in row["requirements"]:
                self.assertIn(rid,req_ids)
                mapped.add(rid)
        self.assertEqual(mapped,req_ids)

    def test_requirement_graph_and_seeded_mutations(self):
        reqs=CONTRACT["normalized_requirements"]
        ids=[r["id"] for r in reqs]
        compiled=compile_requirement_contract(reqs,expected_required_ids=ids)
        self.assertTrue(compiled["pass"],compiled)
        mutation=requirement_mutation_score(reqs)
        self.assertTrue(mutation["pass"],mutation)
        self.assertEqual(mutation["survived"],0)

    def test_independent_acceptance_covers_all_generated_obligations(self):
        out=assess({
            "requirements":CONTRACT["normalized_requirements"],
            "checks":CONTRACT["independent_acceptance_plan"]["checks"],
        })
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["failed_requirements"],[])

    def test_material_requirement_is_explicit_and_independently_covered(self):
        req={r["id"]:r for r in CONTRACT["normalized_requirements"]}
        self.assertIn("R16_MATERIAL_INDICES",req)
        self.assertEqual(set(req["R16_MATERIAL_INDICES"]["must_detect_failure_modes"]),
                         {"wrong_core_effective_index","wrong_cladding_index"})
        checks=CONTRACT["independent_acceptance_plan"]["checks"]
        a08=[c for c in checks if c["id"]=="A08_MATERIAL_INDICES"]
        self.assertEqual(len(a08),1)
        self.assertEqual(a08[0]["covers"],["R16_MATERIAL_INDICES"])
        self.assertEqual(set(a08[0]["detects"]),
                         {"wrong_core_effective_index","wrong_cladding_index"})

    def test_bounded_literal_consensus_against_official_source(self):
        # Independent literal anchors for the explicit numerical/configuration facts.
        fragments=[
            r"n_\text{core}=2.85",
            r"n_\text{clad}=1.44",
            "eig_parity = mp.ODD_Z",
            "mp.EVEN_Z",
            r"[1.50, 1.54]",
            r"[1.56, 1.60]",
            r"\geq 0.87",
            r"\leq 0.15",
            "single-simulation self-normalization",
            r"\\left|s_\\text{out}^{+}/s_\\text{in}^{+}\\right|^2",
            "/app/design.npy",
            "float64",
            r"\rho<0.05",
            r"\rho>0.95",
            "8-connected components",
            r"0.06\ \mu\text{m}",
            r"0.12\ \mu\text{m}",
            r"[0.30, 0.60]",
            r"[2.0, 3.2]",
            "[32, 256]",
            "R \\in [15, 30]",
            r"\geq 0.30\ \mu\text{m}",
            r"PML thickness $0.8\ \mu\text{m}$",
            r"straight waveguide extension $1.0\ \mu\text{m}$",
            r"vertical padding $0.6\ \mu\text{m}$",
            'grid_type="U_MEAN"',
            "eig_band=1",
            "direction=mp.NO_DIRECTION",
            "eig_kpoint=mp.Vector3(1,0,0)",
            "1/1.58",
            "1/1.52",
            "stop_when_dft_decayed(tol=1e-4)",
            "alpha[0, :, 0]",
            "28800 seconds",
        ]
        missing=[x for x in fragments if x not in TEXT]
        self.assertEqual(missing,[])

        b=CONTRACT["behavioral_contract"]
        self.assertEqual(b["materials"]["core_effective_index"],2.85)
        self.assertEqual(b["materials"]["cladding_index"],1.44)
        self.assertEqual(b["polarization"]["meep_eig_parity"],"mp.ODD_Z")
        self.assertEqual(b["performance"][0]["mean_transmission_gte"],0.87)
        self.assertEqual(b["performance"][1]["other_output_leakage_lte"],0.15)

    def test_v3_remains_fail_closed_before_stage_b_completion(self):
        self.assertFalse(CONTRACT["task_execution_authorized"])
        self.assertIn("PENDING",CONTRACT["independent_literal_consensus"]["status"])
        self.assertFalse(CONTRACT["cheap_deterministic_precheck"]["pass"])

if __name__=="__main__":
    unittest.main(verbosity=2)
