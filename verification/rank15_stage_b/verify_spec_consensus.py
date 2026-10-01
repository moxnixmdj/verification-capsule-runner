from __future__ import annotations
import json, re, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
contract=json.loads((ROOT/"verification/rank15_stage_b/wdm_design_stage_b_contract_v3.json").read_text())
text=Path(sys.argv[1]).read_text()
lo=text.lower()

REQS={r["id"] for r in contract["normalized_requirements"]}
assert len(REQS)==16

# Route A: literal semantic anchors, chosen from distinct clauses in the frozen instruction.
A={
"R01_FIXED_SINGLE_PATTERN":["same fixed pattern","all four conditions simultaneously"],
"R02_EZ_ODD_Z_POLARIZATION":["fundamental out-of-plane-electric-field","mp.odd_z","mp.even_z"],
"R03_SHORT_BAND_THRESHOLDS":["short band","[1.50, 1.54]","short-band output transmission","long-band output leakage"],
"R04_SAME_RUN_SELF_NORMALIZATION":["single-simulation self-normalization","same run","separate straight-waveguide reference simulation"],
"R05_LONG_BAND_THRESHOLDS":["long band","[1.56, 1.60]","long-band output transmission","short-band output leakage"],
"R06_DESIGN_NPY_CONTRACT":["/app/design.npy","float64","axis 0 = spatial","fully binary"],
"R07_META_SCHEMA_AND_BOUNDS":["/app/meta.json","design_region_size_um","fdtd_resolution","verifier rejects submissions"],
"R08_PORT_GEOMETRY":["both outputs fully inside","opposite sides of","port-to-port edge gap"],
"R09_MIN_FEATURE_DRC":["minimum-feature drc","8-connected components","maximum inscribed diameter"],
"R10_FIXED_CELL_AND_MATERIALGRID":["pml thickness","mp.materialgrid","u_mean","no smoothing","fixed measurement layout","simulation cell is therefore"],
"R11_WAVEGUIDE_PLACEMENT":["input waveguide at center","long-band output at","short-band output at","submitted design block","input waveguide on the left","output waveguides on the right"],
"R12_SOURCE_CONFIGURATION":["mp.eigenmodesource","eig_band=1","eig_kpoint","source center frequency"],
"R13_MONITOR_CONFIGURATION":["three mode monitors","input monitor is centered","long and short output monitors"],
"R14_RUN_AND_COEFFICIENT_EXTRACTION":["mp.stop_when_dft_decayed","get_eigenmode_coefficients","alpha[0, :, 0]"],
"R15_RESOURCE_AND_POLICY":["28800 seconds","do not cheat by using online solutions or hints specific to this task"],
"R16_MATERIAL_MODEL":["2.85","1.44","215\\ \\text{nm}"]
}
route_a={rid for rid,anchors in A.items() if all(x in lo for x in anchors)}

