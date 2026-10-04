#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import re
from pathlib import Path

import langdetect
from langdetect import DetectorFactory
from langdetect import detector_factory
from langdetect.utils.unicode_block import unicode_block

OUT = Path("livebench_lang_decorator_gate_v1_receipt.json")

EXPECTED_LANGDETECT_VERSION = "1.0.9"
EXPECTED_LANGDETECT_RELEASE_COMMIT = "a1598f1afcbfe9a758cfd06bd688fbc5780177b2"
EXPECTED_LANGDETECT_BLOBS = {
    "detector.py": "cc831a0e7530d49fa9b544c9b779ba075ffdbe5c",
    "ngram.py": "ee82e38f73aadbf118ec03a6342c328d808539d2",
}
FROZEN_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
FROZEN_LIVEBENCH_INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
FROZEN_LIVEBENCH_UTIL_BLOB = "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b"
BRAIN_LANGUAGE_WITNESS_BLOB = "3ddec73fa9b8439e0460d786c38044e6cb7b2ef6"
BRAIN_SEMANTIC_REDUCTION_BLOB = "c08812986e1224bcbb910dfff3bc112f57453996"

LANGUAGE_SEEDS = {
    "en": "this is a simple english sentence about people work places and everyday life",
    "es": "esta es una frase sencilla en español sobre personas trabajo lugares y la vida cotidiana",
    "pt": "esta é uma frase simples em português sobre pessoas trabalho lugares e a vida cotidiana",
    "ar": "هذه جملة عربية بسيطة عن الناس والعمل والأماكن والحياة اليومية",
    "hi": "यह लोगों काम स्थानों और दैनिक जीवन के बारे में एक सरल हिंदी वाक्य है",
    "fr": "ceci est une phrase française simple sur les gens le travail les lieux et la vie quotidienne",
    "ru": "это простое русское предложение о людях работе местах и повседневной жизни",
    "de": "dies ist ein einfacher deutscher satz über menschen arbeit orte und das tägliche leben",
    "ja": "これは人々と仕事と場所と日常生活についての簡単な日本語の文章です",
    "it": "questa è una semplice frase italiana sulle persone il lavoro i luoghi e la vita quotidiana",
    "bn": "এটি মানুষ কাজ স্থান এবং দৈনন্দিন জীবন সম্পর্কে একটি সহজ বাংলা বাক্য",
    "uk": "це просте українське речення про людей роботу місця і повсякденне життя",
    "th": "นี่คือประโยคภาษาไทยง่ายๆ เกี่ยวกับผู้คน งาน สถานที่ และชีวิตประจำวัน",
    "ur": "یہ لوگوں کام جگہوں اور روزمرہ زندگی کے بارے میں ایک سادہ اردو جملہ ہے",
    "ta": "இது மக்கள் வேலை இடங்கள் மற்றும் அன்றாட வாழ்க்கையைப் பற்றிய எளிய தமிழ் வாக்கியம்",
    "te": "ఇది ప్రజలు పని ప్రదేశాలు మరియు దైనందిన జీవితం గురించి సరళమైన తెలుగు వాక్యం",
    "bg": "това е просто българско изречение за хората работата местата и ежедневието",
    "ko": "이것은 사람들 일 장소 그리고 일상생활에 관한 간단한 한국어 문장입니다",
    "pl": "to jest proste polskie zdanie o ludziach pracy miejscach i codziennym życiu",
    "he": "זה משפט פשוט בעברית על אנשים עבודה מקומות וחיי היומיום",
    "fa": "این یک جمله ساده فارسی درباره مردم کار مکان‌ها و زندگی روزمره است",
    "vi": "đây là một câu tiếng việt đơn giản về con người công việc địa điểm và cuộc sống hằng ngày",
    "ne": "यो मानिसहरू काम स्थानहरू र दैनिक जीवनको बारेमा सरल नेपाली वाक्य हो",
    "sw": "hii ni sentensi rahisi ya kiswahili kuhusu watu kazi maeneo na maisha ya kila siku",
    "kn": "ಇದು ಜನರು ಕೆಲಸ ಸ್ಥಳಗಳು ಮತ್ತು ದೈನಂದಿನ ಜೀವನದ ಬಗ್ಗೆ ಸರಳ ಕನ್ನಡ ವಾಕ್ಯ",
    "mr": "हे लोक काम ठिकाणे आणि दैनंदिन जीवनाबद्दलचे एक साधे मराठी वाक्य आहे",
    "gu": "આ લોકો કામ સ્થળો અને દૈનિક જીવન વિશેનું એક સરળ ગુજરાતી વાક્ય છે",
    "pa": "ਇਹ ਲੋਕਾਂ ਕੰਮ ਥਾਵਾਂ ਅਤੇ ਰੋਜ਼ਾਨਾ ਜੀਵਨ ਬਾਰੇ ਇੱਕ ਸਧਾਰਨ ਪੰਜਾਬੀ ਵਾਕ ਹੈ",
    "ml": "ഇത് ആളുകൾ ജോലി സ്ഥലങ്ങൾ ദൈനംദിന ജീവിതം എന്നിവയെ കുറിച്ചുള്ള ലളിതമായ മലയാള വാക്യമാണ്",
    "fi": "tämä on yksinkertainen suomenkielinen lause ihmisistä työstä paikoista ja arkielämästä",
}

