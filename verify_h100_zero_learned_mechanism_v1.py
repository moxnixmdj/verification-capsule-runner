from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SUBJECT=ROOT/"subject"/"h100_zero_learned_mechanism_v1"
RUNTIME=SUBJECT/"canonical"/"runtime"/"h100_zero_learned_mechanism_synthesizer_v1.py"
TESTS=SUBJECT/"canonical"/"tests"/"test_h100_zero_learned_mechanism_synthesizer_v1.py"
GOV=SUBJECT/"canonical"/"governance"/"H100_ZERO_LEARNED_MECHANISM_CANDIDATE_V1.json"

EXPECTED_RUNTIME="fa77c6a0f4edf214c4237cf1e204b640261622fe"
EXPECTED_TESTS="0e5e7ab361d495cb76e6e8644cf2cdd46c733ed8"
EXPECTED_GOV="253715727a8cdbaa5bde6d84a2196debbe96e183"

def git_blob_sha(path:Path)->str:
    data=path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()

assert git_blob_sha(RUNTIME)==EXPECTED_RUNTIME
assert git_blob_sha(TESTS)==EXPECTED_TESTS
assert git_blob_sha(GOV)==EXPECTED_GOV

gov=json.loads(GOV.read_text())
assert gov["schema"]=="PROJECT_BRAIN_H100_ZERO_LEARNED_MECHANISM_CANDIDATE_V1"
assert gov["zero_learned_accounting"]["persistent_learned_artifacts"]==[]
assert gov["zero_learned_accounting"]["persistent_learned_bytes"]==0
assert gov["zero_learned_accounting"]["external_frontier_model_calls"]==0
assert gov["zero_learned_accounting"]["external_learned_capability_calls"]==0
assert gov["accounting"]["acceptance_credit_delta"]==0
assert gov["accounting"]["capability_credit_delta"]==0
assert gov["authority"]["execution"] is False
assert gov["authority"]["promotion"] is False
assert gov["authority"]["fresh_reality"] is False

# Static escape-hatch audit. The candidate is intentionally standard-library-only,
# with no filesystem/network/process/dynamic-code/model import surface.
tree=ast.parse(RUNTIME.read_text(),filename=str(RUNTIME))
allowed_import_roots={"itertools","math","typing","__future__"}
imports=set()
for node in ast.walk(tree):
    if isinstance(node,ast.Import):
        imports.update(alias.name.split(".")[0] for alias in node.names)
    elif isinstance(node,ast.ImportFrom):
        imports.add((node.module or "").split(".")[0])
assert imports<=allowed_import_roots,(imports,allowed_import_roots)

forbidden_calls={"open","eval","exec","compile","__import__","input"}
for node in ast.walk(tree):
    if isinstance(node,ast.Call) and isinstance(node.func,ast.Name):
        assert node.func.id not in forbidden_calls,node.func.id

spec=importlib.util.spec_from_file_location("h100_zero",RUNTIME)
mod=importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)

# 1. Exact single-variable power law.
rows=[{"a":x,"out":3*x*x+2} for x in range(1,13)]
d=mod.discover(rows,target="out")
b=d["candidates"][0]
assert b["structural_signature"]=="identity|monomial|2",b
assert b["nrmse"]<1e-10,b
assert d["learned_parameter_bytes"]==0
assert d["external_learned_capability_calls"]==0

# 2. Multivariable law with division.
rows_ratio=[
    {"foo":x,"bar":z,"out":5*x*x/z+1}
    for x in [1,2,3,4] for z in [1,2,4]
]
dr=mod.discover(rows_ratio,target="out")
br=dr["candidates"][0]
assert br["feature_expression"]=="bar^-1 * foo^2",br
assert br["nrmse"]<1e-10

# 3. Affine sum.
rows_lin=[
    {"x":x,"z":z,"out":2*x-3*z+4}
    for x in [1,2,3,4,5] for z in [2,4,7]
]
dl=mod.discover(rows_lin,target="out")
bl=dl["candidates"][0]
assert bl["family"]=="linear",bl
assert abs(bl["coefficients"][0]-2)<1e-8
assert abs(bl["coefficients"][1]+3)<1e-8
assert abs(bl["intercept"]-4)<1e-8

