import json, math
from pathlib import Path

HERE=Path(__file__).parent
C=json.loads((HERE/"contract.json").read_text())
S=json.loads((HERE/"source_accounting.json").read_text())
instruction=(HERE/"instruction.md").read_text()
task_toml=(HERE/"task.toml").read_text()
docker=(HERE/"Dockerfile").read_text()

def merged_params():
    b=dict(C["base_parameters"])
    e=dict(b); e.update(C["edit_substitutions"])
    return b,e

def check_invariants(p):
    assert math.isclose(p["outer_bend_radius"],p["inner_bend_radius"]+p["clip_wall_thickness"],abs_tol=1e-9)
    assert math.isclose(p["overall_leg_span"],2*p["outer_bend_radius"],abs_tol=1e-9)
    assert p["leg_length"] > 2*p["retention_lobe_center_offset"]+p["inner_bend_radius"]
    assert p["tip_fillet_radius"] < p["clip_width"]
    assert p["tip_fillet_radius"] < p["outer_bend_radius"]
    assert p["tab_transition_arc_radius"] < p["retention_lobe_center_offset"]
    assert p["retention_lobe_center_offset"] < p["leg_length"]
    assert p["lobe_arc_span_angle"] < 180

def test_exact_fetch_only_boundary():
    info=S["information_boundary"]
    assert info["mode"]=="EXACT_FETCH_ONLY"
    for k in ("discovery_search_after_stage_b","task_specific_external_search","solution_read","tests_read","hidden_verifier_read","task_command_executed"):
        assert info[k] is False

def test_contract_matches_mirrored_exact_sources_without_network():
    for name,value in C["base_parameters"].items():
        assert str(value) in instruction,(name,value)
    for name,value in C["edit_substitutions"].items():
        assert str(value) in instruction,("edit",name,value)
    for path in C["artifacts"]:
        assert path in instruction or path in task_toml
    for token in ["PartDesign","Body","single solid","tangent","spring clip","answer_base.FCStd","answer_edit.FCStd"]:
        assert token.lower() in (instruction+"\n"+task_toml).lower(),token
    assert "freecad" in docker.lower()
    assert "0.21.2" in docker

def test_base_and_edit_invariants_and_exact_delta():
    b,e=merged_params(); check_invariants(b); check_invariants(e)
    changed={k for k in b if b[k]!=e[k]}
    assert changed==set(C["edit_substitutions"])
    assert (set(b)-changed)==set(C["unchanged_on_edit"])

def test_geometry_and_mutation_closure():
    assert len(C["geometric_semantics"])>=11
    assert len(C["independent_acceptance_obligations"])>=10
    assert set(C["mutation_kill_set"])=={
      "EDIT_INNER_RADIUS_WITHOUT_COMPENSATING_WALL_THICKNESS",
      "EDIT_UNDECLARED_PARAMETER","OMIT_ONE_REQUIRED_PROFILE_SEGMENT",
      "BREAK_DECLARED_TANGENCY","USE_PART_FEATURE_BAKED_SHAPE",
      "CREATE_MULTIPLE_BODIES","CREATE_MULTIPLE_SOLIDS",
      "WRONG_PAD_WIDTH","WRONG_ARTIFACT_PATH","FAIL_TO_SAVE_BOTH_BASE_AND_EDIT_FILES"
    }
    assert C["task_execution_authorized"] is False
