#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SUBJECT=ROOT/"subject/h100_primitive_repair_v1"
RUNTIME=SUBJECT/"canonical/runtime/h100_zero_learned_parametric_unary_v1.py"
RUNTIME_TESTS=SUBJECT/"canonical/tests/test_h100_zero_learned_parametric_unary_v1.py"
REPAIR=SUBJECT/"canonical/runtime/h100_zero_learned_primitive_repair_v1.py"
REPAIR_TESTS=SUBJECT/"canonical/tests/test_h100_zero_learned_primitive_repair_v1.py"
PRE2=SUBJECT/"canonical/governance/H100_ZERO_LEARNED_PRIMITIVE_REPAIR_PREEXPOSURE_V1.json"
CAND=SUBJECT/"canonical/governance/H100_ZERO_LEARNED_PRIMITIVE_REPAIR_CANDIDATE_V1.json"

EXPECTED={
 RUNTIME:"6a77f80e2cf01b079fcf7b688689d08a11b47c32",
 RUNTIME_TESTS:"b2e04c9ee497ed51a54d9982ca6b9bf47f75c465",
 REPAIR:"2c05b8f7aaf4d8c4c66fe2cf163da858832c4f8b",
 REPAIR_TESTS:"aded2cae8e32f8634502c7a41df9a0b9e7160cd4",
 PRE2:"faddeb9bff2c5a317c25f963c3f267ab993f7a22",
 CAND:"e818777cf2075202edee0c73eaaff60101923144",
}


def require(x,msg):
 if not x: raise AssertionError(msg)


def blob(path):
 b=path.read_bytes()
 return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()


def load_module(path,name):
 spec=importlib.util.spec_from_file_location(name,path)
 require(spec is not None and spec.loader is not None,"IMPORT_SPEC_FAILED")
 m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def fresh_checks(m):
 xs=[-5,-4,-3,-2,-1,-0.25,0,0.4,1.2,2.3,3.7,5.1]
 # Deliberately different from phase-1 sine parameters.
 omega=2.2713
 phase=-0.37
 rows=[{"x":x,"y":0.61-0.093*x+1.27*math.sin(omega*x+phase)} for x in xs]
 out=m.discover(rows,target="y")
 require(out["status"]=="EXACT_CANDIDATE_FOUND","FRESH_SINE_NOT_EXACT:"+repr(out))
 c=out["best_candidate"]
 require(c["family"]=="linear_trend_sinusoid","FRESH_SINE_WRONG_FAMILY")
 for x in (-4.4,-1.33,-0.11,0.77,2.91,4.6):
  want=0.61-0.093*x+1.27*math.sin(omega*x+phase)
  got=m.predict(c,{"x":x})
  require(abs(got-want)<=2e-6,f"FRESH_SINE_HOLDOUT:{x}:{got}:{want}")

 # Deliberately different scale/rate.
 rows=[{"x":x,"y":2.31*math.exp(0.4817*abs(x))} for x in xs]
 out=m.discover(rows,target="y")
 require(out["status"]=="EXACT_CANDIDATE_FOUND","FRESH_EXP_NOT_EXACT")
 c=out["best_candidate"]
 require(c["family"]=="exp_abs","FRESH_EXP_WRONG_FAMILY")
 for x in (-4.7,-0.7,0.19,1.71,4.33):
  require(abs(m.predict(c,{"x":x})-2.31*math.exp(0.4817*abs(x)))<=1e-7,"FRESH_EXP_HOLDOUT")

 # Deliberately different levels and observed threshold.
 rows=[{"x":x,"y":-3.2 if x<1.2 else 4.7} for x in xs]
 out=m.discover(rows,target="y")
 require(out["status"]=="EXACT_CANDIDATE_FOUND","FRESH_STEP_NOT_EXACT")
 c=out["best_candidate"]
 require(c["family"]=="threshold_step","FRESH_STEP_WRONG_FAMILY")
 require(abs(float(c["threshold"])-1.2)<=1e-12,"FRESH_STEP_THRESHOLD")
 for x in (-2.1,0.9,1.1999,1.2,2.7):
  want=-3.2 if x<1.2 else 4.7
  require(abs(m.predict(c,{"x":x})-want)<=1e-8,"FRESH_STEP_HOLDOUT")

 rows=[{"x":x,"y":0.23*x**3-0.91*x+0.17} for x in xs]
 out=m.discover(rows,target="y")
 require(out["status"]=="PARAMETRIC_FAMILIES_NOT_EXACT","CUBIC_FALSE_EXACT")

 for out in [
  m.discover([{"x":x,"y":math.exp(0.2*abs(x))} for x in xs],target="y"),
  m.discover([{"x":x,"y":-1.0 if x<0 else 1.0} for x in xs],target="y")
 ]:
  require(out["persistent_learned_bytes"]==0,"LEARNED_BYTES_NONZERO")
  require(out["external_frontier_model_calls"]==0,"FRONTIER_CALL_NONZERO")
  require(out["external_learned_capability_calls"]==0,"LEARNED_PROVIDER_NONZERO")
  require(out["random_search"] is False,"RANDOM_SEARCH_TRUE")
  require(out["dynamic_code_execution"] is False,"DYNAMIC_EXEC_TRUE")


def governance_checks():
 d=json.loads(CAND.read_text())
 b=d["exact_bound_components"]
 require(b["canonical/governance/H100_ZERO_LEARNED_PRIMITIVE_REPAIR_PREEXPOSURE_V1.json"]==EXPECTED[PRE2],"PRE2_BINDING")
 require(b["canonical/runtime/h100_zero_learned_parametric_unary_v1.py"]==EXPECTED[RUNTIME],"RUNTIME_BINDING")
 require(b["canonical/tests/test_h100_zero_learned_parametric_unary_v1.py"]==EXPECTED[RUNTIME_TESTS],"RUNTIME_TEST_BINDING")
 require(b["canonical/runtime/h100_zero_learned_primitive_repair_v1.py"]==EXPECTED[REPAIR],"REPAIR_BINDING")
 require(b["canonical/tests/test_h100_zero_learned_primitive_repair_v1.py"]==EXPECTED[REPAIR_TESTS],"REPAIR_TEST_BINDING")
 require(d["chronology"]["phase2_outcomes_observed_before_candidate"] is False,"OUTCOME_CHRONOLOGY_DIRTY")
 require(d["primitive_design"]["persistent_learned_bytes"]==0,"GOV_LEARNED_BYTES_NONZERO")
 require(d["primitive_design"]["external_learned_capability_calls"]==0,"GOV_EXTERNAL_PROVIDER_NONZERO")


def main():
 for p,h in EXPECTED.items():
  require(blob(p)==h,f"EXACT_BLOB_MISMATCH:{p.name}:{blob(p)}:{h}")
 governance_checks()
 sys.path.insert(0,str(SUBJECT))
 m=load_module(RUNTIME,"parametric_subject")
 fresh_checks(m)
 print(json.dumps({
  "status":"INDEPENDENT_ADVERSARIAL_PASS",
  "exact_subject_blobs":True,
  "fresh_sinusoid_parameter_generalization":"PASS",
  "fresh_exponential_parameter_generalization":"PASS",
  "fresh_threshold_step_generalization":"PASS",
  "nonmatching_cubic_fail_closed":"PASS",
  "persistent_learned_bytes":0,
  "external_learned_capability_calls":0,
  "phase2_outcomes_consumed_by_this_verifier":0
 },indent=2,sort_keys=True))


if __name__=="__main__": main()
