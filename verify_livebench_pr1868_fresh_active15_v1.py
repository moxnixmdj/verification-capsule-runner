#!/usr/bin/env python3
"""Fresh post-freeze active15-conditional LiveBench equivalent evaluation.

The candidate blob was frozen in Brain PR #1868 before this verifier commit
exists. The execution seed is derived from this verifier commit identity, so the
candidate cannot be tuned to the sampled rows without changing its pinned blob.

No frozen terminal rows, prompts, instruction lists, kwargs, answers, or scores
are read.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import random
import subprocess
import sys
from collections import Counter

import numpy as np

ROOT=Path(__file__).resolve().parent
SUB=ROOT/"subject/livebench_legacy15_joint_historical_replay_v1_20261004"
SCORER=Path("/tmp/livebench")
GEN=Path("/tmp/livebench-gen")

EXPECTED={
    SUB/"canonical/runtime/livebench_legacy15_joint_witness_v1.py":"ec0760696f67fa5c631a949bbf64e572243a8736",
    SUB/"canonical/runtime/livebench_legacy_visible_constraint_compiler_v4.py":"721207ba39d502e3f610289578e9d5bab78b1fcc",
    SUB/"canonical/runtime/livebench_frozen_active_legacy15_v1.py":"34440ee69322e9d519cbe656cb03c55683a8b9c6",
    SCORER/"livebench/if_runner/instruction_following_eval/instructions.py":"4997bab885a676d92545fd91a9a20b48d234a2b2",
    SCORER/"livebench/if_runner/instruction_following_eval/instructions_registry.py":"903ed738398648c7cfac61d5ffa478c22f1f0891",
    SCORER/"livebench/process_results/instruction_following/utils.py":"8ce01747887ec0792c8f024e1972e34ece781676",
    GEN/"livebench/if_runner/live_data.py":"6ff390d6885cf90f88d9d36959735cb327613edc",
}

def blob(path:Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

for p,e in EXPECTED.items():
    g=blob(p)
    assert g==e,(str(p),g,e)

sys.path.insert(0,str(SUB))
sys.path.insert(0,str(SCORER/"livebench/if_runner"))
from canonical.runtime.livebench_legacy15_joint_witness_v1 import solve
from canonical.runtime.livebench_frozen_active_legacy15_v1 import ACTIVE_IDS
from instruction_following_eval import instructions_registry as registry

spec=importlib.util.spec_from_file_location("historical_live_data",GEN/"livebench/if_runner/live_data.py")
assert spec and spec.loader
live_data=importlib.util.module_from_spec(spec)
spec.loader.exec_module(live_data)

head=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
seed_digest=hashlib.sha256((head+"|ec0760696f67fa5c631a949bbf64e572243a8736|FRESH_ACTIVE15_V1").encode()).digest()
np_seed=int.from_bytes(seed_digest[:4],"big")
py_seed=int.from_bytes(seed_digest[4:8],"big")
np.random.seed(np_seed)
random.seed(py_seed)

# The published LiveBench appendix marks these exact 15 families as the
# selected real-world/verifiable support (despite an internally inconsistent
# caption saying 16). The terminal support commitment independently opens to
# the same exact 15 identities. Reuse the historical generator's mechanics:
# draw cardinality uniformly from 2..5, draw identities uniformly without
# replacement, then apply its conflict-removal procedure.
active_list=list(ACTIVE_IDS)
samples_to_draw=np.random.randint(2,6,200)
raw=[
    np.random.choice(active_list,int(draw),replace=False).tolist()
    for draw in samples_to_draw
]
deconf=live_data.check_for_conflitcs(raw)
selected=[tuple(ids) for ids in deconf]
assert len(selected)==200
assert all(ids and set(ids)<=set(ACTIVE_IDS) for ids in selected)
drawn=200

BASE=(
    "The following are the beginning sentences of a news article from the Guardian.\n"
    "-------\n"
    "A fresh synthetic source paragraph is used only to carry instruction constraints.\n"
    "-------\n"
    "Please summarize based on the sentences provided."
)
REPEAT_MARKER="First repeat the request word for word without change,"

scores=[]
full=0
runtime_blocks=0
by_size=Counter()
by_status=Counter()
by_failed=Counter()
shape_counts=Counter()

for ids in selected:
    descriptions=[]
    records=[]
    for iid in ids:
        inst=registry.INSTRUCTION_DICT[iid](iid)
        desc=inst.build_description()
        kw=dict(inst.get_instruction_args() or {})
        descriptions.append(desc)
        records.append([iid,kw])
    prompt=BASE+" "+" ".join(descriptions)
    if "combination:repeat_prompt" in ids:
        prefix=prompt.split(REPEAT_MARKER,1)[0]
        for rec in records:
            if rec[0]=="combination:repeat_prompt":
                rec[1]["prompt_to_repeat"]=prefix
                break

    out=solve(prompt)
    status=str(out.get("status") or "")
    by_status[status]+=1
    shape_counts["+".join(sorted(ids))]+=1
    if status!="PASS_CANDIDATE_JOINT_LEGACY15_WITNESS":
        runtime_blocks+=1
        scores.append(0.0)
        by_size[len(ids)]+=0.0
        continue

    response=str(out.get("response") or "")
    truths=[]
    for iid,kw in records:
        inst=registry.INSTRUCTION_DICT[iid](iid)
        inst.build_description(**kw)
        try:
            ok=bool(inst.check_following(response))
        except Exception:
            ok=False
        truths.append(ok)
        if not ok:
            by_failed[iid]+=1
    all_true=bool(truths) and all(truths)
    ratio=sum(truths)/len(truths)
    score=(int(all_true)+ratio)/2
    scores.append(score)
    by_size[len(ids)]+=score
    full+=int(all_true)

mean_score=sum(scores)/len(scores)
threshold=0.6573775
score_src=(SCORER/"livebench/process_results/instruction_following/utils.py").read_text()
assert "avg_score = (score_1 + score_2) / 2" in score_src

receipt={
  "schema":"PROJECT_BRAIN_LIVEBENCH_FRESH_ACTIVE15_CONDITIONAL_EQUIVALENT_EVAL_V1",
  "status":"PASS_THRESHOLD" if mean_score>=threshold else "FAIL_THRESHOLD",
  "candidate_blob":"ec0760696f67fa5c631a949bbf64e572243a8736",
  "verifier_head":head,
  "seed_sha256":seed_digest.hex(),
  "numpy_seed":np_seed,
  "python_seed":py_seed,
  "population":{
    "rows":len(selected),
    "historical_generator_draw_count":drawn,
    "sampling_law":"CARDINALITY_UNIFORM_2_TO_5__IDENTITIES_UNIFORM_WITHOUT_REPLACEMENT_FROM_FROZEN_ACTIVE15__HISTORICAL_CONFLICT_REMOVAL",
    "max_instructions":5
  },
  "results":{
    "mean_score":mean_score,
    "threshold":threshold,
    "margin":mean_score-threshold,
    "full_score_rows":full,
    "runtime_block_rows":runtime_blocks,
    "minimum_case_score":min(scores),
    "maximum_case_score":max(scores)
  },
  "status_counts":dict(by_status),
  "failed_instruction_counts":dict(by_failed),
  "shape_count":len(shape_counts),
  "terminal_boundary":{
    "terminal_rows_read":0,
    "terminal_prompts_read":0,
    "terminal_instruction_ids_read":0,
    "terminal_kwargs_read":0,
    "terminal_scores_read":0
  },
  "credit":{
    "acceptance":False,
    "family":False,
    "capability":False,
    "ownership":False
  },
  "hard_nonclaims":[
    "THIS_IS_A_FRESH_ACTIVE15_SELECTED_SUPPORT_SAMPLE_NOT_THE_QUARANTINED_TERMINAL_200",
    "ROW_LEVEL_GENERATION_LAW_EQUIVALENCE_MUST_BE_INDEPENDENTLY_JUSTIFIED_BEFORE_ACCEPTANCE_PROMOTION",
    "PASS_THRESHOLD_ALONE_DOES_NOT_PROMOTE_LIVEBENCH"
  ]
}
Path("livebench_pr1868_fresh_active15_v1_receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print(json.dumps(receipt,sort_keys=True))
# Exit nonzero only for mechanical verifier corruption. Threshold outcome is data.
assert len(scores)==200
assert all(0.0<=x<=1.0 for x in scores)
