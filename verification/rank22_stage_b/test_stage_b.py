import hashlib, importlib.util, json, math, unittest
from pathlib import Path

ROOT=Path(__file__).parent

def loadmod(name,path):
    s=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

scc=loadmod("scc",ROOT/"source_contract_compiler.py")
iam=loadmod("iam",ROOT/"independent_acceptance_model.py")
contract=json.loads((ROOT/"contract.json").read_text())
account=json.loads((ROOT/"source_accounting.json").read_text())

SOURCES={
 "instruction_md":ROOT/"instruction.md",
 "task_toml":ROOT/"task.toml",
 "environment_Dockerfile":ROOT/"Dockerfile",
}
EXPECTED_BLOBS={
 "instruction_md":"4d80d20b8d6404e68728efda4dfd79d315a9d20d",
 "task_toml":"4fa89d7788a5d56f3d073ce54d46dcdad0a7b012",
 "environment_Dockerfile":"1bb433cd0994aa4f88e4e9d52040fd880e59b919",
}
def git_blob(b):
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def lines_for(spec,n):
    out={}
    for k,v in spec.items():
        if "-" in k:
            a,b=map(int,k.split("-",1))
            for i in range(a,b+1): out[i]=v
        else: out[int(k)]=v
    assert set(out)==set(range(1,n+1)),(sorted(set(range(1,n+1))-set(out)),sorted(set(out)-set(range(1,n+1))))
    return out
def kind_and_req(label):
    if ":" in label:
        k,r=label.split(":",1); return k,r
    return "INFORMATIVE",None

class StageB(unittest.TestCase):
  def test_exact_source_blobs(self):
    for name,p in SOURCES.items():
      self.assertEqual(git_blob(p.read_bytes()),EXPECTED_BLOBS[name])

  def test_lossless_source_contract_zero_holes(self):
    for name,p in SOURCES.items():
      text=p.read_text()
      atoms=scc.atomize_source(text,p.name)
      self.assertEqual(scc.reconstruct_source(atoms),text)
      mapping=lines_for(account["source_line_dispositions"][name],len(atoms))
      dispositions=[]; byreq={}
      for i,a in enumerate(atoms,1):
        k,r=kind_and_req(mapping[i])
        d={"atom_id":a.atom_id,"kind":k,"rationale":mapping[i],"requirement_ids":[]}
        if r:
          d["requirement_ids"]=[r]; byreq.setdefault(r,[]).append(a.atom_id)
        dispositions.append(d)
      requirements=[{"id":r,"source_atom_ids":ids} for r,ids in sorted(byreq.items())]
      errors=scc.validate_contract_coverage(
        source_text=text,atoms=atoms,dispositions=dispositions,requirements=requirements
      )
      self.assertEqual(errors,[],(name,errors))

  def test_base_and_edit_invariants_exact(self):
    b=contract["base_parameters"]; e=dict(b); e.update(contract["edit_substitutions"])
    for x in (b,e):
      self.assertAlmostEqual(x["outer_bend_radius"],x["inner_bend_radius"]+x["clip_wall_thickness"],places=12)
      self.assertAlmostEqual(x["overall_leg_span"],2*x["outer_bend_radius"],places=12)
      self.assertGreater(x["leg_length"],2*x["retention_lobe_center_offset"]+x["inner_bend_radius"])
      self.assertLess(x["tip_fillet_radius"],x["clip_width"])
      self.assertLess(x["tip_fillet_radius"],x["outer_bend_radius"])
      self.assertLess(x["tab_transition_arc_radius"],x["retention_lobe_center_offset"])
      self.assertLess(x["retention_lobe_center_offset"],x["leg_length"])
      self.assertLess(x["lobe_arc_span_angle"],180)
    changed={k for k in b if b[k]!=e[k]}
    self.assertEqual(changed,set(contract["edit_substitutions"]))
    self.assertEqual(set(contract["unchanged_on_edit"]),set(b)-changed)

  def test_independent_acceptance_plan_covers_generic_failure_modes(self):
    reqs=[
      {"id":"ART","critical":True,"transform_kinds":["artifact"],"builder_dependencies":["builder:answer.py"]},
      {"id":"GEO","critical":True,"transform_kinds":["geometry_reconstruction"],"builder_dependencies":["builder:profile-construction"]},
      {"id":"INV","critical":True,"transform_kinds":["numeric_formula"],"builder_dependencies":["builder:parameter-relations"]},
      {"id":"EDIT","critical":True,"transform_kinds":["state_transition"],"builder_dependencies":["builder:edit-generation"]},
    ]
    checks=[
      {"id":"fcstd-independent-inspector","covers":["ART"],"provenance":"independent_oracle","dependencies":["raw:fcstd-files","oracle:freecad-document-inspector"],"detects":["existence","schema","roundtrip_or_parse"]},
      {"id":"shape-independent-inspector","covers":["GEO"],"provenance":"independent_oracle","dependencies":["raw:fcstd-files","oracle:topology-curvature-inspector"],"detects":["global_mass_property","topology","envelope","curvature","watertightness"]},
      {"id":"parameter-independent-arithmetic","covers":["INV"],"provenance":"independent_oracle","dependencies":["raw:named-parameter-values","oracle:stdlib-arithmetic"],"detects":["unit_or_scale","boundary_or_extreme","alternate_derivation"]},
      {"id":"base-edit-independent-differencer","covers":["EDIT"],"provenance":"independent_oracle","dependencies":["raw:base-edit-parameter-dumps","oracle:document-differencer"],"detects":["ordering_precedence","idempotence","failure_recovery"]},
    ]
    out=iam.assess({"requirements":reqs,"checks":checks})
    self.assertTrue(out["pass"],out)

  def test_contract_closes_known_shortcuts(self):
    required={
      "EDIT_INNER_RADIUS_WITHOUT_COMPENSATING_WALL_THICKNESS",
      "EDIT_UNDECLARED_PARAMETER","OMIT_ONE_REQUIRED_PROFILE_SEGMENT",
      "BREAK_DECLARED_TANGENCY","USE_PART_FEATURE_BAKED_SHAPE",
      "CREATE_MULTIPLE_BODIES","CREATE_MULTIPLE_SOLIDS",
      "WRONG_PAD_WIDTH","WRONG_ARTIFACT_PATH","FAIL_TO_SAVE_BOTH_BASE_AND_EDIT_FILES"
    }
    self.assertTrue(required <= set(contract["mutation_kill_set"]))
    self.assertFalse(contract["task_execution_authorized"])
    self.assertFalse(contract["hidden_verifier_read"])
    self.assertEqual(account["information_boundary"]["mode"],"EXACT_FETCH_ONLY")
    self.assertFalse(account["information_boundary"]["discovery_search_after_stage_b"])

if __name__=="__main__": unittest.main(verbosity=2)