PLACEHOLDER = "[]"
HIGHLIGHT = "*-*"
MAX_PLACEHOLDERS = 4
MAX_HIGHLIGHTS = 4
SEED_SWEEP = 64


def git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def package_bindings() -> dict:
    version = importlib.metadata.version("langdetect")
    assert version == EXPECTED_LANGDETECT_VERSION, version

    detector_path = Path(__import__("langdetect.detector", fromlist=["x"]).__file__).resolve()
    ngram_path = Path(__import__("langdetect.utils.ngram", fromlist=["x"]).__file__).resolve()
    got = {
        "detector.py": git_blob_sha(detector_path),
        "ngram.py": git_blob_sha(ngram_path),
    }
    assert got == EXPECTED_LANGDETECT_BLOBS, got
    return {"version": version, "git_blob_sha1": got}


def base_carrier(code: str) -> str:
    seed = LANGUAGE_SEEDS[code]
    return " ".join([seed] * 3)


def decorate_at_whitespace(text: str, placeholders: int, highlights: int) -> str:
    assert 0 <= placeholders <= MAX_PLACEHOLDERS
    assert 0 <= highlights <= MAX_HIGHLIGHTS
    pieces = [PLACEHOLDER] * placeholders + [HIGHLIGHT] * highlights
    if not pieces:
        return text
    i = text.find(" ")
    assert i > 0
    payload = " ".join(pieces)
    return text[:i] + " " + payload + " " + text[i + 1:]


def cleaning_counts(text: str) -> tuple[int, int, bool]:
    latin_count = 0
    non_latin_count = 0
    for ch in text:
        if "A" <= ch <= "z":
            latin_count += 1
        elif ch >= "\u0300" and unicode_block(ch) != "Latin Extended Additional":
            non_latin_count += 1
    remove_latin = latin_count * 2 < non_latin_count
    return latin_count, non_latin_count, remove_latin


def feature_stream(text: str) -> tuple[tuple[str, ...], tuple[int, int, bool], str]:
    detector_factory.init_factory()
    detector = detector_factory._factory.create()
    detector.append(text)
    counts = cleaning_counts(detector.text)
    detector.cleaning_text()
    cleaned = detector.text
    features = tuple(detector._extract_ngrams())
    return features, counts, cleaned


def scorer_regex_facts(text: str) -> tuple[int, int]:
    placeholders = len(re.findall(r"\[.*?\]", text))
    highlights = 0
    for match in re.findall(r"\*[^\n\*]*\*", text):
        if match.strip("*").strip():
            highlights += 1
    for match in re.findall(r"\*\*[^\n\*]*\*\*", text):
        if match.removeprefix("**").removesuffix("**").strip():
            highlights += 1
    return placeholders, highlights


