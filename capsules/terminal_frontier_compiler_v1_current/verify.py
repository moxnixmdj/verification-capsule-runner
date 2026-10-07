from __future__ import annotations
import copy, hashlib, importlib.util, json, re, shutil, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANIFEST = json.loads((ROOT / "EXPECTED_BRAIN_BLOBS.json").read_text())

def load(rel):
    return json.loads((ROOT / rel).read_text())

def blob(rel, root=ROOT):
    raw=(root/rel).read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def proved(v):
    s=str(v or "").upper()
    return s.startswith("PROVED") or s.startswith("CLOSED__PROVED")

def is_open(v):
    s=str(v or "").upper()
    return not (s.startswith("CLOSED") or s.startswith("PROVED") or s.startswith("PASS") or s.startswith("RESOLVED") or "CLOSED__" in s)

def select(regex):
    pat=re.compile(regex); rows=[]
    for p in (ROOT/"canonical/governance").glob("*.json"):
        m=pat.match(p.name)
        if not m: continue
        d=json.loads(p.read_text())
        if d.get("scheduling_authority") is True:
            rows.append((int(m.group(1)),p.relative_to(ROOT).as_posix(),d))
    assert rows
    rows.sort()
    v,rel,d=rows[-1]
    assert str(d.get("status") or "").upper().startswith("ACTIVE")
    return v,rel,d

def validate(rel,d):
    s=d["subject"]; v=d["verification"]
    assert blob(s["path"])==s["git_blob_sha"]
    assert blob(v["path"])==v["git_blob_sha"]
    vd=load(v["path"])
    st=str(vd.get("status") or "").upper()
    assert "PASS" in st or "SUCCESS" in st
    if isinstance(vd.get("errors"),list): assert not vd["errors"]
    b=vd.get("subject")
    if isinstance(b,dict):
        assert b.get("path")==s["path"]
        assert b.get("git_blob_sha")==s["git_blob_sha"]
    return load(s["path"])

for rel,expected in MANIFEST["files"].items():
    assert blob(rel)==expected,(rel,expected,blob(rel))

registry=load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json")
evidence=load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json")
root=load("canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json")
ids=[str(x["id"]) for x in registry["predicates"]]
assert len(ids)==len(set(ids))==38
proved_ids={str(c["predicate_id"]) for c in evidence["claims"] if proved(c.get("state"))}
unresolved=set(ids)-proved_ids
assert len(proved_ids)==14 and len(unresolved)==24
part=root["current_residual_root_partition"]
r1=set(part["root1_only"]); r2o=set(part["root2_only"]); r3o=set(part["root3_only"]); mix=set(part["root2_and_root3"])
buckets=[r1,r2o,r3o,mix]
for i,a in enumerate(buckets):
    for b in buckets[i+1:]: assert not (a&b)
assert r1|r2o|r3o|mix==unresolved
root2=r2o|mix; root3=r3o|mix
assert len(r1)==0 and len(root2)==18 and len(root3)==9

r1v,r1rel,r1act=select(r"^ROOT1_TERMINAL_FAMILY_ENVELOPE_AUDIT_V(\d+)_ACTIVATION_V1\.json$")
meta=validate(r1rel,r1act)
zv,zrel,zact=select(r"^CURRENT_ZERO_REALITY_MINIMUM_CUT_V(\d+)_ACTIVATION_V1\.json$")
zcut=validate(zrel,zact)

mappings=[]
for x in meta.get("family_mapping_frontier") or []:
    if isinstance(x,dict):
        if is_open(x.get("state")): mappings.append(str(x.get("family") or x.get("surface") or "UNNAMED"))
    else: mappings.append(str(x))
conditions=[str(x.get("condition")) for x in (meta.get("cross_cutting_condition_frontier") or []) if isinstance(x,dict) and is_open(x.get("state"))]
repairs=[]
r=meta.get("proof_basis_repair")
if isinstance(r,dict) and is_open(r.get("state")): repairs.append(str(r.get("surface") or "UNNAMED"))
meta_open=len(mappings)+len(conditions)+len(repairs)
assert meta_open>0
exact=zcut["exact_state"]
assert exact["proved_atomic"]==14 and exact["unresolved_atomic"]==24
assert exact["root2_touching_count"]==18 and exact["root3_touching_count"]==9

spec=importlib.util.spec_from_file_location("candidate",ROOT/"canonical/runtime/terminal_frontier_compiler_v1.py")
candidate=importlib.util.module_from_spec(spec); assert spec and spec.loader; spec.loader.exec_module(candidate)
out=candidate.compile_frontier(ROOT)
assert set(out["proved_predicates"])==proved_ids
assert set(out["unresolved_predicates"])==unresolved
assert set(out["root1_positive_predicates"])==r1
assert set(out["root2_touching"])==root2
assert set(out["root3_touching"])==root3
assert out["meta_envelope"]["open_count"]==meta_open
assert out["meta_envelope"]["active_version"]==r1v
assert out["zero_reality_cut"]["active_version"]==zv
assert out["terminal"] is False

with tempfile.TemporaryDirectory() as td:
    t=Path(td)/"c"; shutil.copytree(ROOT,t)
    p=t/"canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json"
    d=json.loads(p.read_text()); d["current_residual_root_partition"]["root2_only"][0]="FAKE_EQUAL_COUNT_PREDICATE"; p.write_text(json.dumps(d,indent=2)+"\n")
    try: candidate.compile_frontier(t)
    except candidate.FrontierCompileError as e: assert "ROOT_PARTITION_IDENTITY_DRIFT" in str(e)
    else: raise AssertionError("wrong-identity mutation did not fail closed")

with tempfile.TemporaryDirectory() as td:
    t=Path(td)/"c"; shutil.copytree(ROOT,t)
    p=t/"canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V14_ACTIVATION_V1.json"
    d=json.loads(p.read_text()); d["subject"]["git_blob_sha"]="0"*40; p.write_text(json.dumps(d,indent=2)+"\n")
    try: candidate.compile_frontier(t)
    except candidate.FrontierCompileError as e: assert "ACTIVATION_SUBJECT_BLOB_MISMATCH" in str(e)
    else: raise AssertionError("activation-drift mutation did not fail closed")

print(json.dumps({"status":"INDEPENDENT_RECOMPUTATION_PASS","source_commit":MANIFEST["source_commit"],"proved_atomic":14,"unresolved_atomic":24,"root2_touching":18,"root3_touching":9,"meta_open":meta_open,"terminal":False,"falsification_tests":2},indent=2,sort_keys=True))
