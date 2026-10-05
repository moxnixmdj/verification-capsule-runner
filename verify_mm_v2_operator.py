#!/usr/bin/env python3
from __future__ import annotations

import ast
import hashlib
import json
import os
import pathlib
import subprocess
import sys

ROOT=pathlib.Path(__file__).resolve().parent
SUBJECT=ROOT/"subject"/"mm_v2_operator"
EXPECTED={
 "canonical/governance/MYSTERYMECHANISM_PUBLIC_OPERATOR_COVERAGE_AUDIT_20261005_V1.json":"25f0e62c8eeea8be2e99f0e5be6d9dc29cf75704",
 "canonical/runtime/mysterymechanism_sparse_symbolic_adapter_v2.py":"6df049693a568ffb60bf2691b95a09a9be651a90",
 "canonical/tests/test_mysterymechanism_sparse_symbolic_adapter_v2.py":"ad81af042e38ecce823c54525bcc509fe6a404a9",
 "canonical/runtime/h100_zero_learned_mechanism_synthesizer_v1.py":"fa77c6a0f4edf214c4237cf1e204b640261622fe",
}

def blob_sha(path:pathlib.Path)->str:
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def main()->int:
    got={p:blob_sha(SUBJECT/p) for p in EXPECTED}
    assert got==EXPECTED,(got,EXPECTED)
    env=dict(os.environ); env["PYTHONPATH"]=str(SUBJECT)
    cp=subprocess.run(
        [sys.executable,"-m","unittest","-v","canonical.tests.test_mysterymechanism_sparse_symbolic_adapter_v2"],
        cwd=SUBJECT,env=env,text=True,capture_output=True,
    )
    print(cp.stdout); print(cp.stderr)
    assert cp.returncode==0,"BRAIN_V2_TESTS_FAILED"

    sys.path.insert(0,str(SUBJECT))
    from canonical.runtime import mysterymechanism_sparse_symbolic_adapter_v2 as mm

    fresh={}
    rows=[{"x":x,"out":1.1+2.7*__import__("math").exp(1/x)}
          for x in (0.7,0.9,1.2,1.6,2.1,2.8,3.7)]
    d=mm.sparse_discover(rows,target="out",max_depth=2,beam_width=48,pair_pool=24)
    assert d["best_candidate"]["loo_nrmse"]<1e-7,d["best_candidate"]
    fresh["composed_exp_reciprocal"]={
        "pass":True,"loo_nrmse":d["best_candidate"]["loo_nrmse"],
        "expression":mm._sparse_expr(d["best_candidate"]),
    }

    import math
    pts=[(0.4,1.1),(0.8,1.7),(1.3,0.9),(1.9,2.4),(2.6,1.2),(3.1,2.8),(3.8,1.5)]
    rows=[{"x":x,"z":z,"out":-0.3+1.9*math.sin(x/z)} for x,z in pts]
    d=mm.sparse_discover(rows,target="out",max_depth=2,beam_width=48,pair_pool=24)
    assert d["best_candidate"]["loo_nrmse"]<1e-7,d["best_candidate"]
    fresh["composed_sin_ratio"]={
        "pass":True,"loo_nrmse":d["best_candidate"]["loo_nrmse"],
        "expression":mm._sparse_expr(d["best_candidate"]),
    }

    src=(SUBJECT/"canonical/runtime/mysterymechanism_sparse_symbolic_adapter_v2.py").read_text()
    tree=ast.parse(src)
    dangerous=[n.func.id for n in ast.walk(tree)
               if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)
               and n.func.id in {"eval","exec"}]
    assert dangerous==[],dangerous
    lower=src.lower()
    for banned in ("subprocess","requests","openai","anthropic"):
        assert banned not in lower,banned

    receipt={
      "schema":"PROJECT_BRAIN_MYSTERYMECHANISM_OPERATOR_EXPANSION_V2_INDEPENDENT_VERIFICATION_V1",
      "status":"PASS__CONTENT_BOUND_EXACT_DIV_RECIPROCAL_EXP_TRIG_COMPOSITION__FRESH_COMPOSED_CHALLENGES_PASS__ZERO_CREDIT",
      "subject_blobs":got,
      "brain_authored_tests":"PASS",
      "fresh_independent_challenges":fresh,
      "boundary":{
        "public_mechbench_formulas_used_as_runtime_lookup":False,
        "private_mysterymechanism_cases_used":0,
        "private_score_claimed":False,
        "dynamic_eval":False,
        "external_learned_capability_provider":False,
        "persistent_learned_bytes":0
      },
      "accounting":{
        "incremental_spend_usd":0,
        "terminal_cases_consumed":0,
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0
      }
    }
    (ROOT/"mm_v2_operator_verification.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print(json.dumps(receipt,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
