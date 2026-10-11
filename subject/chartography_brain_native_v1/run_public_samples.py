from __future__ import annotations
import hashlib,json,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"mirror"))

from canonical.runtime.chartography_professional_semantics_v1 import solve_professional_chart

OFFICIAL=ROOT/"official"/"task_packs"/"sample_charts"
CASES=[
  {
    "id":"sample_task_1",
    "image":OFFICIAL/"charts"/"sample_chart_1.png",
    "prompt":"How long would it take an environment of 1100 degC / 0.03 K/m to deform 4 metres vertically. Answer in years with 1 decimal place",
    "acceptable":[76.0,79.0],
  },
  {
    "id":"sample_task_2",
    "image":OFFICIAL/"charts"/"sample_chart_2.jpg",
    "prompt":"Using Mg-9 wt % Al alloy, at what temperature does Mg17Al12 precipitate? Round to the nearest 10 degrees.",
    "acceptable":[330.0,370.0],
  },
]

def first_num(s):
    import re
    m=re.search(r"[-+]?\d+(?:\.\d+)?",str(s))
    return float(m.group(0)) if m else None

rows=[]
for c in CASES:
    out=solve_professional_chart(c["image"],c["prompt"],root=ROOT)
    v=first_num(out["answer"])
    ok=v is not None and c["acceptable"][0] <= v <= c["acceptable"][1]
    rows.append({
      "id":c["id"],
      "answer":out["answer"],
      "numeric":v,
      "route":out["route"],
      "pass":ok,
      "model_dependency_count":out["model_dependency_count"],
      "external_model_runtime_dependency_count":out["external_model_runtime_dependency_count"],
      "cognition_dependency_class":out["cognition_dependency_class"],
      "ocr_terminal_semantic_authority":out["ocr_terminal_semantic_authority"],
      "axis_calibration":out.get("axis_calibration"),
      "swatch":out.get("swatch"),
      "trace":out.get("trace"),
      "candidate_intersections_c":out.get("candidate_intersections_c"),
    })
result={
  "schema":"PROJECT_BRAIN_CHARTOGRAPHY_DONOR_FREE_PUBLIC_SAMPLE_VERIFY_V1",
  "passed":sum(r["pass"] for r in rows),
  "total":len(rows),
  "pass":all(r["pass"] for r in rows),
  "rows":rows,
  "heldout_cases_consumed":0,
  "heldout_gold_consumed":0,
  "runtime_general_purpose_model_dependencies":[],
  "external_runtime_cognition":False,
  "incremental_spend_usd":0,
}
Path("out").mkdir(exist_ok=True)
Path("out/result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
print(json.dumps(result,sort_keys=True))
raise SystemExit(0 if result["pass"] else 1)
