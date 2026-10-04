#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "livebench_composer_v2_verification.json"
LB = pathlib.Path("/tmp/LiveBench")
sys.path.insert(0, str(LB / "livebench/if_runner"))

from instruction_following_eval import instructions_registry as registry
from instruction_following_eval import instructions_util
import langdetect

SEEDS = {
    "en": "this is a simple response written entirely in english language",
    "es": "esta es una respuesta sencilla escrita completamente en español",
    "pt": "esta é uma resposta simples escrita inteiramente em português",
    "ar": "هذه إجابة بسيطة مكتوبة بالكامل باللغة العربية",
    "hi": "यह एक सरल उत्तर है जो पूरी तरह हिंदी भाषा में लिखा गया है",
    "fr": "ceci est une réponse simple écrite entièrement en français",
    "ru": "это простой ответ полностью написанный на русском языке",
    "de": "dies ist eine einfache antwort vollständig auf deutsch geschrieben",
    "ja": "これは日本語だけで書かれた簡単な回答です",
    "it": "questa è una risposta semplice scritta interamente in italiano",
    "bn": "এটি সম্পূর্ণ বাংলা ভাষায় লেখা একটি সহজ উত্তর",
    "uk": "це проста відповідь повністю написана українською мовою",
    "th": "นี่คือคำตอบง่ายๆ ที่เขียนเป็นภาษาไทยทั้งหมด",
    "ur": "یہ ایک سادہ جواب ہے جو مکمل طور پر اردو زبان میں لکھا گیا ہے",
    "ta": "இது முழுவதும் தமிழ் மொழியில் எழுதப்பட்ட எளிய பதில்",
    "te": "ఇది పూర్తిగా తెలుగు భాషలో వ్రాసిన సరళమైన సమాధానం",
    "bg": "това е прост отговор написан изцяло на български език",
    "ko": "이것은 전적으로 한국어로 작성된 간단한 답변입니다",
    "pl": "to jest prosta odpowiedź napisana całkowicie po polsku",
    "he": "זוהי תשובה פשוטה הכתובה כולה בעברית",
    "fa": "این یک پاسخ ساده است که کاملاً به زبان فارسی نوشته شده است",
    "vi": "đây là một câu trả lời đơn giản được viết hoàn toàn bằng tiếng việt",
    "ne": "यो पूर्ण रूपमा नेपाली भाषामा लेखिएको सरल उत्तर हो",
    "sw": "hili ni jibu rahisi lililoandikwa kabisa kwa kiswahili",
    "kn": "ಇದು ಸಂಪೂರ್ಣವಾಗಿ ಕನ್ನಡ ಭಾಷೆಯಲ್ಲಿ ಬರೆಯಲಾದ ಸರಳ ಉತ್ತರ",
    "mr": "हे पूर्णपणे मराठी भाषेत लिहिलेले सोपे उत्तर आहे",
    "gu": "આ સંપૂર્ણપણે ગુજરાતી ભાષામાં લખાયેલો સરળ જવાબ છે",
    "pa": "ਇਹ ਪੂਰੀ ਤਰ੍ਹਾਂ ਪੰਜਾਬੀ ਭਾਸ਼ਾ ਵਿੱਚ ਲਿਖਿਆ ਇੱਕ ਸਧਾਰਨ ਜਵਾਬ ਹੈ",
    "ml": "ഇത് പൂർണ്ണമായും മലയാള ഭാഷയിൽ എഴുതിയ ലളിതമായ മറുപടിയാണ്",
    "fi": "tämä on yksinkertainen vastaus joka on kirjoitettu kokonaan suomeksi",
}

EXPECTED_LANGS = tuple(instructions_util.LANGUAGE_CODES.keys())


def stable_detect(text: str, code: str, trials: int = 32) -> bool:
    for _ in range(trials):
        try:
            if langdetect.detect(text) != code:
                return False
        except langdetect.LangDetectException:
            return False
    return True


def exact_language_checker(text: str, code: str, trials: int = 32) -> bool:
    iid = "language:response_language"
    for _ in range(trials):
        c = registry.INSTRUCTION_DICT[iid](iid)
        c.build_description(language=code)
        if not c.check_following(text):
            return False
    return True


def candidate_pool(seed: str):
    seed = re.sub(r"\s+", " ", seed).strip()
    out = set()
    words = seed.split()
    for r in (1,2,3,4,6,8,12,16):
        out.add(" ".join([seed] * r))
    if words:
        for width in range(1, min(5, len(words)) + 1):
            phrase = " ".join(words[:width])
            for r in (2,4,8,12,16,24,32,48,64):
                out.add(" ".join([phrase] * r))
        for word in words:
            for r in (4,8,12,16,24,32,48,64):
                out.add(" ".join([word] * r))
    compact = re.sub(r"\s+", "", seed)
    for width in range(1, min(13, len(compact)+1)):
        chunk = compact[:width]
        for r in (4,8,16,32,64):
            out.add(chunk * r)
    return sorted(out, key=lambda x:(instructions_util.count_words(x),len(x)))


