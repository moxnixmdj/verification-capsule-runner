from __future__ import annotations
import hashlib,json
from pathlib import Path
from canonical.runtime.h100_unichart_chartqa_preservation_runner_v1 import (
    make_model_and_processor,load_fp32_donor,answer_case,relaxed_correct
)
from canonical.runtime.h100_unichart_structural_holdout_runner_v1 import load_structural

PRE=Path("h100_unichart_fresh_capability_holdout_v1.json")
SOURCE=Path("/tmp/h100fresh/pytorch_model.bin")
PACK=Path("/tmp/h100fresh/chartqa_mse_structural.h100uc")
IMG=Path("/tmp/h100fresh/images")
EXPECTED_PRE_GIT_BLOB="e4b42fb7e0a2210ce00eae64136567319091f4d6"
EXPECTED_SOURCE_SHA="4407db60801a20bcf254946acfee6727491ef1739ad7b4d3abbf87b7c75e7229"
EXPECTED_PACK_SHA="17fc7d37f6c6e8457d53dd93efff365b17850acf5810ba3067bb06c7c226cb14"
EXPECTED_PACK_BYTES=94686795
ANCILLARY_BYTES=5313202
EXPECTED_COMPLETE=99999997

def sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(8*1024*1024),b""):
            h.update(b)
    return h.hexdigest()

raw_pre=PRE.read_bytes()
pre_blob=hashlib.sha1(b"blob "+str(len(raw_pre)).encode()+b"\0"+raw_pre).hexdigest()
assert pre_blob==EXPECTED_PRE_GIT_BLOB
assert sha(SOURCE)==EXPECTED_SOURCE_SHA
assert sha(PACK)==EXPECTED_PACK_SHA
assert PACK.stat().st_size==EXPECTED_PACK_BYTES
assert PACK.stat().st_size+ANCILLARY_BYTES==EXPECTED_COMPLETE

pre=json.load(PRE.open())
cases=pre["cases"]
assert len(cases)==100
assert pre["candidate_precommit"]["packed_sha256"]==EXPECTED_PACK_SHA
assert pre["candidate_precommit"]["complete_bundle_bytes"]==EXPECTED_COMPLETE

model,proc=make_model_and_processor()
load_fp32_donor(model,SOURCE)
fp=[]; fp_correct=0
for i,c in enumerate(cases,1):
    pred=answer_case(model,proc,IMG/c["imgname"],c["query"])
    ok=relaxed_correct(c["label"],pred)
    fp_correct+=int(ok)
    fp.append({"index":i,"id":c["id"],"label":c["label"],"prediction":pred,"correct":ok})
    print(json.dumps({"subject":"fp32",**fp[-1]}),flush=True)
del model

model,proc=make_model_and_processor()
load=load_structural(model,PACK,EXPECTED_PACK_SHA)
packed=[]; pc=0
for i,c in enumerate(cases,1):
    pred=answer_case(model,proc,IMG/c["imgname"],c["query"])
    ok=relaxed_correct(c["label"],pred)
    pc+=int(ok)
    packed.append({"index":i,"id":c["id"],"label":c["label"],"prediction":pred,"correct":ok})
    print(json.dumps({"subject":"packed",**packed[-1]}),flush=True)

gate=pre["pass_gate"]
fp_acc=fp_correct/100
p_acc=pc/100
passed=(
    fp_acc>=float(gate["minimum_fp32_relaxed_accuracy"])
    and p_acc>=fp_acc-float(gate["packed_noninferiority_margin_absolute"])
    and EXPECTED_COMPLETE<=100_000_000
)
out={
    "schema":"PROJECT_BRAIN_H100_UNICHART_FRESH_CAPABILITY_V2_PROVIDER_DIVERSE_REPLAY_V1",
    "status":"PASS__INDEPENDENT_CARRIER_FRESH_CAPABILITY_REPLAY" if passed else "FAIL__INDEPENDENT_CARRIER_FRESH_CAPABILITY_REPLAY",
    "carrier":"GITHUB_HOSTED_UBUNTU",
    "precommit_git_blob_sha":EXPECTED_PRE_GIT_BLOB,
    "source_sha256":EXPECTED_SOURCE_SHA,
    "packed_sha256":EXPECTED_PACK_SHA,
    "packed_bytes":EXPECTED_PACK_BYTES,
    "ancillary_bytes":ANCILLARY_BYTES,
    "complete_bundle_bytes":EXPECTED_COMPLETE,
    "fp32_correct":fp_correct,
    "fp32_total":100,
    "fp32_accuracy":fp_acc,
    "packed_correct":pc,
    "packed_total":100,
    "packed_accuracy":p_acc,
    "packed_minus_fp32_accuracy":p_acc-fp_acc,
    "noninferiority_pass":passed,
    "fp32_rows":fp,
    "packed_rows":packed,
    "load":load,
    "hard_nonclaims":[
        "PUBLIC_CHARTQA_CAPABILITY_ONLY",
        "FROZEN_V2_100_CASE_HOLDOUT",
        "NO_CHARTOGRAPHY_GE_89_PROOF",
        "NO_FULL_H100_TERMINAL_PROOF"
    ],
    "h100_terminal_credit_delta":0
}
Path("h100_unichart_fresh_independent_replay_result_v1.json").write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
print(json.dumps({k:out[k] for k in ["status","fp32_correct","packed_correct","complete_bundle_bytes","packed_sha256"]},indent=2,sort_keys=True))
if not passed:
    raise SystemExit(2)
