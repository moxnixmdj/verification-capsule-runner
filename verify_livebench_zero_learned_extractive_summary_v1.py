from __future__ import annotations
import ast
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SUBJECT=ROOT/"subject"
EXPECTED={
    "canonical/governance/LIVEBENCH_ZERO_LEARNED_EXTRACTIVE_SUMMARY_PREEXPOSURE_V1.json":"abab3af85d5074d498ae2cd5b71f1085066f3cea",
    "canonical/tests/test_zero_learned_extractive_summary_v1.py":"c27922e9119377ce424cc62164bea437853fbe91",
    "canonical/runtime/zero_learned_extractive_summary_v1.py":"6d02d938a21da2a015b138478cfdadc26d059b22",
    "canonical/governance/LIVEBENCH_ZERO_LEARNED_EXTRACTIVE_SUMMARY_CANDIDATE_V1.json":"3aa43e99bf6a6f26b0252e700562497639432a65",
}
ALLOWED_IMPORT_ROOTS={"__future__","math","re","collections","typing"}


def git_blob_sha(path:Path)->str:
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()


def assert_exact_subject()->dict:
    observed={}
    for rel,expected in EXPECTED.items():
        actual=git_blob_sha(SUBJECT/rel)
        if actual!=expected:
            raise AssertionError(f"BLOB_MISMATCH:{rel}:{actual}:{expected}")
        observed[rel]=actual
    return observed


def assert_runtime_surface()->list[str]:
    runtime=SUBJECT/"canonical/runtime/zero_learned_extractive_summary_v1.py"
    tree=ast.parse(runtime.read_text(encoding="utf-8"))
    roots=set()
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):
            roots.update(alias.name.split(".",1)[0] for alias in node.names)
        elif isinstance(node,ast.ImportFrom) and node.module:
            roots.add(node.module.split(".",1)[0])
    unexpected=roots-ALLOWED_IMPORT_ROOTS
    if unexpected:
        raise AssertionError("UNEXPECTED_IMPORTS:"+repr(sorted(unexpected)))
    return sorted(roots)


def fresh_challenges()->list[dict]:
    sys.path.insert(0,str(SUBJECT))
    from canonical.runtime.zero_learned_extractive_summary_v1 import summarize

    cases=[
        {
            "id":"ENERGY_THEME_WITH_DISTRACTOR",
            "text":"Alpha systems store energy. Energy storage helps balance demand. Decorative paint changes appearance. Stored energy can be released later.",
            "max_sentences":2,
            "forbidden":"Decorative paint changes appearance.",
            "required_token":"energy",
        },
        {
            "id":"ENZYME_THEME_WITH_DISTRACTOR",
            "text":"Enzymes accelerate chemical reactions. Enzyme activity depends on molecular structure. The laboratory door is painted green. Temperature can change enzyme activity.",
            "max_sentences":2,
            "forbidden":"The laboratory door is painted green.",
            "required_token":"enzyme",
        },
        {
            "id":"ORBITAL_THEME_WITH_DISTRACTOR",
            "text":"Orbital energy changes when a spacecraft performs a burn. A prograde burn can increase orbital energy. The mission patch contains a triangle. Drag can slowly remove orbital energy.",
            "max_sentences":2,
            "forbidden":"The mission patch contains a triangle.",
            "required_token":"orbital",
        },
    ]
    rows=[]
    for case in cases:
        out=summarize(case["text"],max_sentences=case["max_sentences"])
        assert out["status"]=="SUMMARY_READY", (case["id"],out)
        assert out["extractive_faithfulness_verified"] is True
        assert out["persistent_learned_bytes"]==0
        assert out["external_model_calls"]==0
        assert out["network_calls"]==0
        assert case["forbidden"] not in out["summary"]
        assert all(sentence in case["text"] for sentence in out["summary_sentences"])
        assert all(case["required_token"] in sentence.lower() for sentence in out["summary_sentences"])
        rows.append({"id":case["id"],"summary":out["summary"],"selected_indices":out["selected_indices"]})

    numeric="The reactor produced 12 megawatts during trial one. Trial two produced 12 megawatts after tuning. The control room has 7 chairs. Repeated 12 megawatt output was the central result."
    out=summarize(numeric,max_sentences=2)
    source_nums=set(re.findall(r"\b\d+(?:\.\d+)?\b",numeric))
    summary_nums=set(re.findall(r"\b\d+(?:\.\d+)?\b",out["summary"]))
    assert summary_nums <= source_nums
    assert "7 chairs" not in out["summary"]
    rows.append({"id":"NUMERIC_NO_INVENTION","summary":out["summary"],"numeric_subset":sorted(summary_nums)})

    abstain=summarize("One source sentence only.",max_sentences=2)
    assert abstain["status"]=="ABSTAIN_NOT_COMPRESSIBLE"
    assert abstain["summary"]==""
    rows.append({"id":"NOT_COMPRESSIBLE_ABSTENTION","status":abstain["status"]})
    return rows


def main()->None:
    exact=assert_exact_subject()
    imports=assert_runtime_surface()
    challenges=fresh_challenges()
    result={
        "schema":"PROJECT_BRAIN_LIVEBENCH_ZERO_LEARNED_EXTRACTIVE_SUMMARY_INDEPENDENT_VERIFICATION_V1",
        "status":"PASS",
        "exact_subject_blobs":exact,
        "runtime_import_roots":imports,
        "copied_subject_tests":"RUN_BY_WORKFLOW",
        "fresh_challenges":challenges,
        "fresh_challenge_count":len(challenges),
        "persistent_learned_bytes":0,
        "external_model_calls":0,
        "runtime_network_calls":0,
        "terminal_cases_consumed":0,
        "hard_nonclaims":[
            "NO_ABSTRACTIVE_SUMMARIZATION_CLAIM",
            "NO_SUMMARY_COMPLETENESS_CLAIM",
            "NO_PARAPHRASE_SIMPLIFICATION_OR_STORY_GENERATION_CLAIM",
            "NO_LIVEBENCH_TERMINAL_SCORE_CREDIT"
        ],
    }
    (ROOT/"verification_result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2,sort_keys=True))


if __name__=="__main__":
    main()