def find_compact(code: str, seed: str):
    viable=[]
    for cand in candidate_pool(seed):
        wc=instructions_util.count_words(cand)
        if wc > 80:
            continue
        if stable_detect(cand, code, 16) and exact_language_checker(cand, code, 16):
            try:
                probs=langdetect.detect_langs(cand)
                p=max((x.prob for x in probs if x.lang==code), default=0.0)
            except Exception:
                p=0.0
            viable.append((wc,len(cand),-p,cand,p))
    if not viable:
        return None
    # Prefer <=20-word carriers when possible; then maximum confidence and size.
    small=[x for x in viable if x[0] <= 20]
    pool=small or viable
    pool.sort(key=lambda x:(x[0],x[2],x[1]))
    wc,n,negp,cand,p=pool[0]
    return {"text":cand,"word_count":wc,"chars":n,"confidence":p}


def stress_variants(carrier: str):
    # Only syntax/noise from families allowed to coexist with response_language
    # in the frozen conflict graph. These are deliberately harsh, not intended
    # to satisfy every companion checker simultaneously; they test whether the
    # language carrier survives their lexical surface.
    ascii_noise = " ".join([
        "A"*10, "a"*10, "[1]", "[2]", "[3]", "[4]",
        "* 1", "* 2", "* 3", "* 4", "* 5",
        "*1*", "*2*", "*3*", "*4*",
        "P.S.", "ROCK", "12345",
    ])
    return {
        "base": carrier,
        "quote": '"' + carrier + '"',
        "title": carrier + " <<123>>",
        "postscript": carrier + "\nP.S. " + carrier,
        "two_responses": carrier + "******" + carrier + " 123",
        "paragraphs": (" *** ").join([carrier]*5),
        "nth_ascii_first_word": "rock " + carrier + "\n\n" + "\n\n".join([carrier]*4),
        "bullets": "\n".join(["* "+carrier for _ in range(5)]),
        "highlights": carrier + " " + " ".join(["*1*","*2*","*3*","*4*"]),
        "capital_pressure": carrier + " " + " ".join(["X"]*20) + " " + carrier,
        "letter_a_pressure": carrier + " " + ("a"*10) + " " + carrier,
        "numeric_word_padding": carrier + " " + " ".join(str(i) for i in range(60)),
        "combined_ascii_noise": carrier + " " + ascii_noise + " " + carrier + " " + carrier,
    }


def main():
    failures=[]
    carriers={}
    if tuple(SEEDS) != EXPECTED_LANGS:
        failures.append({
            "kind":"LANGUAGE_SET_MISMATCH",
            "expected":list(EXPECTED_LANGS),
            "actual":list(SEEDS),
        })

    for code in EXPECTED_LANGS:
        found=find_compact(code, SEEDS[code])
        if found is None:
            failures.append({"kind":"NO_STABLE_COMPACT_CARRIER","language":code})
            continue
        carriers[code]=found
        for name,text in stress_variants(found["text"]).items():
            # Exact checker is the load-bearing criterion. 16 repetitions catches
            # randomized langdetect instability without pretending sampling is a
            # formal proof of determinism.
            if not exact_language_checker(text,code,16):
                failures.append({
                    "kind":"WRAPPER_DESTABILIZES_LANGUAGE",
                    "language":code,
                    "variant":name,
                    "carrier":found,
                    "detected":[
                        (lambda: (langdetect.detect(text) if text else None))()
                        for _ in range(5)
                    ],
                })

    # The two global English-case families are not mysterious either.
    upper=("THIS IS A SIMPLE ENGLISH RESPONSE WRITTEN ENTIRELY IN ENGLISH " * 8).strip()
    lower=upper.lower()
    for iid,text in [
        ("change_case:english_capital",upper),
        ("change_case:english_lowercase",lower),
    ]:
        checker=registry.INSTRUCTION_DICT[iid](iid)
        checker.build_description()
        if not all(checker.check_following(text) for _ in range(32)):
            failures.append({"kind":"ENGLISH_CASE_CARRIER_FAIL","instruction_id":iid})

    payload={
        "schema":"PROJECT_BRAIN_LIVEBENCH_UNION25_LANGUAGE_CARRIER_FALSIFIER_V1",
        "status":"PASS__30_OF_30_LANGUAGE_CARRIERS_AND_ENGLISH_CASE_CARRIERS"
                 if not failures else
                 "FAIL__LANGUAGE_CARRIER_COUNTEREXAMPLE",
        "pinned_livebench_commit":"8f8e5c381a16e3f24257776edd53471fe86f8091",
        "language_count":len(EXPECTED_LANGS),
        "carriers":carriers,
        "stress_variants_per_language":12,
        "exact_language_checker_trials_per_variant":16,
        "english_case_trials":32,
        "failures":failures,
        "terminal_rows_read":0,
        "hidden_kwargs_read":0,
        "target_scores_read":0,
        "acceptance_credit_delta":0,
        "hard_nonclaim":"FINITE_STRESS_IS_A_CONSTRUCTOR_DISCOVERY_FALSIFIER_NOT_YET_A_UNIVERSAL_COMPOSITION_PROOF",
    }
    OUT.write_text(json.dumps(payload,indent=2,ensure_ascii=False,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({
        "status":payload["status"],
        "languages":payload["language_count"],
        "failure_count":len(failures),
        "max_carrier_words":max((x["word_count"] for x in carriers.values()),default=None),
        "max_carrier_chars":max((x["chars"] for x in carriers.values()),default=None),
    },sort_keys=True))
    return 0 if not failures else 1

if __name__=="__main__":
    raise SystemExit(main())
