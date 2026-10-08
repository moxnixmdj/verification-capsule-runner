from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
RUNTIME=ROOT/"canonical/runtime/exact_linear_parameter_polytope_v1.py"
TESTS=ROOT/"canonical/tests/test_exact_linear_parameter_polytope_v1.py"
GOV=ROOT/"canonical/governance/MYSTERYMECHANISM_EXACT_LINEAR_PARAMETER_POLYTOPE_20261008_V1.json"
EXPECTED={
    RUNTIME:"b3db128a42d9b9620fa73f719ae993dd4bed2107",
    TESTS:"74edb668d071964040e952cb307b243d4cae0250",
    GOV:"093a778d1e72dffe40bd619eb2444e40b787969e",
}


def blob_sha(path):
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()


def req(cond,msg):
    if not cond:
        raise AssertionError(msg)


def load_runtime():
    spec=importlib.util.spec_from_file_location("polytope_exact",RUNTIME)
    req(spec is not None and spec.loader is not None,"runtime import failed")
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def obs(features,lo,hi):
    return {"features":features,"output_interval":[lo,hi]}


def base():
    return {
        "feature_semantics_bound":True,
        "observation_intervals_sound":True,
        "observations":[
            obs(["1","0"],"9/10","11/10"),
            obs(["1","1"],"29/10","31/10"),
        ],
        "queries":[{"query_id":"x2","features":["1","2"]}],
    }


def main():
    observed={}
    for path,expected in EXPECTED.items():
        actual=blob_sha(path)
        req(actual==expected,f"blob drift {path}: {actual} != {expected}")
        observed[str(path.relative_to(ROOT))]=actual

    governance=json.loads(GOV.read_text())
    req(all(v==0 for v in governance["accounting"].values()),"governance grants credit")
    req("NO CLAIM PUBLIC MYSTERYMECHANISM NOISE HAS A KNOWN FINITE BOUND" in governance["hard_nonclaims"],
        "noise-bound nonclaim missing")

    env=dict(os.environ)
    env["PYTHONPATH"]=str(ROOT)
    proc=subprocess.run(
        [sys.executable,"-m","unittest","-v","canonical.tests.test_exact_linear_parameter_polytope_v1"],
        cwd=ROOT,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=False,
    )
    print(proc.stdout)
    req(proc.returncode==0,"exact copied Brain tests failed")

    rt=load_runtime()

    # Fresh canary 1: noisy line exact range and stable vertex digest under row order.
    p=base()
    a=rt.solve(p)
    req(a["pass"] is True and a["query_predictions"][0]["prediction_interval"]==["47/10","53/10"],
        "fresh noisy-line range mismatch")
    p2=base()
    p2["observations"]=list(reversed(p2["observations"]))
    b=rt.solve(p2)
    req(b["pass"] is True and a["vertex_set_sha256"]==b["vertex_set_sha256"],
        "vertex identity depends on observation ordering")

    # Fresh canary 2: contradictory exact interval must be infeasible.
    p={
        "feature_semantics_bound":True,
        "observation_intervals_sound":True,
        "observations":[obs(["1"],"0","0"),obs(["1"],"1","1")],
        "queries":[],
    }
    out=rt.solve(p)
    req(out["pass"] is False and out["reason"]=="NO_FEASIBLE_BOUNDED_PARAMETER_POLYTOPE_VERTEX",
        "contradictory observations admitted")

    # Fresh canary 3: exact 3-parameter identity case.
    p={
        "feature_semantics_bound":True,
        "observation_intervals_sound":True,
        "observations":[
            obs(["1","0","0"],"1","1"),
            obs(["1","1","0"],"3","3"),
            obs(["1","0","1"],"4","4"),
        ],
        "queries":[{"query_id":"both","features":["1","2","3"]}],
    }
    out=rt.solve(p)
    req(out["pass"] is True and out["coefficient_bounds"]==[["1","1"],["2","2"],["3","3"]],
        "3D exact coefficient recovery failed")
    req(out["query_predictions"][0]["prediction_interval"]==["14","14"],
        "3D exact prediction failed")

    # Fresh canary 4: malformed interval order and duplicate query IDs fail closed.
    p=base()
    p["observations"][0]["output_interval"]=["2","1"]
    out=rt.solve(p)
    req(out["pass"] is False and "INTERVAL_ORDER_INVALID" in out["reason"],
        "reversed observation interval admitted")

    p=base()
    p["queries"]=[
        {"query_id":"dup","features":["1","2"]},
        {"query_id":"dup","features":["1","3"]},
    ]
    out=rt.solve(p)
    req(out["pass"] is False and "QUERY_ID_INVALID_OR_DUPLICATE" in out["reason"],
        "duplicate query identity admitted")

    # Fresh canary 5: proof gates remain real, not decorative flags.
    p=base()
    p["feature_semantics_bound"]=False
    out=rt.solve(p)
    req(out["pass"] is False and out["reason"]=="FEATURE_SEMANTICS_UNBOUND",
        "unbound feature semantics passed")
    p=base()
    p["observation_intervals_sound"]=False
    out=rt.solve(p)
    req(out["pass"] is False and out["reason"]=="OBSERVATION_INTERVAL_SOUNDNESS_UNPROVED",
        "unproved observation interval soundness passed")

    receipt={
        "schema":"PROJECT_BRAIN_EXACT_LINEAR_PARAMETER_POLYTOPE_PUBLIC_CAPSULE_VERIFICATION_V1",
        "brain_pr":3163,
        "exact_git_blobs":observed,
        "exact_committed_tests_passed":11,
        "fresh_independent_canary_groups_passed":5,
        "hard_boundary":"EXACT_COEFFICIENT_POLYTOPE_ONLY__FEATURE_SEMANTICS_NOISE_INTERVAL_SOUNDNESS_AND_FAMILY_COVERAGE_REMAIN_EXTERNAL_PREMISES__ZERO_MYSTERYMECHANISM_OR_TERMINAL_CREDIT",
    }
    print(json.dumps(receipt,sort_keys=True))
    print("EXACT_LINEAR_PARAMETER_POLYTOPE_PUBLIC_CAPSULE_PASS")


if __name__=="__main__":
    main()
