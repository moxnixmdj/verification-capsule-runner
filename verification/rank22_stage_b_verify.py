from __future__ import annotations
import copy, json, math
from pathlib import Path

REQUIRED_MODEL={
 "EXACTLY_ONE_PARTDESIGN_BODY_PER_FCSTD",
 "FEATURE_TREE_DRIVEN_BY_NAMED_DOCUMENT_OBJECTS",
 "SINGLE_SOLID_FINAL_BODY",
 "NO_BAKED_PART_FEATURE_AS_MODEL",
 "ONE_CLOSED_2D_SIDE_PROFILE_EXTRUDED_ALONG_CLIP_WIDTH",
}
REQUIRED_GEOM={
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
REQUIRED_ARTIFACTS={"/app/answer.py","/app/answer_base.FCStd","/app/answer_edit.FCStd"}
REQUIRED_MUTATIONS={
 "EDIT_INNER_RADIUS_WITHOUT_COMPENSATING_WALL_THICKNESS",
 "EDIT_UNDECLARED_PARAMETER","OMIT_ONE_REQUIRED_PROFILE_SEGMENT","BREAK_DECLARED_TANGENCY",
 "USE_PART_FEATURE_BAKED_SHAPE","CREATE_MULTIPLE_BODIES","CREATE_MULTIPLE_SOLIDS",
 "WRONG_PAD_WIDTH","WRONG_ARTIFACT_PATH","FAIL_TO_SAVE_BOTH_BASE_AND_EDIT_FILES"
}
EXPECTED_SOURCES={
 ("tasks/freecad-spring-clip/instruction.md","4d80d20b8d6404e68728efda4dfd79d315a9d20d"),
 ("tasks/freecad-spring-clip/task.toml","4fa89d7788a5d56f3d073ce54d46dcdad0a7b012"),
 ("tasks/freecad-spring-clip/environment/Dockerfile","1bb433cd0994aa4f88e4e9d52040fd880e59b919"),
}
EDIT_KEYS={"inner_bend_radius","clip_wall_thickness","leg_length","tip_line_angle"}

def apply_edit(c):
    x=dict(c["base_parameters"])
    x.update(c["edit_substitutions"])
    return x

def invariant_errors(p):
    e=[]
    def close(a,b,tol=1e-9): return abs(a-b)<=tol
    if not close(p["outer_bend_radius"],p["inner_bend_radius"]+p["clip_wall_thickness"]): e.append("OUTER_RADIUS")
    if not close(p["overall_leg_span"],2*p["outer_bend_radius"]): e.append("SPAN")
    if not p["leg_length"]>2*p["retention_lobe_center_offset"]+p["inner_bend_radius"]: e.append("LEG_CLEARANCE")
    if not p["tip_fillet_radius"]<p["clip_width"]: e.append("TIP_WIDTH")
    if not p["tip_fillet_radius"]<p["outer_bend_radius"]: e.append("TIP_OUTER")
    if not p["tab_transition_arc_radius"]<p["retention_lobe_center_offset"]: e.append("TRANSITION_OFFSET")
    if not p["retention_lobe_center_offset"]<p["leg_length"]: e.append("OFFSET_LEG")
    if not p["lobe_arc_span_angle"]<180: e.append("LOBE_SPAN")
    return e

def validate(source,c):
    err=[]
    if source.get("status")!="LOSSLESS_ALLOWLISTED_SOURCE_ACCOUNTING_COMPLETE__ZERO_DISCOVERY_AFTER_STAGE_B":
        err.append("SOURCE_ACCOUNTING_STATUS")
    ib=source.get("information_boundary",{})
    if ib.get("mode")!="EXACT_FETCH_ONLY" or ib.get("discovery_search_after_stage_b") is not False:
        err.append("INFORMATION_BOUNDARY")
    if any(ib.get(k) is not False for k in ("task_specific_external_search","solution_read","tests_read","hidden_verifier_read","task_command_executed")):
        err.append("SOURCE_BOUNDARY_DIRTY")
    got_sources={(x.get("path"),x.get("blob")) for x in source.get("authoritative_sources",[])}
    if got_sources!=EXPECTED_SOURCES: err.append("SOURCE_SET")
    tree=source.get("environment_tree",{})
    if not(tree.get("enumerated_exactly") is True and tree.get("entry_count")==1 and tree.get("unaccounted_entries")==0):
        err.append("ENVIRONMENT_TREE")
    if {x.get("blob") for x in tree.get("entries",[])}!={"1bb433cd0994aa4f88e4e9d52040fd880e59b919"}:
        err.append("ENVIRONMENT_BLOB")

    if set(c.get("artifacts",[]))!=REQUIRED_ARTIFACTS: err.append("ARTIFACTS")
    if not REQUIRED_MODEL <= set(c.get("model_requirements",[])): err.append("MODEL_REQUIREMENTS")
    if not REQUIRED_GEOM <= set(c.get("geometric_semantics",[])): err.append("GEOMETRIC_SEMANTICS")
    if set(c.get("edit_substitutions",{}))!=EDIT_KEYS: err.append("EDIT_KEYS")
    b=c.get("base_parameters",{}); ed=apply_edit(c)
    if invariant_errors(b): err.append("BASE_INVARIANTS:"+",".join(invariant_errors(b)))
    if invariant_errors(ed): err.append("EDIT_INVARIANTS:"+",".join(invariant_errors(ed)))
    changed={k for k in b if b[k]!=ed[k]}
    if changed!=EDIT_KEYS: err.append("EDIT_DELTA")
    if abs(ed["outer_bend_radius"]-b["outer_bend_radius"])>1e-9: err.append("OUTER_CHANGED")
    if abs(ed["overall_leg_span"]-b["overall_leg_span"])>1e-9: err.append("SPAN_CHANGED")
    if abs((b["leg_length"]-2*b["retention_lobe_center_offset"]-b["inner_bend_radius"])-0.574929)>1e-9:
        err.append("BASE_MARGIN")
    if abs((ed["leg_length"]-2*ed["retention_lobe_center_offset"]-ed["inner_bend_radius"])-0.3)>1e-9:
        err.append("EDIT_MARGIN")
    if not (0 < b["inner_bridge_arc_half_angle"] < 90 and 0 < b["tip_line_angle"] < 90 and 0 < ed["tip_line_angle"] < 90):
        err.append("ANGLE_FEASIBILITY")
    if min(b["outer_bend_radius"],b["inner_bend_radius"],b["clip_wall_thickness"],b["clip_width"],ed["inner_bend_radius"],ed["clip_wall_thickness"])<=0:
        err.append("POSITIVE_GEOMETRY")
    if not REQUIRED_MUTATIONS <= set(c.get("mutation_kill_set",[])): err.append("MUTATION_COVERAGE")
    if c.get("task_execution_authorized") is not False or c.get("hidden_verifier_read") is not False:
        err.append("PREEXECUTION_AUTHORITY")
    return sorted(set(err))

def load_here():
    here=Path(__file__).parent
    return (
      json.loads((here/"rank22_stage_b_source_accounting.json").read_text()),
      json.loads((here/"rank22_stage_b_contract.json").read_text())
    )
