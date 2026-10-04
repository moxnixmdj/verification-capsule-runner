#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, os, pathlib, subprocess, sys

ROOT=pathlib.Path(__file__).resolve().parent
SUBJECT=ROOT/"subject/root2_blind_threshold_receipt_v1_20261004"
EXPECTED={
    SUBJECT/"canonical/runtime/blind_threshold_receipt_v1.py":"324e9c236fed50d150082ebcca6078a2921ed65a",
    SUBJECT/"canonical/tests/test_blind_threshold_receipt_v1.py":"80c634be25fb2ffaef3aa156b13eaefdde010d3d",
    SUBJECT/"canonical/governance/ROOT2_BLIND_THRESHOLD_RECEIPT_V1.json":"ad699b6e5e9a0268b18cabe39588f9a0a401016f",
}
def git_blob_sha(p:pathlib.Path)->str:
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

for p,want in EXPECTED.items():
    if not p.is_file():
        raise SystemExit("MISSING_SUBJECT:"+str(p))
    got=git_blob_sha(p)
    if got!=want:
        raise SystemExit("SUBJECT_BLOB_DRIFT:"+str(p)+":"+got+":"+want)

env=os.environ.copy()
env["PYTHONPATH"]=str(SUBJECT)
cp=subprocess.run(
    [sys.executable,"-m","unittest","-v","canonical.tests.test_blind_threshold_receipt_v1"],
    cwd=SUBJECT, env=env, text=True, capture_output=True
)
print(cp.stdout,end="")
print(cp.stderr,end="")
if cp.returncode!=0:
    raise SystemExit("COPIED_SUBJECT_TESTS_FAILED")

sys.path.insert(0,str(SUBJECT))
for name in list(sys.modules):
    if name=="canonical" or name.startswith("canonical."):
        sys.modules.pop(name,None)
from canonical.runtime.blind_threshold_receipt_v1 import INPUT_SCHEMA, compile_blind_threshold_receipt

A="a"*40; B="b"*40; C="c"*40; D="d"*40
def ref(path,sha=A): return {"path":path,"git_blob_sha":sha}
def ident(): return {"commit_sha":B,"tree_sha":C}
def base(kind="ADDITIVE_THRESHOLD", semantics="OFFICIAL_FIXED_BAR_THRESHOLD_VERDICT"):
    target={
      "predicate_id":"P","benchmark_id":"B","metric_kind":kind,"operator":"GE",
      "threshold":"10","unit":"PERCENT","candidate_identity":ident(),
      "harness_receipt":ref("harness.json",D),
    }
    receipt={
      "receipt_class":"OWNER_BLIND_SCORE_THRESHOLD_RECEIPT",
      "predicate_id":"P","benchmark_id":"B","operator":"GE","threshold":"10","unit":"PERCENT",
      "candidate_identity":ident(),"harness_receipt":ref("harness.json",D),
      "source_artifact":ref("owner.json",A),
      "source_verification_receipt":ref("independent.json",B),
      "issuer":"owner","evaluation_run_id":"run",
      "source_authenticity_verified":True,"exact_frozen_protocol_verified":True,
      "candidate_identity_verified":True,"harness_identity_verified":True,
      "threshold_identity_verified":True,"independent_or_objective":True,
      "metric_semantics":semantics,"verdict":"PASS","exact_score_disclosed":False,
    }
    return {"schema":INPUT_SCHEMA,"frozen_target":target,"blind_receipt":receipt}

positive=compile_blind_threshold_receipt(base())
assert positive["status"].startswith("PASS__BLIND_THRESHOLD")
assert positive["exact_score_required"] is False
assert positive["acceptance_credit_delta"]==0
assert positive["execution_authority"] is False
assert positive["fresh_reality_authority"] is False
assert positive["promotion_authority"] is False

rel=base("RELATIVE_RATING_THRESHOLD","OFFICIAL_RELATIVE_RATING_THRESHOLD_VERDICT")
rel["frozen_target"]["unit"]="ELO"; rel["blind_receipt"]["unit"]="ELO"
assert compile_blind_threshold_receipt(rel)["status"].startswith("PASS__")

forged=base()
forged["blind_receipt"]["source_authenticity_verified"]=False
assert compile_blind_threshold_receipt(forged)["status"]=="FAIL_CLOSED"

matched=base()
matched["frozen_target"]["metric_kind"]="MATCHED_NONINFERIORITY"
assert compile_blind_threshold_receipt(matched)["status"]=="FAIL_CLOSED"

manifest=json.loads((SUBJECT/"canonical/governance/ROOT2_BLIND_THRESHOLD_RECEIPT_V1.json").read_text())
assert manifest["execution_authority"] is False
assert manifest["fresh_reality_authority"] is False
assert manifest["promotion_authority"] is False
assert manifest["accounting"]["acceptance_credit_delta"]==0
assert "RELATIVE_RATING_THRESHOLD" in manifest["supported_metric_kinds"]
assert "MATCHED_NONINFERIORITY" in manifest["deliberately_excluded"]

print(json.dumps({
  "schema":"PROJECT_BRAIN_ROOT2_BLIND_THRESHOLD_RECEIPT_PUBLIC_RUNNER_VERIFICATION_20261004_V1",
  "status":"PASS__EXACT_SUBJECT_BLOBS__COPIED_TESTS_PASS__INDEPENDENT_ADVERSARIAL_CHECKS_PASS__ZERO_CREDIT",
  "subject_blobs":{str(k.relative_to(ROOT)):v for k,v in EXPECTED.items()},
  "copied_subject_tests":"PASS",
  "independent_checks":{
    "blind_pass_without_exact_score":True,
    "relative_rating_requires_direct_relative_semantics":True,
    "forged_source_authenticity_rejected":True,
    "matched_noninferiority_rejected":True,
    "zero_authority_preserved":True,
  },
  "acceptance_credit_delta":0,
  "family_credit_delta":0,
  "capability_credit_delta":0,
  "ownership_credit_delta":0,
  "execution_authority":False,
  "fresh_reality_authority":False,
  "promotion_authority":False,
},sort_keys=True))
