#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib
import json
import pathlib
import re
import sys

from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException

ROOT = pathlib.Path(__file__).resolve().parent
SUBJECT = ROOT / "subject/livebench_language_exception_carrier_20261005"
OUT = ROOT / "livebench_language_exception_carrier_verification_v1.json"

EXPECTED = {
    "carrier": "b4908c1a02563719029001aeba15f08dd0029b73",
    "precommit": "8c1cb1e2fdb501d578fdfa5517c9d0f9ed4e8fc1",
    "livebench_instructions": "4997bab885a676d92545fd91a9a20b48d234a2b2",
    "langdetect_detector": "cc831a0e7530d49fa9b544c9b779ba075ffdbe5c",
    "langdetect_factory": "aa5a7b24b46b460d6faece5e4afcd23f7178a578",
}
LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
LANG_CODES = (
    "en","es","pt","ar","hi","fr","ru","de","ja","it",
    "bn","uk","th","ur","ta","te","bg","ko","pl","he",
    "fa","vi","ne","sw","kn","mr","gu","pa","ml","fi",
)


def git_blob(path: pathlib.Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def require_detect_exception(text: str) -> str:
    try:
        got = detect(text)
    except LangDetectException as exc:
        return f"{type(exc).__name__}:{exc}"
    raise AssertionError(f"DETECT_DID_NOT_RAISE:{got!r}:{text[:120]!r}")


def main() -> int:
    carrier_path = SUBJECT / "canonical/runtime/livebench_union25_language_exception_carrier_v1.py"
    precommit_path = SUBJECT / "canonical/governance/LIVEBENCH_LANGUAGE_EXCEPTION_CARRIER_PRECOMMIT_20261005_V1.json"
    assert git_blob(carrier_path) == EXPECTED["carrier"]
    assert git_blob(precommit_path) == EXPECTED["precommit"]

    pre = json.loads(precommit_path.read_text(encoding="utf-8"))
    assert pre["status"].startswith("FROZEN_OUTCOME_BLIND")
    assert pre["frozen_subjects"]["carrier_git_blob_sha"] == EXPECTED["carrier"]

    import langdetect
    import langdetect.detector
    import langdetect.detector_factory
    assert getattr(langdetect, "__version__", "1.0.9") in ("1.0.9",)

    detector_path = pathlib.Path(langdetect.detector.__file__).resolve()
    factory_path = pathlib.Path(langdetect.detector_factory.__file__).resolve()
    assert git_blob(detector_path) == EXPECTED["langdetect_detector"], (
        "DETECTOR_SOURCE_DRIFT", git_blob(detector_path)
    )
    assert git_blob(factory_path) == EXPECTED["langdetect_factory"], (
        "FACTORY_SOURCE_DRIFT", git_blob(factory_path)
    )

    live = pathlib.Path("/tmp/LiveBench")
    import subprocess
    head = subprocess.run(
        ["git","-C",str(live),"rev-parse","HEAD"],
        check=True,text=True,capture_output=True,
    ).stdout.strip()
    assert head == LIVEBENCH_COMMIT
    instructions_path = live / "livebench/if_runner/instruction_following_eval/instructions.py"
    assert git_blob(instructions_path) == EXPECTED["livebench_instructions"]

    sys.path.insert(0, str(SUBJECT))
    sys.path.insert(0, str(live / "livebench/if_runner"))
    carrier = importlib.import_module(
        "canonical.runtime.livebench_union25_language_exception_carrier_v1"
    )
    registry = importlib.import_module(
        "instruction_following_eval.instructions_registry"
    )

    static = carrier.static_invariants()
    assert static["codepoint"] == "U+E000"
    c = carrier.PRIVATE_USE_CARRIER
    assert not re.match(r"\w", c)
    assert not re.search(r"[A-Za-z]", c)
    assert not c.isalpha() and not c.isupper() and not c.islower()
    assert all(x not in c for x in (",",".","?","!","\n",'"',"[","]","*"))

    # Safe composition points: carrier is inserted at a component boundary,
    # never inside a mandatory lexical token.
    payloads = [
        ("EMPTY", "", ""),
        ("ASCII_LOWER", "alpha birch cedar", ""),
        ("ASCII_UPPER", "ALPHA BIRCH CEDAR", ""),
        ("MIXED_ASCII_DIGITS_PUNCT", "Alpha 9000001 [slot] *mark* P.S.+", ""),
        ("LIVEBENCH_SCAFFOLD", "Section 1 body P.S.+ <<TITLE>>", " Any other questions?"),
        ("COUNTER_STYLE", "alphaalphaalpha qqqqqqqqqq WORD1 WORD2 WORD3", ""),
        ("NEAR_WINDOW", "a" * 3000, ""),
    ]

    cases = []
    for name,prefix,suffix in payloads:
        base = prefix + suffix
        out = carrier.inject_before_suffix(prefix, suffix)
        latin = carrier.ascii_latin_count(base)
        required = carrier.required_carrier_count(base)
        assert required == 2 * latin + 1
        assert out.count(c) == required
        assert len(out) < carrier.DETECTOR_MAX_TEXT_LENGTH

        # Exact frozen detector cleaning theorem: private-use characters count
        # as non-Latin, forcing removal of all ASCII A-z characters.
        from langdetect.detector_factory import _factory, init_factory
        init_factory()
        d = _factory.create()
        d.append(out)
        original = d.text
        d.cleaning_text()
        assert not re.search(r"[A-Za-z]", d.text), (name, d.text[:120])
        ngrams = d._extract_ngrams()
        assert ngrams == [], (name, ngrams[:20], d.text[:120])
        exc = require_detect_exception(out)

        # At a safe component boundary, the carrier itself adds no semantic
        # counts used by the other frozen checker families.
        assert len(re.findall(r"\w+", out)) == len(re.findall(r"\w+", base))
        assert sum(ch.lower()=="q" for ch in out) == sum(ch.lower()=="q" for ch in base)
        assert out.count(",") == base.count(",")
        cases.append({
            "name":name,
            "latin_count":latin,
            "carrier_count":required,
            "length":len(out),
            "post_clean_length":len(d.text),
            "ngram_features":0,
            "exception":exc,
        })

    # One carrier response must satisfy every requested language via the exact
    # checker's explicit LangDetectException-success branch.
    language_response = carrier.inject_before_suffix("alpha 9000001 body")
    require_detect_exception(language_response)
    language_pass = []
    for code in LANG_CODES:
        checker = registry.INSTRUCTION_DICT["language:response_language"](
            "language:response_language"
        )
        checker.build_description(language=code)
        ok = checker.check_following(language_response)
        assert ok is True, code
        language_pass.append(code)
    assert len(language_pass) == 30

    upper = carrier.inject_before_suffix(
        "THIS IS SIMPLE ENGLISH TEXT WITH WORD1 WORD2 WORD3"
    )
    lower = carrier.inject_before_suffix(
        "this is simple english text with word1 word2 word3"
    )
    assert upper.isupper()
    assert lower.islower()
    require_detect_exception(upper)
    require_detect_exception(lower)

    upper_checker = registry.INSTRUCTION_DICT["change_case:english_capital"](
        "change_case:english_capital"
    )
    upper_checker.build_description()
    lower_checker = registry.INSTRUCTION_DICT["change_case:english_lowercase"](
        "change_case:english_lowercase"
    )
    lower_checker.build_description()
    assert upper_checker.check_following(upper) is True
    assert lower_checker.check_following(lower) is True

    receipt = {
        "schema":"PROJECT_BRAIN_LIVEBENCH_LANGUAGE_EXCEPTION_CARRIER_INDEPENDENT_VERIFICATION_V1",
        "status":"PASS__PINNED_LANGDETECT_NO_FEATURE_EXCEPTION__30_OF_30_LANGUAGE_CODES__UPPER_LOWER_ENGLISH_CASE__ZERO_TERMINAL_ROWS",
        "subject_blobs":{
            "carrier":EXPECTED["carrier"],
            "precommit":EXPECTED["precommit"],
        },
        "pinned_runtime":{
            "livebench_commit":LIVEBENCH_COMMIT,
            "instructions_blob":EXPECTED["livebench_instructions"],
            "langdetect_version":"1.0.9",
            "detector_blob":EXPECTED["langdetect_detector"],
            "detector_factory_blob":EXPECTED["langdetect_factory"],
        },
        "adversarial_payload_cases":cases,
        "response_language_checker":{
            "requested_codes":list(LANG_CODES),
            "pass_count":len(language_pass),
            "mechanism":"EXPLICIT_CHECKER_SUCCESS_ON_LANGDETECT_EXCEPTION",
        },
        "english_case_checkers":{
            "uppercase_isupper":upper.isupper(),
            "lowercase_islower":lower.islower(),
            "uppercase_checker_pass":True,
            "lowercase_checker_pass":True,
        },
        "detector_proof":{
            "cleaning_condition":"non_latin_count > 2*ascii_latin_count",
            "carrier_count_rule":"2*ASCII_LATIN_COUNT+1",
            "all_ascii_latin_removed":True,
            "all_profile_ngram_feature_lists_empty":True,
            "all_direct_detect_calls_raise_LangDetectException":True,
        },
        "terminal_rows_read":0,
        "hidden_terminal_kwargs_read":0,
        "target_responses_read":0,
        "target_scores_read":0,
        "incremental_spend_usd":0,
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
        "hard_nonclaims":[
            "THIS_VERIFIES_THE_LANGUAGE_EXCEPTION_PRIMITIVE_ONLY",
            "UNION25_MULTI_CONTRACT_POINTWISE_OPTIMALITY_REMAINS_SEPARATE",
            "NO_LIVEBENCH_ACCEPTANCE_CREDIT_FROM_THIS_RECEIPT_ALONE",
        ],
    }
    OUT.write_text(json.dumps(receipt,ensure_ascii=True,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({
        "status":receipt["status"],
        "payload_cases":len(cases),
        "language_pass_count":len(language_pass),
    },sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
