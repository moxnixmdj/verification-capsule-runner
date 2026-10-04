#!/usr/bin/env python3
from __future__ import annotations
import ast, hashlib, importlib.util, json, pathlib, subprocess, sys

LIVEBENCH_COMMIT="8f8e5c381a16e3f24257776edd53471fe86f8091"
CARRIER_BLOB="b4908c1a02563719029001aeba15f08dd0029b73"
SAMPLES_BLOB="e927c05071bb4342b41fb9d5be07cc32ea82e820"

ROOT=pathlib.Path(__file__).resolve().parent
CARRIER_PATH=ROOT/"subject/livebench_union25_language_exception_carrier_v1.py"
SAMPLES_PATH=ROOT/"subject/livebench_legacy25_single_contract_witness_v1.py"

def blob(p):
    raw=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def load_module(name,p):
    spec=importlib.util.spec_from_file_location(name,p)
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def extract_samples():
    tree=ast.parse(SAMPLES_PATH.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target,ast.Name) and target.id=="LANGUAGE_SAMPLES":
                    return ast.literal_eval(node.value)
    raise AssertionError("LANGUAGE_SAMPLES_NOT_FOUND")

def main():
    assert blob(CARRIER_PATH)==CARRIER_BLOB
    assert blob(SAMPLES_PATH)==SAMPLES_BLOB
    live=pathlib.Path("/tmp/LiveBench")
    head=subprocess.run(["git","-C",str(live),"rev-parse","HEAD"],check=True,text=True,capture_output=True).stdout.strip()
    assert head==LIVEBENCH_COMMIT

    sys.path.insert(0,str(live/"livebench/if_runner"))
    import langdetect
    from langdetect.lang_detect_exception import LangDetectException
    from instruction_following_eval import instructions_registry

    assert getattr(langdetect,"__version__",None) in (None,"1.0.9")
    carrier=load_module("carrier",CARRIER_PATH)
    samples=extract_samples()
    assert len(samples)==30
    assert carrier.static_invariants()["codepoint"]=="U+E000"

    tested=0
    exceptions=0
    failures=[]

    def expect_exception(text,label):
        nonlocal tested,exceptions
        tested+=1
        try:
            got=langdetect.detect(text)
            failures.append({"label":label,"kind":"DETECTED_INSTEAD_OF_EXCEPTION","got":got,"len":len(text)})
            return False
        except LangDetectException:
            exceptions+=1
            return True

    # Exact algebraic carrier behavior on the entire small payload range plus
    # critical near-window boundaries. This directly falsifies off-by-one and
    # cleaning-threshold mistakes.
    ns=list(range(0,513))+[777,1000,1500,2000,2500,3000,3200,3300,3330,3331,3332]
    for n in ns:
        base="a"*n
        out=carrier.inject_before_suffix(base)
        assert out.count(carrier.PRIVATE_USE_CARRIER)==2*n+1
        assert len(out)==3*n+1
        if len(out)>=carrier.DETECTOR_MAX_TEXT_LENGTH:
            failures.append({"label":f"BOUND_{n}","kind":"UNEXPECTED_WINDOW_OVERFLOW","len":len(out)})
            continue
        expect_exception(out,f"ASCII_{n}")

    # Exact 30-language public domain. The proof target is stronger than
    # language preservation: the pinned checker must accept the same carrier
    # response for every requested code via its explicit exception branch.
    language_checker_pass=0
    for code,sample in sorted(samples.items()):
        variants={
            "base":sample+" "+sample,
            "decorated_prefix":"[] *-* "+sample+" "+sample,
            "decorated_suffix":sample+" "+sample+" [] *-*",
            "upper_ascii":"ALPHA "+sample+" OMEGA",
            "lower_ascii":"alpha "+sample+" omega",
        }
        for vname,base in variants.items():
            out=carrier.inject_before_suffix(base)
            expect_exception(out,f"LANG_{code}_{vname}")
            checker=instructions_registry.INSTRUCTION_DICT["language:response_language"]("language:response_language")
            checker.build_description(language=code)
            if checker.check_following(out):
                language_checker_pass+=1
            else:
                failures.append({"label":f"LANG_CHECKER_{code}_{vname}","kind":"CHECKER_FALSE"})

    # English-case checkers must still have true Python case predicates before
    # the detector is reached; U+E000 itself must be case-neutral.
    case_pass=0
    for fam,base in [
        ("change_case:english_capital","THIS IS A SIMPLE ENGLISH RESPONSE"),
        ("change_case:english_lowercase","this is a simple english response"),
    ]:
        out=carrier.inject_before_suffix(base)
        assert (out.isupper() if fam.endswith("english_capital") else out.islower())
        checker=instructions_registry.INSTRUCTION_DICT[fam](fam)
        checker.build_description()
        if checker.check_following(out):
            case_pass+=1
        else:
            failures.append({"label":fam,"kind":"CASE_CHECKER_FALSE"})

    # Candidate must fail closed exactly at the declared detector window.
    try:
        carrier.inject_before_suffix("a"*3333)
        failures.append({"label":"WINDOW_FAIL_CLOSED","kind":"EXPECTED_VALUE_ERROR_MISSING"})
    except ValueError as e:
        assert str(e)=="LANGUAGE_CARRIER_EXCEEDS_PINNED_DETECTOR_WINDOW"

    receipt={
        "schema":"PROJECT_BRAIN_LIVEBENCH_LANGUAGE_EXCEPTION_CARRIER_INDEPENDENT_VERIFICATION_V1",
        "status":"FAIL" if failures else "PASS__EXACT_LANGDETECT_EXCEPTION_CARRIER__30_OF_30_LANGUAGE_CODES__CASE_CHECKERS_PASS__ZERO_TERMINAL_ROWS",
        "pinned_livebench_commit":LIVEBENCH_COMMIT,
        "langdetect_version":"1.0.9",
        "carrier_blob":CARRIER_BLOB,
        "sample_bank_blob":SAMPLES_BLOB,
        "payload_sizes_tested":len(ns),
        "langdetect_calls":tested,
        "langdetect_exception_calls":exceptions,
        "language_checker_cases":30*5,
        "language_checker_pass":language_checker_pass,
        "english_case_checker_pass":case_pass,
        "max_supported_ascii_latin_payload_for_formula":3332,
        "terminal_rows_read":0,
        "hidden_kwargs_read":0,
        "target_responses_read":0,
        "target_scores_read":0,
        "acceptance_credit_delta":0,
        "failure_count":len(failures),
        "failures":failures[:100],
        "hard_nonclaims":[
            "THIS_VERIFIES_THE_PINNED_SCORER_SEMANTICS_ONLY",
            "IT_DOES_NOT_BY_ITSELF_PROVE_FULL_UNION25_MULTI_CONTRACT_COMPOSITION",
            "NO_SEMANTIC_LANGUAGE_CAPABILITY_CREDIT_IS_GRANTED_FROM_AN_EXCEPTION_PATH"
        ]
    }
    pathlib.Path("livebench_language_exception_carrier_v1.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(receipt,sort_keys=True))
    return 1 if failures else 0

if __name__=="__main__":
    raise SystemExit(main())
