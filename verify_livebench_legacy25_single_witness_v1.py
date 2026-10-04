#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"

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

def setup():
    root = Path("/tmp/livebench")
    sys.path.insert(0, str(root / "livebench" / "if_runner"))
    from instruction_following_eval import instructions_registry
    return instructions_registry

def check(registry, iid, kwargs, response):
    cls = registry.INSTRUCTION_DICT[iid]
    obj = cls(iid)
    obj.build_description(**kwargs)
    ok = bool(obj.check_following(response))
    if not ok:
        raise AssertionError(f"{iid} rejected response={response!r} kwargs={kwargs!r}")

def main():
    registry = setup()
    assert len(registry.INSTRUCTION_DICT) == 25

    cases = [
        ("keywords:existence", {"keywords":["alpha","beta"]}, "alpha beta"),
        ("keywords:frequency", {"keyword":"kiwi","frequency":3,"relation":"at least"}, "kiwi kiwi kiwi"),
        ("keywords:frequency", {"keyword":"kiwi","frequency":3,"relation":"less than"}, "zxqv"),
        ("keywords:forbidden_words", {"forbidden_words":["bad","worse"]}, "zxqv"),
        ("keywords:letter_frequency", {"letter":"q","let_frequency":3,"let_relation":"at least"}, "qqq"),
        ("keywords:letter_frequency", {"letter":"q","let_frequency":3,"let_relation":"less than"}, "0000"),
        ("length_constraints:number_sentences", {"num_sentences":3,"relation":"at least"}, "Sentence0. Sentence1. Sentence2."),
        ("length_constraints:number_sentences", {"num_sentences":2,"relation":"less than"}, "One sentence."),
        ("length_constraints:number_sentences", {"num_sentences":1,"relation":"less than"}, ""),
        ("length_constraints:number_paragraphs", {"num_paragraphs":3}, "p0 *** p1 *** p2"),
        ("length_constraints:number_words", {"num_words":5,"relation":"at least"}, "w0 w1 w2 w3 w4"),
        ("length_constraints:number_words", {"num_words":5,"relation":"less than"}, "word"),
        ("length_constraints:nth_paragraph_first_word", {"num_paragraphs":3,"nth_paragraph":2,"first_word":"anchor"}, "p1\n\nanchor body\n\np3"),
        ("detectable_content:number_placeholders", {"num_placeholders":3}, "[x0] [x1] [x2]"),
        ("detectable_content:postscript", {"postscript_marker":"P.S."}, "body\nP.S. note"),
        ("detectable_content:postscript", {"postscript_marker":"P.P.S"}, "body\nP.P.S note"),
        ("detectable_format:number_bullet_lists", {"num_bullets":3}, "* item0\n* item1\n* item2"),
        ("detectable_format:constrained_response", {}, "My answer is yes."),
        ("detectable_format:number_highlighted_sections", {"num_highlights":3}, "*h0* *h1* *h2*"),
        ("detectable_format:multiple_sections", {"section_spliter":"SECTION","num_sections":3}, "SECTION 1\nbody1\nSECTION 2\nbody2\nSECTION 3\nbody3"),
        ("detectable_format:json_format", {}, "{}"),
        ("detectable_format:title", {}, "<<x>>"),
        ("combination:two_responses", {}, "alpha******beta"),
        ("combination:repeat_prompt", {"prompt_to_repeat":"original visible request"}, "original visible request\nanswer"),
        ("startend:end_checker", {"end_phrase":"Any other questions?"}, "body Any other questions?"),
        ("change_case:capital_word_frequency", {"capital_frequency":3,"capital_relation":"at least"}, "WORD0 WORD1 WORD2"),
        ("change_case:capital_word_frequency", {"capital_frequency":3,"capital_relation":"less than"}, "lowercase words"),
        ("change_case:english_capital", {}, "THIS IS A SIMPLE ENGLISH SENTENCE ABOUT PEOPLE PLACES WORK AND TIME"),
        ("change_case:english_lowercase", {}, "this is a simple english sentence about people places work and time"),
        ("punctuation:no_comma", {}, "text without forbidden punctuation"),
        ("startend:quotation", {}, '"quoted"'),
    ]

    for iid, kwargs, response in cases:
        check(registry, iid, kwargs, response)

    language_results = {}
    for code, seed in LANGUAGE_SEEDS.items():
        response = " ".join([seed] * 3)
        check(registry, "language:response_language", {"language":code}, response)
        language_results[code] = "pass"

    covered = {iid for iid, _, _ in cases} | {"language:response_language"}
    missing = sorted(set(registry.INSTRUCTION_DICT) - covered)
    extra = sorted(covered - set(registry.INSTRUCTION_DICT))
    assert not missing, missing
    assert not extra, extra

    out = {
        "schema":"LIVEBENCH_LEGACY25_SINGLE_WITNESS_PUBLIC_EXACT_SOURCE_VERIFICATION_V1",
        "status":"PASS",
        "livebench_commit":LIVEBENCH_COMMIT,
        "registered_types":len(registry.INSTRUCTION_DICT),
        "covered_types":len(covered),
        "representative_nonlanguage_cases":len(cases),
        "language_codes_verified":len(language_results),
        "language_results":language_results,
        "scope":"REPRESENTATIVE_EXACT_CHECKER_EXECUTION_PLUS_ALL_30_LANGUAGE_CODES__NOT_MULTI_CONSTRAINT_COMPOSITION__NOT_TERMINAL_POPULATION_SCORE",
        "acceptance_credit":False,
    }
    print(json.dumps(out, ensure_ascii=False, sort_keys=True))

if __name__ == "__main__":
    main()
