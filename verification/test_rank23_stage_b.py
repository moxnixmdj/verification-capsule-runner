import hashlib
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).parent

def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

class Rank23StageBTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract=json.loads((ROOT/"rank23_contract.json").read_text())
        cls.accounting=json.loads((ROOT/"rank23_source_accounting.json").read_text())
        cls.instr=(ROOT/"rank23_sources"/"instruction.md").read_bytes()
        cls.toml=(ROOT/"rank23_sources"/"task.toml").read_bytes()
        cls.docker=(ROOT/"rank23_sources"/"Dockerfile").read_bytes()

    def test_exact_official_source_blobs(self):
        self.assertEqual(git_blob_sha(self.instr),"3ed0e79d6aaef27f429320a7fa38d3be59ade47a")
        self.assertEqual(git_blob_sha(self.toml),"c4638fc1d13ec61cc411ccc4c9a5ae0049a29080")
        self.assertEqual(git_blob_sha(self.docker),"45adbfbc0749b41b9706544d8484859ed5bb150e")

    def test_accounting_matches_exact_sources_and_forbids_execution(self):
        a=self.accounting
        got={x["path"]:x["blob"] for x in a["authoritative_sources"]}
        self.assertEqual(got,{
          "tasks/layout-config-recreation2/instruction.md":"3ed0e79d6aaef27f429320a7fa38d3be59ade47a",
          "tasks/layout-config-recreation2/task.toml":"c4638fc1d13ec61cc411ccc4c9a5ae0049a29080",
          "tasks/layout-config-recreation2/environment/Dockerfile":"45adbfbc0749b41b9706544d8484859ed5bb150e",
        })
        b=a["information_boundary"]
        for k in ("discovery_search_after_stage_b","task_specific_external_search","solution_read","tests_read","hidden_verifier_read","task_command_executed"):
            self.assertFalse(b[k],k)
        self.assertFalse(a["task_execution_authorized"])

    def test_instruction_core_semantics_are_losslessly_represented(self):
        text=self.instr.decode()
        c=self.contract
        bc=c["behavioral_contract"]
        joined=json.dumps(c)
        required_literals=[
          "/app/data/layout.png",
          "/app/data/components/",
          "/app/output/config.json",
          "components/component_*.png",
          "Google Fonts",
          "index 0 is bottom layer",
          "98",
        ]
        for lit in required_literals:
            self.assertIn(lit,text)
        self.assertIn("/app/output/config.json",bc["required_output_or_action"])
        self.assertIn("98%",bc["success_condition"])
        self.assertIn("bottom layer",json.dumps(c["behavioral_requirements"]))
        self.assertIn("Google Fonts",json.dumps(c["behavioral_requirements"]))

    def test_all_behavioral_requirements_present_and_critical(self):
        reqs={r["id"]:r for r in self.contract["behavioral_requirements"]}
        self.assertEqual(set(reqs),{
          "R1_OUTPUT_ARTIFACT","R2_LAYER_ORDER","R3_IMAGE_COMPONENT_SCHEMA",
          "R4_TEXT_COMPONENT_SCHEMA","R5_CANVAS_STYLE","R6_COMPONENT_GEOMETRY",
          "R7_TEXT_APPEARANCE","R8_RENDER_EQUIVALENCE","R9_NO_TASK_SPECIFIC_CHEATING"
        })
        self.assertTrue(all(r["critical"] for r in reqs.values()))

    def test_schema_failure_classes_covered(self):
        joined=json.dumps(self.contract["behavioral_requirements"])
        for fragment in [
          "components/component_*.png","opacity","scale","plain editable text",
          "Google Fonts","textTransform","textAlign","background","pixel identical fraction"
        ]:
            self.assertIn(fragment,joined)

    def test_mutation_kill_set_covers_material_failure_modes(self):
        muts=set(self.contract["mutation_kill_set"])
        required={
          "PERMUTE_TWO_OVERLAPPING_LAYERS",
          "REPLACE_IMAGE_SRC_WITH_NONPROVIDED_PATH",
          "OMIT_REQUIRED_IMAGE_COMPONENT",
          "SHIFT_TRANSLATE_X_OR_Y",
          "ALTER_RENDERED_WIDTH_OR_HEIGHT",
          "FLIP_REQUIRED_MIRROR_SIGN",
          "ALTER_OPACITY",
          "RASTERIZE_REQUIRED_TEXT_AS_IMAGE",
          "CHANGE_TEXT_STRING",
          "USE_NON_GOOGLE_FONT",
          "PERTURB_FONT_SIZE",
          "CHANGE_CANVAS_WIDTH_OR_HEIGHT",
          "CHANGE_BACKGROUND_COLOR",
          "WRITE_WRONG_OUTPUT_PATH",
          "MALFORM_CONFIG_JSON",
          "REDUCE_RENDER_SIMILARITY_BELOW_0_98",
        }
        self.assertTrue(required.issubset(muts),sorted(required-muts))

    def test_contract_remains_preexecution_only(self):
        self.assertFalse(self.contract["task_execution_authorized"])
        self.assertFalse(self.contract["terminal_verifier_authorized"])
        self.assertFalse(self.contract["hidden_verifier_read"])
        unresolved=set(self.contract["unresolved_before_any_stage_c_execution"])
        self.assertTrue(any("GLOBAL_MINIMUM_REALITY_CUT" in x for x in unresolved))
        self.assertTrue(any("INDEPENDENT STRUCTURAL" in x for x in unresolved))

if __name__=="__main__":
    unittest.main()
