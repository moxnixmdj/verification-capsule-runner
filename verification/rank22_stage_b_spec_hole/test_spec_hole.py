from pathlib import Path
import importlib.util, sys, math

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location(
    "source_contract_compiler",
    ROOT/"independent/brain_core_hardening/source_contract_compiler.py"
)
sc=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=sc
spec.loader.exec_module(sc)

text=(Path(__file__).parent/"instruction.md").read_text()
assert "retention_lobe_center_offset = 6.35" in text

# The authoritative source names and constrains the scalar but never defines
# a datum/reference or equivalent coordinate relationship for its geometry.
definition_phrases=[
    "retention_lobe_center_offset is measured",
    "retention_lobe_center_offset measured",
    "retention_lobe_center_offset from the",
    "retention_lobe_center_offset relative to",
    "retention_lobe_center_offset center at",
]
assert not any(p in text.lower() for p in definition_phrases)

# Two distinct coordinate interpretations satisfy every explicit scalar
# relation involving retention_lobe_center_offset in the base configuration.
L=14.958949
o=6.35
r=1.68402
tr=1.263015
assert L > 2*o + r
assert tr < o
assert o < L
x_from_bridge=-o
x_from_tip=-L+o
assert not math.isclose(x_from_bridge,x_from_tip,abs_tol=1e-12)
assert math.isclose(abs(x_from_bridge-x_from_tip),2.258949,abs_tol=1e-9)

atoms=sc.atomize_source(text,"instruction.md")
geom=[a for a in atoms if "A roller chain spring clip is a single extruded" in a.text]
assert len(geom)==1
g=geom[0]

# The verified compiler must treat an explicit ambiguity as an admission blocker.
dispositions=[]
requirements=[]
for a in atoms:
    if a.atom_id==g.atom_id:
        dispositions.append({
            "atom_id":a.atom_id,
            "kind":"AMBIGUOUS",
            "rationale":"retention_lobe_center_offset lacks a geometric datum/reference",
            "requirement_ids":[],
            "interpretations":[
                "offset from right bridge reference toward left",
                "offset from leg tip back toward bridge",
            ],
            "discriminator":"authoritative center-placement relation required",
        })
    else:
        # Non-target atoms are explicitly accounted for in this focused
        # regression. We are testing that the ambiguity can never pass.
        kind="INFORMATIVE"
        if a.normative or a.high_risk:
            kind="AMBIGUOUS"
            dispositions.append({
                "atom_id":a.atom_id,"kind":kind,
                "rationale":"focused regression leaves non-target operative semantics unresolved",
                "requirement_ids":[],
                "interpretations":["interpretation-a","interpretation-b"],
                "discriminator":"not evaluated in focused ambiguity regression",
            })
            continue
        dispositions.append({
            "atom_id":a.atom_id,"kind":kind,
            "rationale":"non-target source atom for focused ambiguity regression",
            "requirement_ids":[],
        })

errors=sc.validate_contract_coverage(
    source_text=text,atoms=atoms,dispositions=dispositions,requirements=requirements
)
needle="OPEN_SPECIFICATION_HOLE:"+g.atom_id
assert needle in errors, (needle,errors)
assert not sc.admission_ready(errors)
print("PASS")
print("geometry_atom",g.atom_id)
print("interpretation_a_center_x_mm",x_from_bridge)
print("interpretation_b_center_x_mm",x_from_tip)
print("separation_mm",abs(x_from_bridge-x_from_tip))
print("blocking_error",needle)
