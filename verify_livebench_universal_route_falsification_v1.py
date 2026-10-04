from __future__ import annotations
import inspect, json, sys
from pathlib import Path

LB=Path("/tmp/LiveBench")
GEN=Path("/tmp/LiveBenchGen")
sys.path.insert(0,str(LB/"livebench/if_runner"))

from instruction_following_eval import instructions_registry as registry
from instruction_following_eval import instructions
from instruction_following_eval import instructions_util

EXPECTED={
    LB/"livebench/if_runner/instruction_following_eval/instructions.py":"4997bab885a676d92545fd91a9a20b48d234a2b2",
    LB/"livebench/if_runner/instruction_following_eval/instructions_registry.py":"903ed738398648c7cfac61d5ffa478c22f1f0891",
    LB/"livebench/process_results/instruction_following/utils.py":"8ce01747887ec0792c8f024e1972e34ece781676",
    GEN/"livebench/if_runner/live_data.py":"6ff390d6885cf90f88d9d36959735cb327613edc",
}

import hashlib
def blob(path:Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

for p,e in EXPECTED.items():
    g=blob(p)
    assert g==e,(str(p),g,e)

sentence_id="length_constraints:number_sentences"
end_id="startend:end_checker"
conflicts=registry.conflict_make(registry.INSTRUCTION_CONFLICTS)
assert end_id not in conflicts[sentence_id], conflicts[sentence_id]
assert sentence_id not in conflicts[end_id], conflicts[end_id]

gen=(GEN/"livebench/if_runner/live_data.py").read_text()
assert '"length_constraints:number_sentences"' in gen
assert '"startend:end_checker"' in gen
assert "np.random.randint(2, max_instructions+1" in gen
assert "np.random.choice(all_constraints, draw, replace=False)" in gen

s=instructions.NumberOfSentences(sentence_id)
s.build_description(num_sentences=1,relation="less than")
e=instructions.EndChecker(end_id)
e.build_description(end_phrase="Any other questions?")
assert s.get_instruction_args()=={"num_sentences":1,"relation":"less than"}
assert e.get_instruction_args()=={"end_phrase":"Any other questions?"}

# Exact frozen Punkt behavior: every non-empty response that can satisfy the
# selected end phrase has >=1 sentence, so it cannot satisfy "less than 1".
# Exercise adversarial prefixes including empty, punctuation, newlines, quotes,
# abbreviations, and arbitrary words. The logical implication is additionally
# source-audited below.
prefixes=[
    "","x","x ","x. ","P.S. ","\n\n","\"","alpha beta gamma ",
    "!!! ","... ","Section 1\n","* item\n",
]
phrase="Any other questions?"
for prefix in prefixes:
    value=prefix+phrase
    assert e.check_following(value) is True,(prefix,value)
    assert instructions_util.count_sentences(value)>=1,(prefix,value)
    assert s.check_following(value) is False,(prefix,value)

sent_src=inspect.getsource(instructions.NumberOfSentences.check_following)
end_src=inspect.getsource(instructions.EndChecker.check_following)
util_src=inspect.getsource(instructions_util.count_sentences)
assert "count_sentences(value)" in sent_src
assert "num_sentences < self._num_sentences_threshold" in sent_src
assert "value.endswith(self._end_phrase)" in end_src
assert "_get_sentence_tokenizer()" in util_src

score_process=(LB/"livebench/process_results/instruction_following/utils.py").read_text()
assert "avg_score = (score_1 + score_2) / 2" in score_process
max_case_score=(0.0 + 0.5)/2.0
comparator=0.6573775
assert max_case_score==0.25
assert max_case_score<comparator

receipt={
    "schema":"PROJECT_BRAIN_LIVEBENCH_GENERATOR_SUPPORT_UNIVERSAL_ROUTE_FALSIFICATION_PUBLIC_RUNNER_V1",
    "status":"INDEPENDENT_PUBLIC_SOURCE_FALSIFICATION_PASS",
    "counterexample_ids":[sentence_id,end_id],
    "conflict_compatible":True,
    "reachable_parameterization":{
        sentence_id:{"num_sentences":1,"relation":"less than"},
        end_id:{"end_phrase":phrase},
    },
    "joint_full_satisfaction":False,
    "maximum_case_score_under_frozen_rule":max_case_score,
    "opus55_comparator_floor":comparator,
    "below_comparator":True,
    "terminal_rows_read":0,
    "acceptance_credit":False,
}
Path("livebench_universal_route_falsification_receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print(json.dumps(receipt,sort_keys=True))
