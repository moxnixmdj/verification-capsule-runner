from __future__ import annotations
import hashlib, importlib.util, json, pathlib, sys, types

ROOT=pathlib.Path(__file__).resolve().parent
EXPECTED={
 "professional_positive_adequacy_escape_router_v1.py":"8344807bb267c88df45091dc2d037001faf8979f",
 "PROFESSIONAL_POSITIVE_ADEQUACY_ESCAPE_20261007_V1.json":"471840f0c4c6ae690b7fa3b953714131a11e6de3",
 "professional_source_authority_coverage_gate_v1.py":"45ff93b28a3ef4170127f572639964fd3b12d637",
 "p2_membership_residual_localizer_v1.py":"e4b555b7dd7c7ff380b687f980ea03856614992b",
 "source_positive_adequacy_db_admission_v1.py":"1febb024c049acf2a0108219d074c31a1f33db26",
}

def blob(p):
    data=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

for name,want in EXPECTED.items():
    got=blob(ROOT/name)
    assert got==want,(name,got,want)

gov=json.loads((ROOT/"PROFESSIONAL_POSITIVE_ADEQUACY_ESCAPE_20261007_V1.json").read_text())
assert gov["accounting"]["terminal_credit_delta"]==0
assert gov["accounting"]["acceptance_credit_delta"]==0
assert gov["tournament_effect"]["new_capability_build_justified"] is False
assert "FULL_SEMANTIC_COMPLETION_IS_NOT_NECESSARY" in gov["first_principles_repair"]

# Load the exact structural gate independently.
gate_spec=importlib.util.spec_from_file_location("structural_gate",ROOT/"professional_source_authority_coverage_gate_v1.py")
gate=importlib.util.module_from_spec(gate_spec); assert gate_spec and gate_spec.loader; gate_spec.loader.exec_module(gate)

def manifest(parsed=True):
    return {
      "sources":[{"source_id":"task","required":True,"parsed":parsed,"content_sha256":"abc","parser_receipt":"r","authority_rank":0}],
      "required_dimension_ids":["deliverable"],
      "dimensions":[{"dimension_id":"deliverable","source_ids":["task"],"coverage_receipt":"c"}],
      "required_convention_ids":[],
      "conventions":[],
    }

assert gate.verify(manifest())["pass"] is True
bad=gate.verify(manifest(False))
assert bad["pass"] is False
assert "REQUIRED_SOURCE_NOT_PARSED:task" in bad["errors"]
x=manifest(); x["dimensions"]=[]
bad=gate.verify(x); assert "REQUIRED_DIMENSION_UNCOVERED:deliverable" in bad["errors"]

# Supply controlled direct dependencies so the exact router can be falsified in isolation.
canonical=types.ModuleType("canonical"); canonical.__path__=[]
runtime=types.ModuleType("canonical.runtime"); runtime.__path__=[]
sys.modules["canonical"]=canonical
sys.modules["canonical.runtime"]=runtime

m1=types.ModuleType("canonical.runtime.p2_membership_residual_localizer_v1")
m1.localize=lambda *a,**k: {"membership_proved":False,"first_residual_class":"RAW_TO_TYPED_P2_SEMANTIC_COMPILATION"}
sys.modules[m1.__name__]=m1
m2=types.ModuleType("canonical.runtime.professional_source_authority_coverage_gate_v1")
m2.verify=gate.verify
sys.modules[m2.__name__]=m2
m3=types.ModuleType("canonical.runtime.source_positive_adequacy_db_admission_v1")
m3.evaluate=lambda p: {"pass":False,"status":"UNRESOLVED__POSITIVE_ADEQUACY_NOT_ENTAILED","db_admission_authorized":False}
sys.modules[m3.__name__]=m3

spec=importlib.util.spec_from_file_location("candidate",ROOT/"professional_positive_adequacy_escape_router_v1.py")
candidate=importlib.util.module_from_spec(spec); assert spec and spec.loader; spec.loader.exec_module(candidate)

