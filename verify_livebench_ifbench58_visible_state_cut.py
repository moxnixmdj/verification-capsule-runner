#!/usr/bin/env python3
import hashlib, json, re, sys
from pathlib import Path

EXPECTED={
 "instructions.py":"02b2dfeb50f036b89bec3df34522c73f756d8f44",
 "instructions_registry.py":"adfed4832877566e62970257b50c6fa32c302fb2",
}

def git_blob(data):
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

root=Path(sys.argv[1])
ins_path=root/"livebench/if_runner/ifbench/instructions.py"
reg_path=root/"livebench/if_runner/ifbench/instructions_registry.py"
src_b=ins_path.read_bytes()
reg_b=reg_path.read_bytes()
assert git_blob(src_b)==EXPECTED["instructions.py"]
assert git_blob(reg_b)==EXPECTED["instructions_registry.py"]
src=src_b.decode("utf-8")
reg=reg_b.decode("utf-8")
maps=re.findall(r'["\']([^"\']+)["\']\s*:\s*instructions\.([A-Za-z0-9_]+)',reg)
assert len(maps)==58

def block(cls):
    m=re.search(rf'^class {re.escape(cls)}\(Instruction\):.*?(?=^class |\Z)',src,re.M|re.S)
    assert m, cls
    return m.group(0)

rows=[]
for iid,cls in maps:
    b=block(cls)
    km=re.search(r'def get_instruction_args_keys\(self\):(.*?)(?=\n\tdef |\n    def |\Z)',b,re.S)
    keys=[]
    if km:
        lm=re.search(r'return\s+\[([^\]]*)\]',km.group(1),re.S)
        if lm:
            keys=re.findall(r'["\']([^"\']+)["\']',lm.group(1))
    bm=re.search(r'def build_description\([^)]*\):(.*?)(?=\n\tdef |\n    def |\Z)',b,re.S)
    build=bm.group(1) if bm else ""
    placeholders=sorted(set(re.findall(r'\{([A-Za-z0-9_]+)\}',build)))
    hidden=[k for k in keys if k not in placeholders]
    rows.append({"instruction_id":iid,"class":cls,"keys":keys,"visible_placeholders":placeholders,"hidden_keys":hidden})

zero=sum(not r["keys"] for r in rows)
param=sum(bool(r["keys"]) for r in rows)
fully=sum(bool(r["keys"]) and not r["hidden_keys"] for r in rows)
hidden=[r for r in rows if r["hidden_keys"]]
assert (zero,param,fully)==(39,19,17),(zero,param,fully)
assert [(r["instruction_id"],r["hidden_keys"]) for r in hidden]==[
    ("ratio:overlap",["reference_text"]),
    ("repeat:repeat_span",["prompt_to_repeat"]),
], hidden

ng=block("NGramOverlapChecker")
rs=block("RepeatSpanChecker")
assert "nltk.ngrams(value, n)" in ng
assert "nltk.ngrams(self._reference_text, n)" in ng
assert "indices are character indices!" in rs
assert "self._prompt_to_repeat.strip().lower().split()[self._n_start:self._n_end]" in rs

receipt={
 "schema":"LIVEBENCH_IFBENCH58_VISIBLE_STATE_STATIC_CUT_INDEPENDENT_VERIFIER_V1",
 "status":"PASS",
 "pinned_livebench_commit":"8f8e5c381a16e3f24257776edd53471fe86f8091",
 "blob_sha":EXPECTED,
 "registered_families":len(rows),
 "zero_argument_families":zero,
 "parameterized_families":param,
 "fully_description_visible_parameterized_families":fully,
 "hidden_state_residuals":hidden,
 "scorer_drift_checks":{
   "ratio_overlap_character_ngram":True,
   "repeat_span_character_word_mismatch":True
 },
 "terminal_rows_read":0
}
Path("livebench_ifbench58_visible_state_cut_receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(receipt,sort_keys=True))
