import ast
import hashlib
import json
import math
import pathlib
import sys
import unittest

ROOT=pathlib.Path(__file__).parent
sys.path.insert(0,str(ROOT))
from source_contract_compiler import SourceAtom, atomize_source, validate_contract_coverage

CONTRACT=json.loads((ROOT/"contract.json").read_text())
CANDIDATE=(ROOT/"candidate_answer.py").read_bytes()

REQ_TEXT={
"I_ARTIFACTS":"Required output artifacts and base/edit derivation.",
"I_TREE":"Exactly one PartDesign Body, named feature tree, one solid, no baked Part::Feature.",
"I_GEOMETRY":"Ordered closed spring-clip 2D profile with specified arcs/lines/tangencies and extrusion.",
"I_REL":"All stated parameter equalities and inequalities hold in both files.",
"I_BASE":"All base parameter values and units are exact.",
"I_EDIT":"Only four stated edit parameters change and all other parameters are unchanged.",
"I_BOUNDARY":"Time and no-online-task-specific-hints boundary.",
"T_SCHEMA":"Task schema version.","T_ARTIFACTS":"Artifact list.","T_BEHAVIOR":"Task behavior.",
"T_VERIFIER":"Verifier mode and timeout.","T_AGENT":"Agent timeout.","T_ENV":"Resource envelope.",
"D_ENV":"Exact FreeCAD task execution surface."
}

def source_paths():
    root=pathlib.Path(sys.argv[1]) if len(sys.argv)>1 and pathlib.Path(sys.argv[1]).exists() else ROOT/"authoritative"
    return root

def build_contract_for_source(spec,text,source_name):
    atoms=atomize_source(text,source_name)
    by_line={i+1:a for i,a in enumerate(atoms)}
    reqs=[]
    atom_to_reqs={}
    if "all_nonblank_noncomment_requirement" in spec:
        rid=spec["all_nonblank_noncomment_requirement"]
        lines=[i for i,a in by_line.items() if a.text.strip() and not a.text.lstrip().startswith("#")]
        reqs.append({"id":rid,"text":REQ_TEXT[rid],"source_atom_ids":[by_line[i].atom_id for i in lines]})
        for i in lines: atom_to_reqs.setdefault(by_line[i].atom_id,[]).append(rid)
        kind_map={rid:spec["kind"]}
    else:
        kind_map=spec["kind_by_requirement"]
        for rid,lines in spec["requirement_lines"].items():
            reqs.append({"id":rid,"text":REQ_TEXT[rid],"source_atom_ids":[by_line[i].atom_id for i in lines]})
            for i in lines: atom_to_reqs.setdefault(by_line[i].atom_id,[]).append(rid)
    dispositions=[]
    for a in atoms:
        rids=atom_to_reqs.get(a.atom_id,[])
        if rids:
            kind=kind_map[rids[0]]
            if any(kind_map[r]!=kind for r in rids):
                kind="BEHAVIOR"
            dispositions.append({"atom_id":a.atom_id,"kind":kind,
              "rationale":"Operative authoritative source atom preserved in normalized requirement graph.",
              "requirement_ids":rids})
        else:
            dispositions.append({"atom_id":a.atom_id,"kind":"INFORMATIVE",
              "rationale":"Formatting, canary, metadata, or non-operative source text; no required behavior discarded.",
              "requirement_ids":[]})
    return atoms,dispositions,reqs

