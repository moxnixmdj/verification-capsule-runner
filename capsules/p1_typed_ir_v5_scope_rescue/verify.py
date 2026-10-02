from __future__ import annotations
import copy, hashlib, importlib.util, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
EXPECTED={
  "candidate.py": "b571076490099addbfd142e635241b730a4d8cad",
  "proof.py": "dbad7bcbad6b342dc631d4559fec9cb656cd2a6e",
  "brain_tests.py": "975fc7ac5012c7c4eb09d3ef31d778cbcfc505cf",
  "governance.json": "81fb44c63320792b450879dda44e2c0bddfb7d29"
}

def blob_sha(path:Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

for name,sha in EXPECTED.items():
    got=blob_sha(ROOT/name)
    assert got==sha,(name,got,sha)

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    mod=importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod

c=load("cand_v5","candidate.py")
p=load("proof_v5","proof.py")
gov=json.loads((ROOT/"governance.json").read_text())

assert "SCOPE" in c.ALLOWED_KINDS
assert set(p.KINDS)==set(c.ALLOWED_KINDS)
assert gov["envelope"]["case_count"]==192
assert gov["envelope"]["rescue_required_case_count"]==144

cases=p.suite_cases()
assert len(cases)==192
rescued=0
ambiguous=0
scope_cases=0
patterns=set()
domains=set()
kinds=set()

for case in cases:
    public=p.public_task(case)
    assert "_oracle" not in public
    out=c.solve(public)
    verdict=p.score_case(case,out)
    assert verdict["pass"],(case["seed"],case["_oracle"],out,verdict)
    domains.add(case["task"]["domain"])
    patterns.add(case["_oracle"]["status"])
    for ks in case["_oracle"]["mechanisms"].values():
        kinds.update(ks)
        if "SCOPE" in ks:
            scope_cases+=1
    if case["_oracle"]["status"]=="AMBIGUOUS":
        ambiguous+=1
        assert verdict["intervention_rescue_verified"] is False
        assert not out.get("repair_targets")
    else:
        rescued+=1
        assert verdict["intervention_rescue_verified"] is True
        assert verdict["intervention"]["terminal_rescued"] is True

assert domains==set(p.DOMAINS)
assert kinds==set(p.KINDS)
assert "SCOPE" in kinds
assert patterns=={"IDENTIFIED","INTERACTION","AMBIGUOUS"}
assert rescued==144
assert ambiguous==48
assert scope_cases>0

case=p.generate_case(9101,pattern="DELAYED",domain="TOOL_API",kind="SCOPE")
out=c.solve(p.public_task(case))
assert out["mechanism_classes"]==["SCOPE"],out
assert out["repair_targets"]==["restore:A1:SCOPE"],out
v=p.score_case(case,out)
assert v["pass"] and v["intervention"]["terminal_rescued"] is True,v

case=p.generate_case(9102,pattern="INTERACTION",domain="RESEARCH",kind="SCOPE")
out=c.solve(p.public_task(case))
assert p.score_case(case,out)["pass"]
partial=copy.deepcopy(out)
partial["repair_targets"]=partial["repair_targets"][:1]
iv=p.execute_intervention(p.public_task(case),partial)
assert iv["terminal_rescued"] is False,iv
assert p.score_case(case,partial)["pass"] is False

case=p.generate_case(9103,pattern="DELAYED",domain="FILESYSTEM",kind="PROVENANCE")
out=c.solve(p.public_task(case))
fake=copy.deepcopy(out)
fake["repair_targets"]=["restore:A999:PROVENANCE"]
iv=p.execute_intervention(p.public_task(case),fake)
assert iv["terminal_rescued"] is False,iv
assert p.score_case(case,fake)["pass"] is False

case=p.generate_case(9104,pattern="DELAYED",domain="CODE",kind="SCOPE")
out=c.solve(p.public_task(case))
iv=p.execute_intervention(p.public_task(case),out)
assert iv["terminal_rescued"] is True,iv
assert iv["active_direct_failures"]==[],iv
assert iv["active_derived_failures"]==[],iv

case=p.generate_case(9105,pattern="SINGLE",domain="ARTIFACT",kind="SCOPE")
before=json.dumps(p.public_task(case),sort_keys=True)
case["_oracle"]["critical"]="A999"
after=json.dumps(p.public_task(case),sort_keys=True)
assert before==after

print(json.dumps({
  "status":"PASS",
  "exact_brain_blob_count":len(EXPECTED),
  "case_count":len(cases),
  "mechanism_class_count":len(p.KINDS),
  "scope_first_class":True,
  "machine_verified_terminal_rescues":rescued,
  "ambiguous_abstentions":ambiguous,
  "interaction_partial_repair_rejected":True,
  "repair_label_only_rejected":True,
  "hidden_oracle_isolated":True,
  "terminal_results_observed":0,
  "capability_credit_delta":0,
  "family_credit_delta":0
},indent=2,sort_keys=True))