def main() -> None:
    bindings = package_bindings()
    assert len(LANGUAGE_SEEDS) == 30

    exact_feature_equivalence_cases = 0
    branch_preservation_cases = 0
    minimum_nonlatin_margin = None
    language_rows = {}

    for code in sorted(LANGUAGE_SEEDS):
        base = base_carrier(code)
        base_features, base_counts, _ = feature_stream(base)
        assert base_features, ("NO_BASE_FEATURES", code)
        base_latin, base_nonlatin, base_branch = base_counts
        per_lang_cases = 0

        for p in range(MAX_PLACEHOLDERS + 1):
            for h in range(MAX_HIGHLIGHTS + 1):
                decorated = decorate_at_whitespace(base, p, h)
                got_p, got_h = scorer_regex_facts(decorated)
                assert got_p >= p, (code, p, h, got_p)
                assert got_h >= h, (code, p, h, got_h)

                features, counts, _ = feature_stream(decorated)
                latin, nonlatin, branch = counts
                assert branch == base_branch, (
                    "CLEANING_BRANCH_CHANGED", code, p, h,
                    base_counts, counts,
                )
                branch_preservation_cases += 1

                assert features == base_features, (
                    "LANGDETECT_FEATURE_STREAM_CHANGED", code, p, h
                )
                exact_feature_equivalence_cases += 1
                per_lang_cases += 1

                # The only surprising cleaning-text interaction is [] because
                # '[' and ']' lie in Python's lexical range 'A' <= ch <= 'z'.
                # Record the exact safety margin for non-Latin branches.
                if base_branch:
                    margin = nonlatin - 2 * latin
                    minimum_nonlatin_margin = (
                        margin if minimum_nonlatin_margin is None
                        else min(minimum_nonlatin_margin, margin)
                    )

        # The feature theorem makes decorator behavior distribution-identical
        # to the base carrier. Separately stress that each base carrier itself
        # lands on the requested language across a reproducible seed sweep.
        wrong = []
        for seed in range(SEED_SWEEP):
            DetectorFactory.seed = seed
            got = langdetect.detect(base)
            if got != code:
                wrong.append({"seed": seed, "got": got})
        assert not wrong, ("BASE_CARRIER_SEED_SWEEP_FAILURE", code, wrong)

        language_rows[code] = {
            "decorator_grid_cases": per_lang_cases,
            "base_feature_count": len(base_features),
            "base_cleaning_counts": {
                "latin_count": base_latin,
                "non_latin_count": base_nonlatin,
                "remove_latin_branch": base_branch,
            },
            "base_detection_seed_sweep": SEED_SWEEP,
            "base_detection_failures": 0,
        }

    DetectorFactory.seed = None

    expected_cases = len(LANGUAGE_SEEDS) * (MAX_PLACEHOLDERS + 1) * (MAX_HIGHLIGHTS + 1)
    assert exact_feature_equivalence_cases == expected_cases
    assert branch_preservation_cases == expected_cases
    assert minimum_nonlatin_margin is None or minimum_nonlatin_margin > 0

    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_LANG_DECORATOR_GATE_INDEPENDENT_VERIFICATION_V1",
        "status": "PASS__EXACT_30_CARRIER_FEATURE_STREAM_EQUIVALENCE_FOR_ALL_LEGAL_PLACEHOLDER_HIGHLIGHT_COUNTS__LANGDETECT_1_0_9__ZERO_ACCEPTANCE_CREDIT",
        "source_bindings": {
            "frozen_livebench_commit": FROZEN_LIVEBENCH_COMMIT,
            "frozen_livebench_instructions_blob": FROZEN_LIVEBENCH_INSTRUCTIONS_BLOB,
            "frozen_livebench_instructions_util_blob": FROZEN_LIVEBENCH_UTIL_BLOB,
            "brain_language_witness_blob": BRAIN_LANGUAGE_WITNESS_BLOB,
            "brain_semantic_reduction_blob": BRAIN_SEMANTIC_REDUCTION_BLOB,
            "langdetect_release_commit": EXPECTED_LANGDETECT_RELEASE_COMMIT,
            "langdetect": bindings,
        },
        "scope": {
            "language_carriers": len(LANGUAGE_SEEDS),
            "placeholder_count_range": [0, MAX_PLACEHOLDERS],
            "highlight_count_range": [0, MAX_HIGHLIGHTS],
            "decorator_grid_cases": expected_cases,
            "base_rng_seed_sweep_per_language": SEED_SWEEP,
            "base_detection_runs": len(LANGUAGE_SEEDS) * SEED_SWEEP,
        },
        "proof_facts": {
            "all_decorated_feature_streams_equal_base_feature_stream": True,
            "all_cleaning_text_branches_preserved": True,
            "all_requested_decorator_counts_satisfy_frozen_regex_shape": True,
            "minimum_nonlatin_cleaning_margin_after_decoration": minimum_nonlatin_margin,
            "base_carriers_correct_for_every_swept_rng_seed": True,
            "decorator_effect_on_langdetect_output_distribution": "IDENTICAL_TO_BASE_CARRIER_BECAUSE_ORDERED_NGRAM_FEATURE_STREAM_IS_EXACTLY_IDENTICAL",
        },
        "critical_path_consequence": {
            "prior_proven_semantic_kernel_count": 64,
            "semantic_kernel_count_after_this_gate_for_pinned_carrier_construction": 41,
            "hard_kernel_count_after_this_gate": 39,
            "kernels_deleted_from_current_proof_obligation": 23,
        },
        "language_rows": language_rows,
        "hard_nonclaims": [
            "NO_ARBITRARY_TEXT_PUNCTUATION_NEUTRALITY_CLAIM",
            "NO_FUTURE_OR_OTHER_LANGDETECT_VERSION_CLAIM",
            "NO_LIVEBENCH_TERMINAL_ROW_OR_HIDDEN_KWARG_READ",
            "NO_LIVEBENCH_SCORE_OR_ACCEPTANCE_CREDIT",
            "NO_GENERAL_SEMANTIC_CAPABILITY_OR_OWNERSHIP_CREDIT",
            "UNPINNED_RUNTIME_DEPENDENCY_STILL_REQUIRES_FAIL_CLOSED_VERSION_BINDING_IN_ANY_PRODUCTION_ACCEPTANCE_EXECUTOR",
        ],
        "accounting": {
            "terminal_cases_read": 0,
            "hidden_kwargs_read": 0,
            "incremental_spend_usd": 0,
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        },
    }
    OUT.write_text(
        json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
