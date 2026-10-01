import hashlib, importlib.util, json, os, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).parent
STAGE=ROOT/"verification/rank22_stage_b"
M=json.loads((STAGE/"FREECAD_SPRING_CLIP_RANK22_SOURCE_CONTRACT_COMPILATION_V1.json").read_text())
C=json.loads((STAGE/"FREECAD_SPRING_CLIP_RANK22_STAGE_B_CONTRACT_V1.json").read_text())

spec=importlib.util.spec_from_file_location("rank22_source_compiler", ROOT/"independent/brain_core_hardening/source_contract_compiler.py")
SC=importlib.util.module_from_spec(spec)
sys.modules["rank22_source_compiler"]=SC
assert spec.loader is not None
spec.loader.exec_module(SC)

def instruction_text():
    tb=Path(os.environ["TB_ROOT"])
    return (tb/"tasks/freecad-spring-clip/instruction.md").read_text()

def pointer(doc, ptr):
    cur=doc
    for part in ptr.strip("/").split("/"):
        if part:
            cur=cur[int(part)] if isinstance(cur,list) else cur[part]
    return cur

def expand(text):
    atoms=SC.atomize_source(text,"instruction.md")
    assert len(atoms)==M["atom_count"]
    assert hashlib.sha256(text.encode()).hexdigest()==M["instruction"]["sha256"]
    reqs=[]; reverse={}
    for rid,idxs in M["requirement_source_atom_indices"].items():
        aids=[atoms[i].atom_id for i in idxs]
        reqs.append({"id":rid,"source_atom_ids":aids})
        for aid in aids: reverse.setdefault(aid,[]).append(rid)
    informative=set(M["informative_atom_indices"])
    dispositions=[]
    for i,a in enumerate(atoms):
        if i in informative:
            dispositions.append({"atom_id":a.atom_id,"kind":"INFORMATIVE","rationale":"non-operative source atom","requirement_ids":[]})
        else:
            assert reverse.get(a.atom_id), (i,a.text)
            dispositions.append({"atom_id":a.atom_id,"kind":"SOURCE_BOUNDARY" if i==44 else "BEHAVIOR","rationale":"operative source atom","requirement_ids":reverse[a.atom_id]})
    return atoms,reqs,dispositions

def test_complete_source_map():
    text=instruction_text()
    atoms,reqs,dispositions=expand(text)
    assert SC.reconstruct_source(atoms)==text
    assert SC.validate_contract_coverage(source_text=text,atoms=atoms,dispositions=dispositions,requirements=reqs)==[]
    assert set(M["contract_bindings"])==set(M["requirement_source_atom_indices"])
    for pointers in M["contract_bindings"].values():
        for p in pointers: assert pointer(C,p) is not None
    claim=M["claimed_result"]
    assert claim["unaccounted_atom_count"]==0
    assert claim["open_specification_hole_count"]==0
    assert claim["normative_or_high_risk_informative_count"]==0
    assert claim["bidirectional_traceability"] is True
    assert claim["contract_binding_complete"] is True

def test_negative_canaries():
    text=instruction_text()
    atoms,reqs,dispositions=expand(text)
    missing=[d for d in dispositions if d["atom_id"]!=atoms[9].atom_id]
    assert "UNACCOUNTED_SOURCE_ATOM:"+atoms[9].atom_id in SC.validate_contract_coverage(source_text=text,atoms=atoms,dispositions=missing,requirements=reqs)
    bad=[dict(d) for d in dispositions]
    bad[2]={"atom_id":atoms[2].atom_id,"kind":"INFORMATIVE","rationale":"bad","requirement_ids":[]}
    assert "NORMATIVE_OR_HIGH_RISK_ATOM_MARKED_INFORMATIVE:"+atoms[2].atom_id in SC.validate_contract_coverage(source_text=text,atoms=atoms,dispositions=bad,requirements=reqs)
    amb=[dict(d) for d in dispositions]
    amb[9]={"atom_id":atoms[9].atom_id,"kind":"AMBIGUOUS","rationale":"challenge","requirement_ids":[],"interpretations":["A","B"],"discriminator":"authority"}
    assert "OPEN_SPECIFICATION_HOLE:"+atoms[9].atom_id in SC.validate_contract_coverage(source_text=text,atoms=atoms,dispositions=amb,requirements=reqs)
