#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
from collections import Counter

SUBJECT_ROOT = pathlib.Path("subject/livebench_composer_v2_20261005").resolve()
RUNTIME = SUBJECT_ROOT / "canonical/runtime"
LIVE = pathlib.Path("/tmp/LiveBench").resolve()

EXPECTED = {
    "numeric": "72189bb8adb12ad36a52ee666a1f79fbb201b06b",
    "arch": "0dbef76a6189a3cdc21ce3dae97ef6921e333b34",
    "composer": "d73ec366b32252996258eae6d10d67d4d6a5e042",
    "feasibility": "7477f5ea5bdeac3595ee2784a38d078fe2f385b0",
    "livebench_commit": "8f8e5c381a16e3f24257776edd53471fe86f8091",
    "instructions_blob": "4997bab885a676d92545fd91a9a20b48d234a2b2",
    "registry_blob": "903ed738398648c7cfac61d5ffa478c22f1f0891",
    "util_blob": "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b",
}

def run(cmd):
    return subprocess.run(cmd, check=True, text=True, capture_output=True).stdout.strip()

def blob(path: pathlib.Path) -> str:
    return run(["git", "hash-object", str(path)])

def contract(iid, **slots):
    return {"instruction_id": iid, "slots": slots}

def replace_contract(rows, iid, **slots):
    out=[]
    for row in rows:
        if row["instruction_id"] == iid:
            out.append(contract(iid, **slots))
        else:
            out.append(dict(row))
    return out

