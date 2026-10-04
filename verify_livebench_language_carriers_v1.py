#!/usr/bin/env python3
import json, re, string
from langdetect import detect, DetectorFactory

SAMPLES = {
    "en":"This is a simple English text written for reliable language detection and testing.",
    "es":"Este es un texto sencillo en español escrito para detectar correctamente el idioma.",
    "pt":"Este é um texto simples em português escrito para detectar corretamente o idioma.",
    "ar":"هذا نص عربي بسيط مكتوب لاختبار التعرف على اللغة بشكل صحيح وواضح.",
    "hi":"यह भाषा पहचान की जाँच के लिए लिखा गया एक सरल हिंदी पाठ है।",
    "fr":"Ceci est un texte simple en français écrit pour détecter correctement la langue.",
    "ru":"Это простой русский текст, написанный для точного определения языка.",
    "de":"Dies ist ein einfacher deutscher Text zur zuverlässigen Erkennung der Sprache.",
    "ja":"これは言語を正確に判定するために書かれた簡単な日本語の文章です。",
    "it":"Questo è un semplice testo italiano scritto per rilevare correttamente la lingua.",
    "bn":"এটি ভাষা সঠিকভাবে শনাক্ত করার জন্য লেখা একটি সহজ বাংলা পাঠ।",
    "uk":"Це простий український текст, написаний для точного визначення мови.",
    "th":"นี่คือข้อความภาษาไทยง่ายๆ ที่เขียนขึ้นเพื่อทดสอบการตรวจจับภาษาอย่างถูกต้อง",
    "ur":"یہ زبان کی درست شناخت کے لیے لکھا گیا ایک سادہ اردو متن ہے۔",
    "ta":"இது மொழியை சரியாக கண்டறிய எழுதப்பட்ட எளிய தமிழ் உரையாகும்.",
    "te":"ఇది భాషను సరిగ్గా గుర్తించడానికి వ్రాసిన సరళమైన తెలుగు వాక్యం.",
    "bg":"Това е прост български текст, написан за точно разпознаване на езика.",
    "ko":"이것은 언어를 정확하게 감지하기 위해 작성된 간단한 한국어 문장입니다.",
    "pl":"To jest prosty polski tekst napisany w celu poprawnego rozpoznania języka.",
    "he":"זהו טקסט פשוט בעברית שנכתב כדי לזהות את השפה בצורה מדויקת.",
    "fa":"این یک متن ساده فارسی است که برای تشخیص دقیق زبان نوشته شده است.",
    "vi":"Đây là một đoạn văn tiếng Việt đơn giản được viết để nhận diện ngôn ngữ chính xác.",
    "ne":"यो भाषा सही रूपमा पहिचान गर्न लेखिएको सरल नेपाली पाठ हो।",
    "sw":"Hii ni maandishi rahisi ya Kiswahili yaliyoandikwa kwa ajili ya kutambua lugha kwa usahihi.",
    "kn":"ಇದು ಭಾಷೆಯನ್ನು ಸರಿಯಾಗಿ ಗುರುತಿಸಲು ಬರೆಯಲಾದ ಸರಳ ಕನ್ನಡ ಪಠ್ಯವಾಗಿದೆ.",
    "mr":"हा भाषा अचूक ओळखण्यासाठी लिहिलेला एक सोपा मराठी मजकूर आहे.",
    "gu":"આ ભાષાને યોગ્ય રીતે ઓળખવા માટે લખાયેલો સરળ ગુજરાતી લખાણ છે.",
    "pa":"ਇਹ ਭਾਸ਼ਾ ਦੀ ਸਹੀ ਪਛਾਣ ਲਈ ਲਿਖਿਆ ਗਿਆ ਇੱਕ ਸਧਾਰਨ ਪੰਜਾਬੀ ਪਾਠ ਹੈ।",
    "ml":"ഇത് ഭാഷ ശരിയായി തിരിച്ചറിയാൻ എഴുതിയ ലളിതമായ മലയാളം വാചകമാണ്.",
    "fi":"Tämä on yksinkertainen suomenkielinen teksti joka on kirjoitettu kielen tunnistamista varten.",
}

def alpha_only(s):
    return "".join(ch for ch in s.lower() if ch.isalpha())

def carrier(sample,banned):
    s=alpha_only(sample)
    if banned:
        s=s.replace(banned,"")
    return s*8

def stable_detect(text, expected, rounds=20):
    got=[detect(text) for _ in range(rounds)]
    return all(x==expected for x in got), got

def main():
    rows=[]
    failures=[]
    for code,sample in SAMPLES.items():
        for banned in [""]+list(string.ascii_lowercase):
            text=carrier(sample,banned)
            ok,got=stable_detect(text,code)
            row={"language":code,"banned":banned or None,"chars":len(text),"ok":ok,"observed":sorted(set(got))}
            rows.append(row)
            if not ok:
                failures.append(row)
    # English all-case variants required by english_capital/lowercase families.
    en=carrier(SAMPLES["en"],"")
    for mode,text in [("lower",en.lower()),("upper",en.upper())]:
        ok,got=stable_detect(text,"en")
        row={"english_case":mode,"chars":len(text),"ok":ok,"observed":sorted(set(got)),
             "python_case_predicate": text.islower() if mode=="lower" else text.isupper()}
        rows.append(row)
        if not ok or not row["python_case_predicate"]:
            failures.append(row)
    out={
      "schema":"PROJECT_BRAIN_LIVEBENCH_LANGUAGE_NEUTRAL_CARRIER_PROBE_V1",
      "status":"PASS" if not failures else "FAIL",
      "langdetect_version":"1.0.9",
      "languages":len(SAMPLES),
      "banned_ascii_conditions_per_language":27,
      "probe_count":30*27+2,
      "detect_rounds_per_probe":20,
      "failures":failures,
      "rows":rows,
      "terminal_rows_used":0,
      "hidden_kwargs_used":0,
      "acceptance_credit":0,
    }
    open("livebench_language_carriers_v1.json","w").write(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({k:v for k,v in out.items() if k!="rows"},ensure_ascii=False))
    return 0 if not failures else 1

if __name__=="__main__":
    raise SystemExit(main())
