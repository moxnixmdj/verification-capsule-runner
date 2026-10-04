#!/usr/bin/env python3
from __future__ import annotations
import collections
import hashlib
import json
import urllib.request

CLASSIC_COMMIT="e49bbfe381c9c0e564b937f1c4e163a2273c65cc"
CLASSIC_PATH="instruction_following_eval/data/input_data.jsonl"
CLASSIC_BLOB="cbe52f6eecf3986fdac745b4acba4da1408eb146"
LIVEBENCH_COMMIT="8f8e5c381a16e3f24257776edd53471fe86f8091"
REG_PATH="livebench/if_runner/instruction_following_eval/instructions_registry.py"
REG_BLOB="903ed738398648c7cfac61d5ffa478c22f1f0891"
EVAL_PATH="livebench/if_runner/instruction_following_eval/evaluation_main.py"
EVAL_BLOB="4a341984936c4d609644a3b77f8c030ac5aa7269"

def get(url:str)->bytes:
    with urllib.request.urlopen(url, timeout=30) as r:
        return r.read()

def git_blob_sha(raw:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

classic=get(f"https://raw.githubusercontent.com/google-research/google-research/{CLASSIC_COMMIT}/{CLASSIC_PATH}")
assert git_blob_sha(classic)==CLASSIC_BLOB
rows=[json.loads(x) for x in classic.decode().splitlines() if x.strip()]
assert len(rows)==541
assert sum(len(r["instruction_id_list"]) for r in rows)==834

dup_rows=[]
affected=collections.Counter()
max_mult=1
for i,row in enumerate(rows):
    c=collections.Counter(row["instruction_id_list"])
    d={k:v for k,v in c.items() if v>1}
    if d:
        dup_rows.append((i,d))
        for k,v in d.items():
            affected[k]+=1
            max_mult=max(max_mult,v)

assert len(dup_rows)==17, len(dup_rows)
assert max_mult==2
assert dict(affected)=={
    "change_case:capital_word_frequency":5,
    "keywords:frequency":3,
    "length_constraints:number_sentences":6,
    "length_constraints:number_words":2,
    "startend:quotation":1,
}, affected

reg=get(f"https://raw.githubusercontent.com/LiveBench/LiveBench/{LIVEBENCH_COMMIT}/{REG_PATH}")
ev=get(f"https://raw.githubusercontent.com/LiveBench/LiveBench/{LIVEBENCH_COMMIT}/{EVAL_PATH}")
assert git_blob_sha(reg)==REG_BLOB
assert git_blob_sha(ev)==EVAL_BLOB
reg_text=reg.decode()
ev_text=ev.decode()

# Conflict registry is generation policy. The evaluator itself accepts an
# arbitrary instruction_id_list and loops over every positional instance.
assert 'INSTRUCTION_CONFLICTS = {' in reg_text
assert 'for index, instruction_id in enumerate(instruction_list):' in ev_text
assert 'instruction.build_description(**(inp.kwargs[index]))' in ev_text
assert 'is_following_list.append(True)' in ev_text
assert 'is_following_list.append(False)' in ev_text

print("LIVEBENCH_LEGACY_DUPLICATE_INPUT_VALIDITY=PASS")
print("public_classic_rows=541")
print("public_instruction_instances=834")
print("duplicate_same_family_rows=17")
print("maximum_same_family_multiplicity=2")
print("affected_ids="+json.dumps(dict(affected),sort_keys=True))
print("deduction=SELF_CONFLICT_IN_GENERATOR_REGISTRY_IS_NOT_EVALUATOR_INPUT_INVALIDITY")
print("runtime_requirement=PRESERVE_EACH_REPEATED_VISIBLE_CONSTRAINT_INSTANCE_IN_PROMPT_ORDER")
print("terminal_case_content_read=0")
print("incremental_spend_usd=0")
