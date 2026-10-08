from __future__ import annotations
import hashlib, importlib.util, json, os, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
RUNTIME=ROOT/"canonical/runtime/exact_rational_symbolic_feature_v1.py"
TESTS=ROOT/"canonical/tests/test_exact_rational_symbolic_feature_v1.py"
GOV=ROOT/"canonical/governance/MYSTERYMECHANISM_EXACT_RATIONAL_SYMBOLIC_FEATURE_20261008_V1.json"
EXPECTED={
 RUNTIME:"d90110a54f80c1d0d6e6c3baa443f8c057da42ca",
 TESTS:"55e0b8ae688bbfc7ee1331c56cd4827bdac74598",
 GOV:"b783c6f91255cce73e3aed0a9c4a15da134b059f",
}
def blob(path):
 raw=path.read_bytes(); return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def req(c,m):
 if not c: raise AssertionError(m)
def load():
 spec=importlib.util.spec_from_file_location("feature_exact",RUNTIME); req(spec and spec.loader,"import")
 m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
def var(n): return {"op":"var","name":n}
def unary(op,a): return {"op":op,"arg":a}
def binary(op,a,b): return {"op":op,"left":a,"right":b}
def main():
 observed={}
 for p,e in EXPECTED.items():
  a=blob(p); req(a==e,f"blob drift {p}: {a} != {e}"); observed[str(p.relative_to(ROOT))]=a
 g=json.loads(GOV.read_text())
 req(all(v==0 for v in g["accounting"].values()),"nonzero governance credit")
 env=dict(os.environ); env["PYTHONPATH"]=str(ROOT)
 proc=subprocess.run([sys.executable,"-m","unittest","-v","canonical.tests.test_exact_rational_symbolic_feature_v1"],cwd=ROOT,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 print(proc.stdout); req(proc.returncode==0,"committed tests failed")
 rt=load()

 # Fresh 1: nested supported law.
 tree=binary("stable_div",binary("mul",unary("sat",var("x")),var("y")),unary("abs",var("z")))
 p={"trees":[tree],"rows":[{"x":"2","y":"9","z":"2"}],"queries":[],"include_intercept":False}
 out=rt.compile_basis(p); req(out["pass"] and out["feature_rows"]==[["2"]],"nested exact law failed")

 # Fresh 2: basis identity is independent of data rows.
 p1={"trees":[var("x"),unary("square",var("x"))],"rows":[{"x":"1"},{"x":"2"}],"queries":[]}
 p2={"trees":[var("x"),unary("square",var("x"))],"rows":[{"x":"2"},{"x":"1"}],"queries":[]}
 a=rt.compile_basis(p1); b=rt.compile_basis(p2)
 req(a["pass"] and b["pass"] and a["basis_sha256"]==b["basis_sha256"],"basis identity depends on rows")

 # Fresh 3: unsupported transcendental/fractional operator stays outside proof route.
 out=rt.compile_basis({"trees":[{"op":"sqrt_abs","arg":var("x")}],"rows":[{"x":"4"}]})
 req(out["pass"] is False and out["reason"]=="TREE_BINDING_FAILED","unsupported sqrt entered proof path")

 # Fresh 4: tree shape is exact, not permissive.
 out=rt.compile_basis({"trees":[{"op":"var","name":"x","junk":1}],"rows":[{"x":"1"}]})
 req(out["pass"] is False and "VAR_TREE_EXTRA_FIELDS" in out.get("detail",{}).get("detail",""),"extra tree semantics silently ignored")

 # Fresh 5: exact rational query path.
 out=rt.compile_basis({
   "trees":[binary("safe_div",var("x"),var("y"))],
   "rows":[{"x":"1","y":"2"}],
   "queries":[{"query_id":"q","point":{"x":"3","y":"4"}}],
   "include_intercept":True,
 })
 req(out["pass"] and out["feature_rows"]==[["1","1/2"]],"row exactness failed")
 req(out["query_features"]==[{"query_id":"q","features":["1","3/4"]}],"query exactness failed")
 req(out["terminal_credit_delta"]==0 and out["acceptance_credit_delta"]==0,"credit leak")

 print(json.dumps({
   "schema":"PROJECT_BRAIN_EXACT_RATIONAL_SYMBOLIC_FEATURE_PUBLIC_CAPSULE_VERIFICATION_V1",
   "brain_pr":3168,
   "exact_git_blobs":observed,
   "exact_committed_tests_passed":11,
   "fresh_independent_canary_groups_passed":5,
   "hard_boundary":"SUPPORTED_RATIONAL_SUBGRAMMAR_ONLY__UNSUPPORTED_OPERATORS_GRAMMAR_COMPLETENESS_NOISE_SOUNDNESS_AND_PRIVATE_SCORE_REMAIN_OPEN__ZERO_CREDIT"
 },sort_keys=True))
 print("EXACT_RATIONAL_SYMBOLIC_FEATURE_PUBLIC_CAPSULE_PASS")
if __name__=="__main__": main()