def main() -> int:
    files = {
        "numeric": RUNTIME / "livebench_legacy15_numeric_quotient_v1.py",
        "arch": RUNTIME / "livebench_legacy15_composition_archetypes_v1.py",
        "composer": RUNTIME / "livebench_legacy15_contract_composer_v2.py",
        "feasibility": RUNTIME / "livebench_legacy15_slot_feasibility_v1.py",
    }
    for key, path in files.items():
        got = blob(path)
        assert got == EXPECTED[key], (key, got, EXPECTED[key])

    assert run(["git", "-C", str(LIVE), "rev-parse", "HEAD"]) == EXPECTED["livebench_commit"]
    live_paths = {
        "livebench/if_runner/instruction_following_eval/instructions.py": EXPECTED["instructions_blob"],
        "livebench/if_runner/instruction_following_eval/instructions_registry.py": EXPECTED["registry_blob"],
        "livebench/if_runner/instruction_following_eval/instructions_util.py": EXPECTED["util_blob"],
    }
    for rel, expected in live_paths.items():
        got = run(["git", "-C", str(LIVE), "rev-parse", "HEAD:" + rel])
        assert got == expected, (rel, got, expected)

    instructions_source = (LIVE / "livebench/if_runner/instruction_following_eval/instructions.py").read_text()
    source_constants = {
        "_NUM_WORDS_LOWER_LIMIT": 100,
        "_NUM_WORDS_UPPER_LIMIT": 500,
        "_MAX_NUM_SENTENCES": 20,
        "_NUM_PARAGRAPHS": 5,
        "_NUM_BULLETS": 5,
        "_NUM_SECTIONS": 5,
    }
    for name, value in source_constants.items():
        assert re.search(rf"^{re.escape(name)}\s*=\s*{value}\s*$", instructions_source, re.M), name

    sys.path.insert(0, str(SUBJECT_ROOT))
    sys.path.insert(0, str(LIVE / "livebench/if_runner"))
    from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as arch
    from canonical.runtime import livebench_legacy15_contract_composer_v2 as comp
    from canonical.runtime import livebench_legacy15_numeric_quotient_v1 as q
    from instruction_following_eval import instructions_registry

    result = q.verify()
    assert result["status"] == "PASS__PARAMETRIC_NUMERIC_REDUCTION"
    assert q.WORD_MIN == 100 and q.WORD_MAX == 500
    assert q.SENT_MIN == 1 and q.SENT_MAX == 20
    assert q.ANALYTIC_WORD_CEILING == 48

    all_sets = arch.enumerate_compatible_sets()
    assert len(all_sets) == 928

    def independent_max_profile(ids):
        rows=[]
        for iid in ids:
            if iid==comp.EXIST: rows.append(contract(iid,keywords=["harbor","violet","canyon","meadow","signal"]))
            elif iid==comp.FORBIDDEN: rows.append(contract(iid,forbidden_words=["amber","forest","silver","planet","window"]))
            elif iid==comp.PARAGRAPHS: rows.append(contract(iid,num_paragraphs=5))
            elif iid==comp.WORDS: rows.append(contract(iid,num_words=100,relation="less than"))
            elif iid==comp.SENTENCES: rows.append(contract(iid,num_sentences=20,relation="at least"))
            elif iid==comp.NTH: rows.append(contract(iid,num_paragraphs=5,nth_paragraph=5,first_word="harbor"))
            elif iid==comp.POSTSCRIPT: rows.append(contract(iid,postscript_marker="P.P.S"))
            elif iid==comp.BULLETS: rows.append(contract(iid,num_bullets=5))
            elif iid==comp.TITLE: rows.append(contract(iid))
            elif iid==comp.SECTIONS: rows.append(contract(iid,section_spliter="SECTION",num_sections=5))
            elif iid==comp.JSON_ID: rows.append(contract(iid))
            elif iid==comp.REPEAT: rows.append(contract(iid,prompt_to_repeat="Public request"))
            elif iid==comp.TWO: rows.append(contract(iid))
            elif iid==comp.END: rows.append(contract(iid,end_phrase="Is there anything else I can help with?"))
            elif iid==comp.QUOTE: rows.append(contract(iid))
            else: raise AssertionError(iid)
        return rows

    counts=Counter()
    max_word_count=-1
    maximizers=[]
    for ids in all_sets:
        if comp.WORDS not in ids:
            continue
        counts["word_structural_sets"] += 1
        base=independent_max_profile(ids)
        less=comp.compose_contracts(base)
        assert less["status"]=="CANDIDATE_WITNESS", (ids,less)
        w=int(less["word_count"])
        if w>max_word_count:
            max_word_count=w; maximizers=[list(ids)]
        elif w==max_word_count:
            maximizers.append(list(ids))
        assert w < 100, (ids,w)

        # Exhaust the public lower-bound threshold domain on the same worst-token
        # structural profile. Padding tokens are punctuation-free one-word atoms,
        # so increasing n cannot hurt any structural delimiter.
        for n in range(100,501):
            rows=replace_contract(base, comp.WORDS, num_words=n, relation="at least")
            out=comp.compose_contracts(rows)
            assert out["status"]=="CANDIDATE_WITNESS", (ids,n,out)
            assert int(out["word_count"]) >= n, (ids,n,out["word_count"])
            counts["word_atleast_threshold_cases"] += 1

    assert max_word_count == 48, max_word_count
    assert 100-max_word_count == 52

    sentence_cls = instructions_registry.INSTRUCTION_DICT[comp.SENTENCES]
    sentence_sets=[ids for ids in all_sets if comp.SENTENCES in ids]
    counts["sentence_structural_sets"]=len(sentence_sets)

    def exact_sentence_ok(response, n, relation):
        chk=sentence_cls(comp.SENTENCES)
        chk.build_description(num_sentences=n, relation=relation)
        return bool(response.strip()) and bool(chk.check_following(response))

    for ids in sentence_sets:
        base=independent_max_profile(ids)

        # The strongest satisfiable upper-bound member is <2. Larger thresholds
        # accept the same one-sentence-or-less construction if <2 does.
        for marker in (["P.S.","P.P.S"] if comp.POSTSCRIPT in ids else [None]):
            for phrase in ([
                "Any other questions?",
                "Is there anything else I can help with?",
            ] if comp.END in ids else [None]):
                rows=base
                if marker is not None:
                    rows=replace_contract(rows, comp.POSTSCRIPT, postscript_marker=marker)
                if phrase is not None:
                    rows=replace_contract(rows, comp.END, end_phrase=phrase)

                upper=replace_contract(rows, comp.SENTENCES, num_sentences=2, relation="less than")
                out=comp.compose_contracts(upper)
                assert out["status"]=="CANDIDATE_WITNESS", (ids,marker,phrase,out)
                assert exact_sentence_ok(out["response"],2,"less than"), (ids,marker,phrase,out["response"])
                counts["sentence_lt2_semantic_skeleton_cases"] += 1

                for n in range(1,21):
                    lower=replace_contract(rows, comp.SENTENCES, num_sentences=n, relation="at least")
                    lo=comp.compose_contracts(lower)
                    assert lo["status"]=="CANDIDATE_WITNESS", (ids,n,marker,phrase,lo)
                    assert exact_sentence_ok(lo["response"],n,"at least"), (ids,n,marker,phrase,lo["response"])
                    counts["sentence_atleast_threshold_cases"] += 1

        zero=replace_contract(base, comp.SENTENCES, num_sentences=1, relation="less than")
        z=comp.compose_contracts(zero)
        assert z["status"]=="PROVED_UNSAT", (ids,z)
        assert "STRICT_NONEMPTY_RESPONSE_IMPLIES_AT_LEAST_ONE_PUNKT_SENTENCE" in z["hard_unsat_reasons"]
        counts["sentence_lt1_unsat_structural_cases"] += 1

    receipt={
        "schema":"LIVEBENCH_NUMERIC_QUOTIENT_V1_INDEPENDENT_VERIFICATION",
        "status":"PASS__INDEPENDENT_PARAMETRIC_NUMERIC_QUOTIENT__EXACT_PINNED_SENTENCE_CHECKER",
        "subject_blobs":{k:EXPECTED[k] for k in ("numeric","arch","composer","feasibility")},
        "pinned_livebench":{
            "commit":EXPECTED["livebench_commit"],
            "instructions_blob":EXPECTED["instructions_blob"],
            "registry_blob":EXPECTED["registry_blob"],
            "util_blob":EXPECTED["util_blob"],
        },
        "word_theorem":{
            "maximum_unpadded_public_constructor_word_count":max_word_count,
            "minimum_public_less_than_threshold":100,
            "safety_margin":52,
            "maximizer_count":len(maximizers),
        },
        "sentence_partition":{
            "less_than_1":"PROVED_UNSAT",
            "less_than_2_to_20":"REDUCED_TO_EXACT_LT2_SEMANTIC_SKELETON",
            "at_least_1_to_20":"EXHAUSTED_ALL_PUBLIC_THRESHOLDS_ON_EVERY_COMPATIBLE_STRUCTURAL_SET_WITH_POSTSCRIPT_END_VARIANTS",
        },
        "coverage":dict(counts),
        "terminal_rows_read":0,
        "hidden_terminal_kwargs_read":0,
        "target_scores_read":0,
        "acceptance_credit_delta":0,
        "hard_nonclaims":[
            "THIS_RECEIPT_DOES_NOT_BY_ITSELF_PROVE_THE_FULL_POST_SACRIFICE_COMPOSER_THEOREM",
            "NO_LIVEBENCH_ACCEPTANCE_OR_FAMILY_CREDIT_FROM_THIS_RECEIPT_ALONE",
        ],
    }
    pathlib.Path("livebench_numeric_quotient_v1_verification.json").write_text(
        json.dumps(receipt,indent=2,sort_keys=True)+"\n"
    )
    print(json.dumps(receipt,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
