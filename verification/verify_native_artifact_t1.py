import json
from pathlib import Path
d=json.loads(Path("verification/native_artifact_t1_binding.json").read_text())
errors=[]
if d.get("behavior_id")!="NATIVE_ARTIFACT_STRUCTURED_EDIT_PRESERVATION_001":errors.append("BEHAVIOR")
if d.get("proof_mode")!="T1_MULTIPLEXED_MECHANICAL_GATE_PLUS_PUBLIC_PROFESSIONAL_BAR":errors.append("MODE")
dec=d.get("decomposition") or {}
if dec.get("adjacent_behavior_id")!="PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001":errors.append("ADJACENT")
if "SEMANTIC_TARGET_SELECTION" not in str(dec.get("excluded_adjacent_behavior") or ""):errors.append("SPLIT")
expected={"docx":"XML_SET_TEXT","xlsx":"XML_SET_TEXT","pptx":"XML_SET_TEXT","pdf":"PDF_REPLACE_UNIQUE_TEXT"}
fs=d.get("format_scope") or {}
if set(fs)!=set(expected):errors.append("FORMATS")
for k,v in expected.items():
    if (fs.get(k) or {}).get("edit_kind")!=v:errors.append("EDIT:"+k)
vis=set(d.get("candidate_visible_information") or [])
if {"PRE_EDIT_STRUCTURAL_SNAPSHOT","EXPECTED_POST_EDIT_STRUCTURAL_SNAPSHOT","UNRELATED_STRUCTURE_DIFF_ORACLE","RENDER_PIXEL_DIFF_ORACLE"} & vis:errors.append("ORACLE_LEAK")
if len(d.get("independent_preflights") or [])!=2:errors.append("PREFLIGHTS")
ts=d.get("terminal_surface") or {}
if ts.get("portfolio")!="T1" or ts.get("synthetic_whole_domain_superset_required") is not False:errors.append("SURFACE")
if (d.get("abstention") or {}).get("silent_fallback") is not False:errors.append("FALLBACK")
for k,v in (d.get("contamination") or {}).items():
    if v is not False:errors.append("CONTAMINATION:"+k)
if d.get("execution_authority") is not False or d.get("terminal_results_observed")!=0:errors.append("AUTHORITY")
if d.get("capability_credit_delta")!=0 or d.get("family_credit_delta")!=0:errors.append("CREDIT")
if d.get("brain_blob_sha")!="24305922dbe3e1a940a107b6686b004907dfb395":errors.append("BLOB")
print(json.dumps({"pass":not errors,"errors":errors},sort_keys=True))
raise SystemExit(1 if errors else 0)
