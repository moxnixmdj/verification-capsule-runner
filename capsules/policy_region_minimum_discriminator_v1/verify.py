from __future__ import annotations
import hashlib, itertools, json, pathlib, sys

ROOT=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from canonical.runtime.policy_region_minimum_discriminator_v1 import solve

def git_blob_sha(p):
    raw=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

runtime=ROOT/"canonical/runtime/policy_region_minimum_discriminator_v1.py"
kernel=ROOT/"canonical/runtime/monotone_semantic_constraint_kernel_v1.py"
assert git_blob_sha(runtime)=="74fbb5533e178486fe0eb3a698dd3d5224b36938"
assert git_blob_sha(kernel)=="8874d89ad852ae118330a50961e61ba9633b00ff"

def A(x): return {"op":"ATOM","id":x}
def N(x): return {"op":"NOT","arg":A(x)}
def AND(*xs): return {"op":"AND","args":list(xs)}
def OR(*xs): return {"op":"OR","args":list(xs)}

# Independent reference evaluator, intentionally not importing production internals.
def ev(f,v):
    op=f["op"]
    if op=="TRUE": return True
    if op=="FALSE": return False
    if op=="ATOM": return bool(v[f["id"]])
    if op=="NOT": return not ev(f["arg"],v)
    if op=="AND": return all(ev(x,v) for x in f["args"])
    if op=="OR": return any(ev(x,v) for x in f["args"])
    if op=="XOR": return sum(ev(x,v) for x in f["args"])==1
    if op=="IMPLIES": return (not ev(f["if"],v)) or ev(f["then"],v)
    raise AssertionError(op)

def ref_minimum(basis,state,policies):
    models=[dict(zip(basis,bits)) for bits in itertools.product((False,True),repeat=len(basis)) if ev(state,dict(zip(basis,bits)))]
    adequate=[{p for p,phi in policies.items() if ev(phi,m)} for m in models]
    if any(not x for x in adequate): return ("GAP",None,None)
    common=set.intersection(*map(set,adequate))
    if common: return ("COMMON",0,())
    for k in range(1,len(basis)+1):
        for atoms in itertools.combinations(basis,k):
            buckets={}
            for i,m in enumerate(models):
                buckets.setdefault(tuple(m[a] for a in atoms),[]).append(i)
            ok=True
            for ids in buckets.values():
                if not set.intersection(*(set(adequate[i]) for i in ids)):
                    ok=False; break
            if ok: return ("DISC",k,atoms)
    raise AssertionError("full basis must separate non-gap singleton worlds")

cases=[
    (["a"],{"op":"TRUE"},{"p0":{"op":"TRUE"}},("COMMON",0,())),
    (["a"],{"op":"TRUE"},{"p0":N("a"),"p1":A("a")},("DISC",1,("a",))),
    (["a","noise"],{"op":"TRUE"},{"p0":N("a"),"p1":A("a")},("DISC",1,("a",))),
    (["a","b"],{"op":"TRUE"},{
        "p00":AND(N("a"),N("b")),"p01":AND(N("a"),A("b")),
        "p10":AND(A("a"),N("b")),"p11":AND(A("a"),A("b")),
    },("DISC",2,("a","b"))),
    (["a"],{"op":"TRUE"},{"p0":A("a")},("GAP",None,None)),
    (["a","b","c"],{"op":"TRUE"},{
        "p0":OR(AND(N("a"),N("b")),AND(N("a"),A("b"))),
        "p1":OR(AND(A("a"),N("b")),AND(A("a"),A("b"))),
    },("DISC",1,("a",))),
]
checked=0
for basis,state,policies,expected in cases:
    out=solve(
        decision_basis=basis,
        formal_source_constraints=[],
        proposed_refinements=[],
        policy_conditions=policies,
        authenticated_policy_ids=sorted(policies),
    )
    ref=ref_minimum(basis,state,policies)
    assert ref==expected,(ref,expected)
    if ref[0]=="GAP":
        assert out["pass"] is False and out["status"]=="AUTHENTICATED_POLICY_COVER_GAP"
    elif ref[0]=="COMMON":
        assert out["pass"] is True and out["status"]=="COMMON_AUTHENTICATED_POLICY_OVER_CURRENT_SOUND_STATE"
        assert out["minimum_discriminator_atom_count"]==0
    else:
        assert out["pass"] is True and out["status"]=="MINIMUM_POLICY_CHANGING_DISCRIMINATOR_FOUND"
        assert out["minimum_discriminator_atom_count"]==ref[1]
        assert tuple(out["minimum_discriminator_atoms"])==ref[2]
    checked+=1

# Source-proved constraint must reduce worlds and can reduce discriminator size.
constraint=A("a")
out=solve(
    decision_basis=["a","b"],
    formal_source_constraints=[constraint],
    proposed_refinements=[constraint],
    policy_conditions={"p0":AND(A("a"),N("b")),"p1":AND(A("a"),A("b"))},
    authenticated_policy_ids=["p0","p1"],
)
assert out["model_count"]==2
assert out["minimum_discriminator_atoms"]==["b"]

# Unproved proposed refinement must not shrink uncertainty.
out=solve(
    decision_basis=["a"],
    formal_source_constraints=[],
    proposed_refinements=[A("a")],
    policy_conditions={"p0":N("a"),"p1":A("a")},
    authenticated_policy_ids=["p0","p1"],
)
assert out["model_count"]==2
assert out["minimum_discriminator_atoms"]==["a"]

# Unauthenticated policy is excluded and may expose a real cover gap.
out=solve(
    decision_basis=["a"],
    formal_source_constraints=[],
    proposed_refinements=[],
    policy_conditions={"p0":A("a"),"p1":N("a")},
    authenticated_policy_ids=["p0"],
)
assert out["status"]=="AUTHENTICATED_POLICY_COVER_GAP"

# Invalid/malformed inputs fail closed.
out=solve(decision_basis=["a"],formal_source_constraints=[],proposed_refinements=[],
          policy_conditions={"p":{"op":"ATOM","id":"b"}},authenticated_policy_ids=["p"])
assert out["pass"] is False and out["reason"]=="POLICY_FORMULA_INVALID"
out=solve(decision_basis=["a"],formal_source_constraints=[],proposed_refinements=[],
          policy_conditions={"p":{"op":"TRUE"}},authenticated_policy_ids=["p","p"])
assert out["pass"] is False and out["reason"]=="AUTHENTICATED_POLICY_IDS_DUPLICATE"

print(json.dumps({
  "schema":"PROJECT_BRAIN_POLICY_REGION_MINIMUM_DISCRIMINATOR_INDEPENDENT_VERIFY_V1",
  "status":"PASS",
  "exact_runtime_blob":git_blob_sha(runtime),
  "exact_kernel_blob":git_blob_sha(kernel),
  "independent_reference_cases":checked,
  "source_constraint_reduction_checked":True,
  "unproved_refinement_monotonicity_checked":True,
  "authenticated_policy_filter_checked":True,
  "malformed_input_fail_closed_checked":True,
  "db_admission_authorized":False,
  "u_empty_authorized":False,
  "terminal_authority":False,
  "terminal_credit_delta":0
},sort_keys=True))