class StageB(unittest.TestCase):
    def test_candidate_hash_and_syntax(self):
        git_blob=hashlib.sha1(b"blob "+str(len(CANDIDATE)).encode()+b"\\0"+CANDIDATE).hexdigest()\n        self.assertEqual(git_blob,CONTRACT["candidate_answer_git_blob"])
        compile(CANDIDATE.decode(),"<candidate>","exec")

    def test_lossless_sources_and_zero_open_holes(self):
        root=source_paths()
        files={"instruction.md":root/"instruction.md","task.toml":root/"task.toml","Dockerfile":root/"Dockerfile"}
        for name,path in files.items():
            text=path.read_text()
            atoms,disp,reqs=build_contract_for_source(CONTRACT["source_contracts"][name],text,
                {"instruction.md":"tasks/freecad-spring-clip/instruction.md",
                 "task.toml":"tasks/freecad-spring-clip/task.toml",
                 "Dockerfile":"tasks/freecad-spring-clip/environment/Dockerfile"}[name])
            errors=validate_contract_coverage(source_text=text,atoms=atoms,dispositions=disp,requirements=reqs)
            self.assertEqual(errors,[],(name,errors))

    def test_source_compiler_fails_on_missing_atom(self):
        root=source_paths(); text=(root/"instruction.md").read_text()
        atoms,disp,reqs=build_contract_for_source(CONTRACT["source_contracts"]["instruction.md"],text,
            "tasks/freecad-spring-clip/instruction.md")
        disp=disp[:-1]
        errors=validate_contract_coverage(source_text=text,atoms=atoms,dispositions=disp,requirements=reqs)
        self.assertTrue(any(e.startswith("UNACCOUNTED_SOURCE_ATOM") for e in errors))

    def test_source_compiler_fails_if_geometry_marked_informative(self):
        root=source_paths(); text=(root/"instruction.md").read_text()
        atoms,disp,reqs=build_contract_for_source(CONTRACT["source_contracts"]["instruction.md"],text,
            "tasks/freecad-spring-clip/instruction.md")
        geom_atom=atoms[9].atom_id
        for d in disp:
            if d["atom_id"]==geom_atom:
                d["kind"]="INFORMATIVE"; d["requirement_ids"]=[]
        errors=validate_contract_coverage(source_text=text,atoms=atoms,dispositions=disp,requirements=reqs)
        self.assertTrue(any("NORMATIVE_OR_HIGH_RISK_ATOM_MARKED_INFORMATIVE" in e for e in errors))

    def test_parameter_invariants_and_exact_edit_delta(self):
        n=CONTRACT["normalized_contract"]; b=n["base"]; e=n["edit"]
        for p in (b,e):
            self.assertAlmostEqual(p["outer_bend_radius"],p["inner_bend_radius"]+p["clip_wall_thickness"],places=9)
            self.assertAlmostEqual(p["overall_leg_span"],2*p["outer_bend_radius"],places=9)
            self.assertGreater(p["leg_length"],2*p["retention_lobe_center_offset"]+p["inner_bend_radius"])
            self.assertLess(p["tip_fillet_radius"],p["clip_width"])
            self.assertLess(p["tip_fillet_radius"],p["outer_bend_radius"])
            self.assertLess(p["tab_transition_arc_radius"],p["retention_lobe_center_offset"])
            self.assertLess(p["retention_lobe_center_offset"],p["leg_length"])
            self.assertLess(p["lobe_arc_span_angle"],180)
        changed=sorted(k for k in b if b[k]!=e[k])
        self.assertEqual(changed,sorted(n["edit_only_keys"]))

    def test_candidate_structure_static(self):
        text=CANDIDATE.decode()
        tree=ast.parse(text)
        calls=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute):
                if node.func.attr in {"addObject","newObject"} and node.args and isinstance(node.args[0],ast.Constant):
                    calls.append(node.args[0].value)
        self.assertIn("PartDesign::Body",calls)
        self.assertIn("Sketcher::SketchObject",calls)
        self.assertIn("PartDesign::Feature",calls)
        self.assertNotIn("Part::Feature",calls)
        for artifact in ("answer_base.FCStd","answer_edit.FCStd"):
            self.assertIn(artifact,text)

    def test_geometry_certificates_are_positive_and_simple(self):
        gp=CONTRACT["geometry_plan"]
        for key in ("base_certificate","edit_certificate"):
            c=gp[key]
            self.assertTrue(c["valid_simple_closed_profile"])
            self.assertGreater(c["area_mm2_approx"],0)
            self.assertGreater(c["inner_tangent_line_length_mm"],0)
            self.assertGreater(c["transition_turn_deg"],0)
            self.assertGreater(c["connector_turn_deg"],0)

if __name__=="__main__":
    unittest.main(argv=[sys.argv[0]],verbosity=2)
