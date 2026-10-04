#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

EXPECTED_LOCAL={
 "canonical/runtime/livebench_pointwise_optimality_certificate_v1.py":"f0e1faae5b5d1a90a1184fe6cca409591acbbb27",
 "canonical/tests/test_livebench_pointwise_optimality_certificate_v1.py":"af762ebcdf9ed5a85db090f10de8216f23465410",
 "canonical/runtime/livebench_legacy15_slot_feasibility_v1.py":"a0885303a9c7088c4eb6f0510963069e35750f02",
 "canonical/tests/test_livebench_legacy15_slot_feasibility_v1.py":"bc6f165804415e7026431284b2a83cdb4dd19899",
 "canonical/runtime/livebench_legacy15_pointwise_certificate_v1.py":"b8f9d0c9a0b0c9f78769cb9534ee4e2c61481fd8",
 "canonical/tests/test_livebench_legacy15_pointwise_certificate_v1.py":"22e37b72287d9ec05562968ee3dd5a1aea98e2c6",
 "canonical/runtime/livebench_legacy15_composition_archetypes_v1.py":"0dbef76a6189a3cdc21ce3dae97ef6921e333b34",
}
EXPECTED_UPSTREAM={
 "livebench/if_runner/instruction_following_eval/instructions.py":"4997bab885a676d92545fd91a9a20b48d234a2b2",
 "livebench/if_runner/instruction_following_eval/instructions_util.py":"1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b",
 "livebench/if_runner/instruction_following_eval/instructions_registry.py":"903ed738398648c7cfac61d5ffa478c22f1f0891",
 "livebench/process_results/instruction_following/utils.py":"8ce01747887ec0792c8f024e1972e34ece781676",
}