# Structural omission must dominate semantic work.
out=candidate.route("Prepare workbook.",source_id="task",structural_manifest=manifest(False))
assert out["status"]=="BLOCKED__DECLARED_STRUCTURAL_OMISSION"
assert out["pass"] is False and out["terminal_credit_delta"]==0

# Exact P2 membership short-circuits positive adequacy.
candidate.localize_p2=lambda *a,**k: {"membership_proved":True,"first_residual_class":None}
def should_not_run(_): raise AssertionError("positive adequacy ran after exact P2 membership")
candidate.evaluate_positive_adequacy=should_not_run
out=candidate.route("{}",source_id="task",structural_manifest=manifest())
assert out["pass"] is True
assert out["selected_route"]=="EXACT_P2_MEMBERSHIP"
assert out["terminal_authority"] is False
assert out["acceptance_credit_delta"]==0

# P2 failure must request positive adequacy before full semantic completion.
candidate.localize_p2=lambda *a,**k: {"membership_proved":False,"first_residual_class":"RAW_TO_TYPED_P2_SEMANTIC_COMPILATION"}
out=candidate.route("Prepare workbook.",source_id="task",structural_manifest=manifest())
assert out["pass"] is False
assert out["status"]=="UNRESOLVED__TRY_POSITIVE_ADEQUACY_BEFORE_FULL_SEMANTIC_COMPLETION"
assert out["full_semantic_manifest_required_for_selected_cell"] is False

# Positive adequacy may close only the selected cell, never global scope or terminal.
candidate.evaluate_positive_adequacy=lambda p: {"pass":True,"status":"PASS__SOURCE_PROVED_POSITIVE_ADEQUACY_CELL_ADMISSIBLE_TO_D_B","db_admission_authorized":True}
text="Prepare workbook."
out=candidate.route(text,source_id="task",structural_manifest=manifest(),positive_adequacy_payload={"source_text":text,"source_id":"task"})
assert out["pass"] is True and out["selected_route"]=="SOURCE_POSITIVE_ADEQUACY"
assert out["global_professional_scope_closed"] is False
assert out["terminal_authority"] is False and out["terminal_credit_delta"]==0 and out["acceptance_credit_delta"]==0

# A fake pass bit without DB admission authority must not pass.
candidate.evaluate_positive_adequacy=lambda p: {"pass":True,"status":"COUNTERFEIT_PASS","db_admission_authorized":False}
out=candidate.route(text,source_id="task",structural_manifest=manifest(),positive_adequacy_payload={"source_text":text,"source_id":"task"})
assert out["pass"] is False
assert out["status"]=="UNRESOLVED__P2_AND_POSITIVE_ADEQUACY_BOTH_OPEN"

# Source mismatch must stop before the adequacy evaluator.
def forbidden(_): raise AssertionError("adequacy evaluator reached despite source mismatch")
candidate.evaluate_positive_adequacy=forbidden
out=candidate.route(text,source_id="task",structural_manifest=manifest(),positive_adequacy_payload={"source_text":"other","source_id":"task"})
assert out["pass"] is False and out["reason"]=="POSITIVE_ADEQUACY_SOURCE_TEXT_MISMATCH"

out=candidate.route(text,source_id="task",structural_manifest=manifest(),positive_adequacy_payload={"source_text":text,"source_id":"other"})
assert out["pass"] is False and out["reason"]=="POSITIVE_ADEQUACY_SOURCE_ID_MISMATCH"

print(json.dumps({
 "status":"PASS",
 "exact_brain_blobs":EXPECTED,
 "structural_gate_adversarial_checks":3,
 "router_adversarial_checks":6,
 "full_semantic_completion_unconditionally_required":False,
 "acceptance_credit_delta":0,
 "terminal_credit_delta":0,
},sort_keys=True))
