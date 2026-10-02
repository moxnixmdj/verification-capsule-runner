from __future__ import annotations
import copy, hashlib, importlib.util, json, sys, types
from pathlib import Path

ROOT=Path(__file__).resolve().parent
EXPECTED={
  "candidate_v7.py": "a36b4f7e0009932a15c7822e670613a1fe921fd1",
  "proof_v7.py": "2771bc81e587f79a6fb6a60d7cf04f8f19e91df1",
  "brain_tests_v7.py": "a38250e95b801e4aef75c6f32c1e361158962274",
  "governance_v7.json": "3020fa6b5ceaf295d80a0b892e64bed63e891a22",
  "candidate_v6.py": "18d4de68ee8352410e986c318868642333ec085a",
  "proof_v6.py": "0f41a36e6ad16722ce05b180e036fb921a2ef886"
}

def blob(path):
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
for name,sha in EXPECTED.items():
    got=blob(ROOT/name)
    assert got==sha,(name,got,sha)

canonical=types.ModuleType("canonical"); canonical.__path__=[]
runtime=types.ModuleType("canonical.runtime"); runtime.__path__=[]
sys.modules["canonical"]=canonical
sys.modules["canonical.runtime"]=runtime

def load(fullname,filename):
    spec=importlib.util.spec_from_file_location(fullname,ROOT/filename)
    mod=importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[fullname]=mod
    spec.loader.exec_module(mod)
    return mod

v6c=load("canonical.runtime.trajectory_failure_typed_ir_candidate_v6","candidate_v6.py")
v6p=load("canonical.runtime.trajectory_failure_typed_ir_proof_v6","proof_v6.py")
v7c=load("canonical.runtime.trajectory_failure_typed_ir_candidate_v7","candidate_v7.py")
v7p=load("canonical.runtime.trajectory_failure_typed_ir_proof_v7","proof_v7.py")

# 192 inherited V6 cases must remain exactly accepted under the old independent oracle.
normal=0
for case in v6p.suite_cases():
    out=v7c.solve(v6p.public_task(case))
    verdict=v6p.score_case(case,out)
    assert verdict["pass"],(case["seed"],case["_oracle"],out,verdict)
    normal+=1
assert normal==192

# Reproduce the V6 falsification over every domain/mechanism, then require V7 abstention.
derived=0
for domain in v7p.DOMAINS:
    for kind in v7p.KINDS:
        public=v7p.derived_only_case(domain,kind)
        old=v6c.solve(public)
        assert old["status"]=="IDENTIFIED",(domain,kind,old)
        assert old["cause_action_id"]=="A1",(domain,kind,old)
        assert v6p.execute_intervention(public,old)["terminal_rescued"] is False,(domain,kind,old)
        new=v7c.solve(public)
        verdict=v7p.score_derived_only(new)
        assert verdict["pass"],(domain,kind,new,verdict)
        assert v6p.execute_intervention(public,new)["terminal_rescued"] is False
        assert "repair_targets" not in new
        derived+=1
assert derived==48

# Visible direct roots remain identifiable even with a downstream derived symptom.
mixed=0
for domain in v7p.DOMAINS:
    for kind in v7p.KINDS:
        public=v7p.direct_plus_derived_case(domain,kind)
        out=v7c.solve(public)
        verdict=v7p.score_direct_plus_derived(public,out,kind)
        assert verdict["pass"],(domain,kind,out,verdict)
        assert verdict["intervention"]["terminal_rescued"] is True
        mixed+=1
assert mixed==48

# Failure semantics are truly load-bearing, not decorative.
public=v7p.derived_only_case("RESEARCH","SCOPE")
derived_out=v7c.solve(public)
assert derived_out["status"]=="AMBIGUOUS"
flipped=copy.deepcopy(public)
f=next(ch for row in flipped["task"]["trajectory"] for ch in row["checks"] if ch["pass"] is False)
f["failure_semantics"]="DIRECT_CONTRACT"
direct_out=v7c.solve(flipped)
assert direct_out["status"]=="IDENTIFIED" and direct_out["cause_action_id"]=="A1",direct_out

# Missing semantics on a failed check fails closed.
missing=copy.deepcopy(public)
f=next(ch for row in missing["task"]["trajectory"] for ch in row["checks"] if ch["pass"] is False)
del f["failure_semantics"]
bad=v7c.solve(missing)
assert bad=={"status":"FAIL_CLOSED","reason":"STEP_SCHEMA_INVALID"},bad

# Prior V6 interaction/repair negatives remain preserved.
case=v6p.generate_case(99001,pattern="INTERACTION",domain="FILESYSTEM",kind="SCOPE")
pub=v6p.public_task(case)
out=v7c.solve(pub)
assert v6p.score_case(case,out)["pass"]
partial=copy.deepcopy(out); partial["repair_targets"]=partial["repair_targets"][:1]
assert v6p.execute_intervention(pub,partial)["terminal_rescued"] is False

print(json.dumps({
 "status":"PASS",
 "exact_brain_blob_count":len(EXPECTED),
 "inherited_v6_cases":normal,
 "derived_only_counterexamples_reproduced_and_killed":derived,
 "direct_plus_derived_cases":mixed,
 "failure_semantics_load_bearing":True,
 "missing_failure_semantics_fails_closed":True,
 "partial_interaction_repair_still_rejected":True,
 "primary_case_count":normal+derived+mixed,
 "terminal_results_replayed":0,
 "capability_credit_delta":0,
 "family_credit_delta":0
},indent=2,sort_keys=True))