# Route B: independently encoded structural/numeric predicates.
B={
"R01_FIXED_SINGLE_PATTERN":[r"same fixed pattern",r"two distinct output ports"],
"R02_EZ_ODD_Z_POLARIZATION":[r"eig_parity\s*=\s*mp\.odd_z",r"mp\.even_z"],
"R03_SHORT_BAND_THRESHOLDS":[r"1\.50\s*,\s*1\.54",r"short-band output transmission must be.*0\.87",r"long-band output leakage must be.*0\.15"],
"R04_SAME_RUN_SELF_NORMALIZATION":[r"single-simulation\s+self-normalization",r"same\s+run",r"straight-waveguide\s+reference"],
"R05_LONG_BAND_THRESHOLDS":[r"1\.56\s*,\s*1\.60",r"long-band output transmission must be.*0\.87",r"short-band output leakage must be.*0\.15"],
"R06_DESIGN_NPY_CONTRACT":[r"design\.npy",r"float64",r"shape \$\(n_x, n_y\)\$",r"rho<0\.05.*rho>0\.95"],
"R07_META_SCHEMA_AND_BOUNDS":[r"waveguide\s+widths.*0\.30.*0\.60",r"l_x\s*,\s*l_y.*2\.0.*3\.2",r"n_x\s*,\s*n_y.*32.*256",r"fdtd\s+pixels\s+per\s+micrometer"],
"R08_PORT_GEOMETRY":[r"fully inside the design height",r"opposite sides of",r"edge gap.*0\.30"],
"R09_MIN_FEATURE_DRC":[r"8-connected components",r"0\.06",r"0\.12"],
"R10_FIXED_CELL_AND_MATERIALGRID":[r"pml thickness.*0\.8",r"grid_type=.u_mean.",r"no smoothing, filtering, projection",r"fixed measurement layout",r"s_x=2\(0\.8\)\+2\(1\.0\)\+l_x",r"s_y=2\(0\.8\)\+l_y\+2\(0\.6\)"],
"R11_WAVEGUIDE_PLACEMENT":[r"\(-s_x/4,0\)",r"\(s_x/4,\\ y_\\text\{long\}\)",r"\(s_x/4,\\ y_\\text\{short\}\)",r"input waveguide on the left",r"output waveguides on the right"],
"R12_SOURCE_CONFIGURATION":[r"eigenmodesource",r"eig_band=1",r"eig_kpoint=mp\.vector3\(1,0,0\)",r"1/1\.58",r"1/1\.52"],
"R13_MONITOR_CONFIGURATION":[r"five frequencies of the active band",r"input monitor is centered",r"output monitors are centered"],
"R14_RUN_AND_COEFFICIENT_EXTRACTION":[r"stop_when_dft_decayed\(tol=1e-4\)",r"get_eigenmode_coefficients",r"alpha\[0, :, 0\]"],
"R15_RESOURCE_AND_POLICY":[r"28800 seconds",r"do not cheat"],
"R16_MATERIAL_MODEL":[r"2\.85",r"1\.44",r"215.*nm"]
}
route_b={rid for rid,patterns in B.items() if all(re.search(p,lo,re.S) for p in patterns)}

missing_a=sorted(REQS-route_a)
missing_b=sorted(REQS-route_b)
extra_a=sorted(route_a-REQS)
extra_b=sorted(route_b-REQS)
assert not missing_a and not extra_a, {"route_a_missing":missing_a,"extra":extra_a}
assert not missing_b and not extra_b, {"route_b_missing":missing_b,"extra":extra_b}
assert route_a==route_b==REQS

# Fail-closed sentence accounting. Any sentence that looks normative/constraint-bearing
# must be captured by at least one requirement's literal or regex evidence.
sentences=[s.strip() for s in re.split(r"(?<=[.!?])\s+(?=\S)", text.strip()) if s.strip()]
normative_markers=("must","do not","rejects","required","minimum","verifier","use ","writes ","write ","bounds",">= ","<= "," ≥ "," ≤ ","exactly","same fixed pattern","no smoothing","no filter")
unaccounted=[]
for i,s in enumerate(sentences,1):
    sl=s.lower()
    normative=any(m in sl for m in normative_markers) or bool(re.search(r"\b0\.\d+\b|\b[12]\.\d+\b|\b[123]\d{1,2}\b",sl))
    if not normative:
        continue
    matched=False
    for anchors in A.values():
        if any(a in sl for a in anchors):
            matched=True; break
    if not matched:
        for pats in B.values():
            if any(re.search(p,sl,re.S) for p in pats):
                matched=True; break
    if not matched:
        unaccounted.append({"sentence_id":i,"text":s})
assert not unaccounted, {"unaccounted_normative_sentences":unaccounted}

print(json.dumps({
 "schema":"RANK15_STAGE_B_SPECIFICATION_CONSENSUS_V1",
 "pass":True,
 "instruction_blob_sha":"ab7255e9b4cf9597e965e2fe385447e502c4e8f9",
 "requirements_route_a":sorted(route_a),
 "requirements_route_b":sorted(route_b),
 "consensus":route_a==route_b,
 "source_sentence_count":len(sentences),
 "unaccounted_normative_sentence_count":0,
 "all_source_sentences_classified":True,
 "nonrequirement_context_sentence_count":sum(1 for s in sentences if not any(a in s.lower() for anchors in A.values() for a in anchors) and not any(re.search(p,s.lower(),re.S) for pats in B.values() for p in pats)),
 "solution_read":False,
 "tests_read":False,
 "hidden_verifier_read":False,
 "task_execution_performed":False
},indent=2))
