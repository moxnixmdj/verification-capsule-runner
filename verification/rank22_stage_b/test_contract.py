import json, math, re, subprocess, tempfile
from pathlib import Path

HERE=Path(__file__).parent
C=json.loads((HERE/"FREECAD_SPRING_CLIP_RANK22_STAGE_B_CONTRACT_V1.json").read_text())
S=json.loads((HERE/"FREECAD_SPRING_CLIP_RANK22_STAGE_B_SOURCE_ACCOUNTING_V1.json").read_text())
REF="452bf305c6daa62fc59061d22133a7cbc7c1572e"

def git_show(path):
    with tempfile.TemporaryDirectory() as td:
        subprocess.run(["git","clone","--filter=blob:none","--no-checkout","https://github.com/harbor-framework/terminal-bench.git",td],check=True,stdout=subprocess.DEVNULL)
        return subprocess.check_output(["git","-C",td,"show",f"{REF}:{path}"],text=True)

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

def test_lossless_source_boundary():
    info=S["information_boundary"]
    assert info["mode"]=="EXACT_FETCH_ONLY"
    for k in ("discovery_search_after_stage_b","task_specific_external_search","solution_read","tests_read","hidden_verifier_read","task_command_executed"):
        assert info[k] is False
    assert S["environment_tree"]["enumerated_exactly"] is True
    assert S["environment_tree"]["entry_count"]==1
    assert S["environment_tree"]["unaccounted_entries"]==0
    src={x["path"]:x["blob"] for x in S["authoritative_sources"]}
    assert src=={
      "tasks/freecad-spring-clip/instruction.md":"4d80d20b8d6404e68728efda4dfd79d315a9d20d",
      "tasks/freecad-spring-clip/task.toml":"4fa89d7788a5d56f3d073ce54d46dcdad0a7b012",
      "tasks/freecad-spring-clip/environment/Dockerfile":"1bb433cd0994aa4f88e4e9d52040fd880e59b919",
    }

def test_contract_matches_official_instruction_literals_and_artifacts():
    instruction=git_show("tasks/freecad-spring-clip/instruction.md")
    task_toml=git_show("tasks/freecad-spring-clip/task.toml")
    docker=git_show("tasks/freecad-spring-clip/environment/Dockerfile")
    # Every task numeric parameter and edited value must be grounded in official bytes.
    for name,value in C["base_parameters"].items():
        token=str(value)
        assert token in instruction, (name,token)
    for name,value in C["edit_substitutions"].items():
        token=str(value)
        assert token in instruction, ("edit",name,token)
    for path in C["artifacts"]:
        assert path in instruction or path in task_toml
    # Critical parametric/geometry nouns must be source-grounded, not invented.
    for token in ["PartDesign","Body","single solid","tangent","spring clip","answer_base.FCStd","answer_edit.FCStd"]:
        assert token.lower() in (instruction+"\n"+task_toml).lower(), token
    assert "freecad" in docker.lower()
    assert "0.21.2" in docker

def test_base_and_edit_invariants_and_exact_delta():
    b,e=merged_params()
    check_invariants(b); check_invariants(e)
    changed={k for k in b if b[k]!=e[k]}
    assert changed==set(C["edit_substitutions"])
    unchanged=set(b)-changed
    assert unchanged==set(C["unchanged_on_edit"])
    assert math.isclose(b["leg_length"]-(2*b["retention_lobe_center_offset"]+b["inner_bend_radius"]),0.574929,abs_tol=1e-9)
    assert math.isclose(e["leg_length"]-(2*e["retention_lobe_center_offset"]+e["inner_bend_radius"]),0.3,abs_tol=1e-9)

def test_structural_and_geometry_acceptance_is_not_local_only():
    model=set(C["model_requirements"])
    assert {
      "EXACTLY_ONE_PARTDESIGN_BODY_PER_FCSTD",
      "FEATURE_TREE_DRIVEN_BY_NAMED_DOCUMENT_OBJECTS",
      "SINGLE_SOLID_FINAL_BODY",
      "NO_BAKED_PART_FEATURE_AS_MODEL",
      "ONE_CLOSED_2D_SIDE_PROFILE_EXTRUDED_ALONG_CLIP_WIDTH",
    } <= model
    geo=set(C["geometric_semantics"])
    required={
      "RIGHT_HAND_CONVEX_OUTER_BRIDGE_ARC",
      "TWO_STRAIGHT_OUTER_LEGS_EXTENDING_LEFT",
      "CHAMFERED_LEG_TIPS_WITH_SMALL_TIP_FILLETS",
      "EACH_TIP_CHAMFER_TANGENT_TO_ITS_TIP_FILLET_AT_OUTER_ENDPOINT",
      "LEFT_CONCAVE_RETENTION_LOBES",
      "TAB_TO_LOBE_TRANSITION_FILLETS_TANGENT_TO_RETENTION_LOBES_AND_INNER_CONNECTOR_ARCS",
      "SLOPED_INNER_LINES_TANGENT_TO_INNER_CONNECTOR_ARCS_AND_INNER_BRIDGE",
      "RIGHT_CONCAVE_INNER_BRIDGE_ARC_CLOSES_PROFILE",
      "RETENTION_LOBE_INNER_CONNECTOR_AND_INNER_BRIDGE_SHARE_INNER_BEND_RADIUS",
      "SMOOTH_CONTINUOUS_INNER_CURVE_ON_EACH_SIDE",
      "PAD_OR_EQUIVALENT_PARTDESIGN_EXTRUSION_LENGTH_EQUALS_CLIP_WIDTH",
    }
    assert required <= geo

def test_mutation_suite_attacks_parametric_structure_geometry_and_artifacts():
    muts=set(C["mutation_kill_set"])
    assert {
      "EDIT_INNER_RADIUS_WITHOUT_COMPENSATING_WALL_THICKNESS",
      "EDIT_UNDECLARED_PARAMETER",
      "OMIT_ONE_REQUIRED_PROFILE_SEGMENT",
      "BREAK_DECLARED_TANGENCY",
      "USE_PART_FEATURE_BAKED_SHAPE",
      "CREATE_MULTIPLE_BODIES",
      "CREATE_MULTIPLE_SOLIDS",
      "WRONG_PAD_WIDTH",
      "WRONG_ARTIFACT_PATH",
      "FAIL_TO_SAVE_BOTH_BASE_AND_EDIT_FILES",
    } == muts
