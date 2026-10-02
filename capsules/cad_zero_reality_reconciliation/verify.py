import json, subprocess
from pathlib import Path

ROOT=Path("capsules/cad_zero_reality_reconciliation")
EXPECTED={
"2026-10-02_CAD_ZERO_REALITY_BLOCKER_RECONCILIATION_V1.json":"0fd3791d2d2d8c3ae0bcfda99db4aa2f402b6605",
"TESSERACT_OCR_DEPENDENCY_ACCOUNTING_V1.json":"b7dd76e3d069653a9491287d396f1bca4465a25a",
"M1A_COMPLETE_ACTION_BUNDLE_V2.json":"65f4dc24c398c1f49cffde5711776074fc9f89ff",
"M1B_COMPLETE_ACTION_BUNDLE_V2.json":"4e2fde88553a4f9b01ac7c55750c3bc2d393ac15",
"M1B_CONTINUOUS_GEOMETRY_COMPILER_001.json":"3cd7bc3d43650929ca8426e856d2e1d2bd8c929c",
"M1B_SMOOTH_SURFACE_COMPILER_001.json":"619766d64540da1faa8ac32fb17a4936c46f86db",
"CAD_ACTIVE_CONTRACT_END_TO_END_PROOF_ROUTE_V1.json":"c0f55a55091186c5ab785b670f935bbc6a2f9432",
}

def blob(path):
    return subprocess.check_output(["git","hash-object",str(path)],text=True).strip()

for name,sha in EXPECTED.items():
    got=blob(ROOT/name)
    assert got==sha,(name,got,sha)

rec=json.loads((ROOT/"2026-10-02_CAD_ZERO_REALITY_BLOCKER_RECONCILIATION_V1.json").read_text())
ocr=json.loads((ROOT/"TESSERACT_OCR_DEPENDENCY_ACCOUNTING_V1.json").read_text())
m1a=json.loads((ROOT/"M1A_COMPLETE_ACTION_BUNDLE_V2.json").read_text())
m1b=json.loads((ROOT/"M1B_COMPLETE_ACTION_BUNDLE_V2.json").read_text())
cont=json.loads((ROOT/"M1B_CONTINUOUS_GEOMETRY_COMPILER_001.json").read_text())
smooth=json.loads((ROOT/"M1B_SMOOTH_SURFACE_COMPILER_001.json").read_text())
cad=json.loads((ROOT/"CAD_ACTIVE_CONTRACT_END_TO_END_PROOF_ROUTE_V1.json").read_text())

assert "VERIFIED_CLOSED_BOUNDED_OCR_DEPENDENCY_SURFACE" in ocr["status"]
assert "ZERO_REALITY_PREFIX_EXECUTED_VERIFIED_AND_SATURATED" in m1a["status"]
assert "ZERO_REALITY_PREFIX_EXECUTED_AND_VERIFIED" in m1b["status"]
assert "VERIFIED_BRAIN_OWNED_BOUNDED_CONTINUOUS_GEOMETRY_PREFIX" in cont["status"]
assert "VERIFIED_BRAIN_OWNED_SMOOTH_SURFACE_COMPONENT" in smooth["status"]
required={
"M1A_DRAWING_NORMALIZATION_OCR_NOTATION_ASSOCIATION_AND_FEATURE_CONSTRAINT_GRAPH",
"M1B_ANALYTIC_CSG_LINE_ARC_REVOLVE_COMPILER",
"M1B_SPLINE_REVOLVE_AND_MULTI_SECTION_LOFT_COMPILER",
"CADQUERY_KERNEL_SOLID_MATERIALIZATION",
}
assert required <= set(cad["candidate_composition"])
expected_remaining={
"M1A_WHOLE_COMPOSED_RAW_DRAWING_ROUTE_SCOPE_EQUIVALENCE_AND_MUTATION_PREFLIGHT_PENDING",
"FROZEN_TERMINAL_ENVELOPE_GEOMETRY_CLASS_COVERAGE_BEYOND_VERIFIED_ANALYTIC_CSG_LINE_ARC_REVOLVE_SPLINE_REVOLVE_AND_MULTI_SECTION_LOFT_GRAMMARS_NOT_YET_PROVEN",
"SCOPE_EQUIVALENT_PROOF_GATE_V2_NOT_YET_PASS",
"POST_FREEZE_TERMINAL_POPULATION_AND_INDEPENDENT_ORACLE_BINDING_PENDING",
}
assert set(rec["remaining_blockers"])==expected_remaining
assert rec["execution_authority"] is False
assert rec["promotion_authority"] is False
assert rec["capability_credit_delta"]==0
assert rec["family_credit_delta"]==0
print(json.dumps({"status":"INDEPENDENT_CAD_RECONCILIATION_PASS","remaining_blockers":sorted(expected_remaining)},sort_keys=True))