# 4. Fractional power.
rows_sqrt=[{"x":x,"out":4*math.sqrt(x)+1} for x in [1,4,9,16,25,36,49,64]]
ds=mod.discover(rows_sqrt,target="out")
assert ds["candidates"][0]["feature_expression"]=="x^0.5",ds["candidates"][0]

# 5. Continuous real-exponent recovery on the public MysteryMechanism stream-power shape.
rows_public=[
    {"x1":25.5646,"x2":0.1859,"out":0.0012396},
    {"x1":0.1108,"x2":0.0187,"out":-0.0000064},
    {"x1":100,"x2":0.05,"out":0.0008841},
    {"x1":10000,"x2":0.05,"out":0.0082336},
    {"x1":100,"x2":0.5,"out":0.0049850},
    {"x1":10000,"x2":0.5,"out":0.0454408},
    {"x1":1000,"x2":0.2,"out":0.0078693},
]
dp=mod.discover(rows_public,target="out")
bp=dp["candidates"][0]
assert bp["family"]=="log_power",bp
assert abs(bp["exponents"][0]-0.4822)<0.01,bp
assert abs(bp["exponents"][1]-0.7478)<0.01,bp
assert bp["nrmse"]<0.03,bp

# 6. Public task budget shape: d=2 -> four bound corners plus center, exactly 2d+1 probes.
design=mod.design_initial_probes({"x1":[0.1,10000],"x2":[0.001,0.5]})
assert design["budget"]==5,design
assert len(design["points"])==5,design
assert design["points"][0]=={"x1":0.1,"x2":0.001},design
assert design["points"][3]=={"x1":10000.0,"x2":0.5},design
assert design["learned_parameter_bytes"]==0

# 7. Surface renaming must not destroy structural transfer signature.
rows_rename=[
    {"u":x,"v":z,"res":2*x*x/z-4}
    for x in [2,3,5,7] for z in [1,3,6]
]
br2=mod.discover(rows_rename,target="res")["candidates"][0]
match=mod.structural_match(br,br2)
assert match["match"] is True,match
assert match["surface_variable_names_ignored"] is True

# 8. An irrelevant variable must not beat the exact simpler relation.
rows_noise=[
    {"x":x,"noise":((-1)**i)*(i+3),"out":7*x*x+1}
    for i,x in enumerate(range(1,13))
]
dn=mod.discover(rows_noise,target="out")
assert dn["candidates"][0]["feature_expression"]=="x^2",dn["candidates"][0]

# 9. Out-of-grammar relation must expand, not force a false law.
rows_sine=[{"x":x/3,"out":math.sin(x/3)} for x in range(1,25)]
do=mod.discover(rows_sine,target="out")
jo=mod.judge(do,rows_sine)
assert jo["status"]=="EXPAND_MECHANISM_LANGUAGE",jo
assert jo["candidate"] is None

# 10. Distinct plausible candidates generate an informative probe.
c1={"family":"monomial","variables":["x"],"exponents":[1],"intercept":0,"scale":1,
    "target_transform":"identity","target_sign":1,"structural_signature":"identity|monomial|1"}
c2={"family":"monomial","variables":["x"],"exponents":[2],"intercept":0,"scale":1,
    "target_transform":"identity","target_sign":1,"structural_signature":"identity|monomial|2"}
probe=mod.propose_discriminator([c1,c2],[{"x":1},{"x":2},{"x":3},{"x":4},{"x":5}])
assert probe["status"]=="DISCRIMINATOR_FOUND",probe
assert probe["disagreement"]>0

# 11. Non-finite evidence fails closed.
bad=[{"x":i,"out":float(i)} for i in range(1,6)]
bad[2]["x"]=math.inf
try:
    mod.discover(bad,target="out")
    raise AssertionError("NONFINITE_INPUT_ACCEPTED")
except mod.MechanismSynthesisError:
    pass

print("PASS: exact H100 zero-learned candidate blobs verified")
print("PASS: runtime import/escape-hatch audit is deterministic standard-library only")
print("PASS: power, ratio, affine, fractional and continuous-power mechanism recovery")
print("PASS: public 2d+1 bound-probe design, surface invariance, distractor rejection")
print("PASS: out-of-grammar fail-closed expansion and disagreement probe generation")
print("PASS: zero learned bytes and zero terminal credit preserved")
