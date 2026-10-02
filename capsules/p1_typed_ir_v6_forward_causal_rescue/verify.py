from __future__ import annotations
import copy, hashlib, importlib.util, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
EXPECTED={
  "candidate.py": "18d4de68ee8352410e986c318868642333ec085a",
  "proof.py": "0f41a36e6ad16722ce05b180e036fb921a2ef886",
  "brain_tests.py": "6961f69cafd718da6dd439765a13f59ffc9790e1",
  "governance.json": "03df530cd77cd834de94b4e3c4588008bf4a8070"
}

def blob(path):
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
for name,sha in EXPECTED.items():
    assert blob(ROOT/name)==sha,(name,blob(ROOT/name),sha)

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    mod=importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod

c=load("candidate_v6","candidate.py")
p=load("proof_v6","proof.py")
g=json.loads((ROOT/"governance.json").read_text())

assert "SCOPE" in c.ALLOWED_KINDS
assert set(c.ALLOWED_KINDS)==set(p.KINDS)
assert g["envelope"]["cross_product_cases"]==192
assert g["envelope"]["nonambiguous_forward_rescue_cases"]==144

cases=p.suite_cases()
assert len(cases)==192
rescued=0
ambiguous=0
kinds=set()
domains=set()
statuses=set()
for case in cases:
    public=p.public_task(case)
    assert "_oracle" not in public
    out=c.solve(public)
    verdict=p.score_case(case,out)
    assert verdict["pass"],(case["seed"],case["_oracle"],out,verdict)
    domains.add(case["task"]["domain"])
    statuses.add(case["_oracle"]["status"])
    for ks in case["_oracle"]["mechanisms"].values():
        kinds.update(ks)
    if case["_oracle"]["status"]=="AMBIGUOUS":
        ambiguous+=1
        assert verdict["intervention_rescue_verified"] is False
    else:
        rescued+=1
        assert verdict["intervention_rescue_verified"] is True
        assert verdict["intervention"]["terminal_rescued"] is True
        assert verdict["intervention"]["active_direct_failures"]==[]
        assert verdict["intervention"]["active_derived_failures"]==[]

assert rescued==144
assert ambiguous==48
assert kinds==set(p.KINDS)
assert domains==set(p.DOMAINS)
assert statuses=={"IDENTIFIED","INTERACTION","AMBIGUOUS"}

# SCOPE must remain a distinct visible mechanism.
for domain in p.DOMAINS:
    case=p.generate_case(9301,pattern="DELAYED",domain=domain,kind="SCOPE")
    out=c.solve(p.public_task(case))
    assert out["mechanism_classes"]==["SCOPE"],(domain,out)
    v=p.score_case(case,out)
    assert v["pass"] and v["intervention"]["terminal_rescued"] is True,(domain,v)

# Remove visible provenance: fail closed.
case=p.generate_case(9302,pattern="SINGLE",domain="RESEARCH",kind="PROVENANCE")
public=p.public_task(case)
for row in public["task"]["trajectory"]:
    for check in row["checks"]:
        if check["pass"] is False:
            check["evidence"]=[]
out=c.solve(public)
assert out["status"]=="FAIL_CLOSED",out
assert p.score_case(case,out)["pass"] is False

# Extra unfalsifiable output cannot sneak through.
case=p.generate_case(9303,pattern="DELAYED",domain="CODE",kind="SCOPE")
out=c.solve(p.public_task(case))
attacked=dict(out); attacked["diagnosis"]={"claim":"UNOBSERVABLE_FORCE"}
v=p.score_case(case,attacked)
assert v["pass"] is False and v["reason"]=="OUTPUT_SCHEMA_NOT_EXACT",v

# Partial conjunctive repair must leave a real active failure.
case=p.generate_case(9304,pattern="INTERACTION",domain="TOOL_API",kind="SCOPE")
out=c.solve(p.public_task(case))
assert p.score_case(case,out)["pass"]
partial=copy.deepcopy(out); partial["repair_targets"]=partial["repair_targets"][:1]
iv=p.execute_intervention(p.public_task(case),partial)
assert iv["terminal_rescued"] is False,iv
assert iv["active_direct_failures"],iv

# Symptom-only repair cannot bypass an unrepaired root.
case=p.generate_case(9305,pattern="DELAYED",domain="BROWSER",kind="AUTHORITY")
out=c.solve(p.public_task(case))
symptom=copy.deepcopy(out); symptom["repair_targets"]=["restore:A4:INVARIANT"]
iv=p.execute_intervention(p.public_task(case),symptom)
assert iv["terminal_rescued"] is False,iv
assert "A1:AUTHORITY" in iv["active_direct_failures"],iv

# A syntactically plausible but causally nonexistent target is powerless.
case=p.generate_case(9306,pattern="DELAYED",domain="FILESYSTEM",kind="PROVENANCE")
out=c.solve(p.public_task(case))
fake=copy.deepcopy(out); fake["repair_targets"]=["restore:A999:PROVENANCE"]
iv=p.execute_intervention(p.public_task(case),fake)
assert iv["terminal_rescued"] is False,iv

# Hidden oracle mutation cannot alter the candidate-visible intervention substrate.
case=p.generate_case(9307,pattern="SINGLE",domain="ARTIFACT",kind="SCOPE")
before=json.dumps(p.public_task(case),sort_keys=True)
case["_oracle"]["critical"]="A999"
after=json.dumps(p.public_task(case),sort_keys=True)
assert before==after

print(json.dumps({
    "status":"PASS",
    "exact_brain_blob_count":len(EXPECTED),
    "cross_product_cases":192,
    "scope_first_class":True,
    "forward_causal_rescues_verified":rescued,
    "ambiguous_abstentions":ambiguous,
    "provenance_erasure_killed":True,
    "unbound_output_killed":True,
    "partial_interaction_repair_killed":True,
    "symptom_only_repair_killed":True,
    "fake_repair_string_killed":True,
    "hidden_oracle_isolated":True,
    "terminal_results_replayed":0,
    "capability_credit_delta":0,
    "family_credit_delta":0
},indent=2,sort_keys=True))