def blob(path:Path)->str:
 d=path.read_bytes()
 return hashlib.sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--root",default=".")
 ap.add_argument("--livebench-root",required=True)
 ap.add_argument("--output",required=True)
 a=ap.parse_args()
 root=Path(a.root).resolve()
 lb=Path(a.livebench_root).resolve()
 for p,h in EXPECTED_LOCAL.items():
  got=blob(root/p); assert got==h,(p,got,h)
 for p,h in EXPECTED_UPSTREAM.items():
  got=blob(lb/p); assert got==h,(p,got,h)

 score_src=(lb/"livebench/process_results/instruction_following/utils.py").read_text()
 ins=(lb/"livebench/if_runner/instruction_following_eval/instructions.py").read_text()
 util=(lb/"livebench/if_runner/instruction_following_eval/instructions_util.py").read_text()

 # Exact frozen scoring law: (all-followed indicator + followed fraction)/2.
 assert "score_1 = 1 if follow_all_instructions else 0" in score_src
 assert "score_2 = sum(score_2) / len(score_2)" in score_src
 assert "avg_score = (score_1 + score_2) / 2" in score_src

 # Exact semantic premises used by the current conservative UNSAT kernel.
 assert 're.search(r"\\b" + word + r"\\b", value, flags=re.IGNORECASE)' in ins
 assert "paragraph = paragraphs[self._nth_paragraph - 1].strip()" in ins
 assert "word = paragraph.split()[0].strip()" in ins
 assert "and first_word == self._first_word" in ins
 assert "return value.endswith(self._end_phrase)" in ins
 assert "num_sentences = instructions_util.count_sentences(value)" in ins
 assert "return num_sentences < self._num_sentences_threshold" in ins
 assert "tokenized_sentences = tokenizer.tokenize(text)" in util
 assert "return len(tokenized_sentences)" in util

 # The retracted false section/forbidden class must remain absent.
 slot=(root/"canonical/runtime/livebench_legacy15_slot_feasibility_v1.py").read_text()
 bridge_tests=(root/"canonical/tests/test_livebench_legacy15_pointwise_certificate_v1.py").read_text()
 assert "MANDATORY_SECTION_SPLITTER_IS_FORBIDDEN_WORD" not in slot
 assert "test_section_forbidden_unsat" not in bridge_tests

 from canonical.runtime import livebench_legacy15_slot_feasibility_v1 as f
 from canonical.runtime.livebench_pointwise_optimality_certificate_v1 import frozen_bound
 from canonical.runtime.livebench_legacy15_pointwise_certificate_v1 import certify

 # Positive proofs.
 nth=[
  {"instruction_id":f.NTH,"slots":{"num_paragraphs":2,"nth_paragraph":1,"first_word":"alpha"}},
  {"instruction_id":f.FORBIDDEN,"slots":{"forbidden_words":["alpha"]}},
 ]
 assert f.hard_unsat_reasons(nth)==("NTH_FIRST_WORD_IS_FORBIDDEN_WORD",)
 end=[
  {"instruction_id":f.END,"slots":{"end_phrase":"Any other questions?"}},
  {"instruction_id":f.FORBIDDEN,"slots":{"forbidden_words":["questions"]}},
 ]
 assert any(x.startswith("MANDATORY_END_PHRASE_CONTAINS_FORBIDDEN_WORD:") for x in f.hard_unsat_reasons(end))
 sentence_end=[
  {"instruction_id":f.SENTENCE,"slots":{"num_sentences":1,"relation":"less than"}},
  {"instruction_id":f.END,"slots":{"end_phrase":"Any other questions?"}},
 ]
 assert "SENTENCE_LT_ONE_WITH_MANDATORY_END_PHRASE" in f.hard_unsat_reasons(sentence_end)

 # Explicit negative guards.
 overlap=[
  {"instruction_id":f.EXISTENCE,"slots":{"keywords":["rock"]}},
  {"instruction_id":f.FORBIDDEN,"slots":{"forbidden_words":["rock"]}},
 ]
 assert f.hard_unsat_reasons(overlap)==()
 section=[
  {"instruction_id":"detectable_format:multiple_sections","slots":{"section_spliter":"Section","num_sections":3}},
  {"instruction_id":f.FORBIDDEN,"slots":{"forbidden_words":["section"]}},
 ]
 assert f.hard_unsat_reasons(section)==()

 # Bridge proves pointwise optimality only when every required g+1 subset is proved UNSAT.
 assert certify(nth,[True,False])["pointwise_optimal"] is True
 unknown=[
  {"instruction_id":f.EXISTENCE,"slots":{"keywords":["river"]}},
  {"instruction_id":"detectable_format:title","slots":{}},
 ]
 assert certify(unknown,[True,False])["pointwise_optimal"] is False
 bound=frozen_bound()
 assert bound["max_checkers_per_case"]==5
 assert bound["max_required_unsat_subsets"]==10

 receipt={
  "schema":"PROJECT_BRAIN_LIVEBENCH_POINTWISE_CORE_INDEPENDENT_FASTLANE_V1",
  "status":"PASS__STRUCTURAL_POINTWISE_THEOREM_AND_CURRENT_THREE_CLASS_SEMANTIC_BRIDGE",
  "exact_local_blobs":EXPECTED_LOCAL,
  "exact_upstream_blobs":EXPECTED_UPSTREAM,
  "verified_semantic_unsat_classes":[
   "NTH_PARAGRAPH_FIRST_WORD_EQUALS_A_FORBIDDEN_WORD",
   "MANDATORY_END_PHRASE_CONTAINS_A_GENERATED_LITERAL_FORBIDDEN_WORD",
   "NUMBER_SENTENCES_LESS_THAN_ONE_WITH_PUBLIC_MANDATORY_END_PHRASE",
  ],
  "explicitly_rejected_classes":[
   "REQUIRED_KEYWORD_EQUALS_FORBIDDEN_WORD",
   "SECTION_SPLITTER_EQUALS_FORBIDDEN_WORD",
  ],
  "max_required_next_cardinality_unsat_certificates":10,
  "terminal_rows_read":0,
  "terminal_case_frequencies_read":0,
  "acceptance_credit":False,
  "hard_nonclaim":"DOES_NOT_PROVE_THE_THREE_CLASSES_ARE_COMPLETE_FOR_ALL_NONFULL_CASES",
 }
 Path(a.output).write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
 print(json.dumps(receipt,sort_keys=True))

if __name__=="__main__":
 main()
