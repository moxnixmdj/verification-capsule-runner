from __future__ import annotations

import difflib
import json
import re
import urllib.request

URL = "http://127.0.0.1:8080/v1/chat/completions"
MODEL = "brain-qwen3.5-9b"


def chat(prompt: str, *, max_tokens: int = 384) -> str:
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Follow the user's transformation request exactly. "
                    "Return only the requested final text, with no preamble, labels, or explanation."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "max_tokens": max_tokens,
        "stream": False,
    }
    req = urllib.request.Request(
        URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as response:
        assert response.status == 200
        data = json.loads(response.read().decode("utf-8", "replace"))
    assert str(data.get("model") or "") == MODEL, data
    choices = data.get("choices")
    assert isinstance(choices, list) and len(choices) == 1, data
    message = choices[0].get("message") or {}
    text = str(message.get("content") or "").strip()
    assert text, data
    return text


def words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]*", text)


def contains_all(text: str, anchors: list[str]) -> bool:
    low = text.lower()
    return all(anchor.lower() in low for anchor in anchors)


def one_sentence(text: str) -> bool:
    pieces = [p for p in re.split(r"(?<=[.!?])\s+", text.strip()) if p.strip()]
    return len(pieces) == 1


def surface_changed(source: str, output: str, ceiling: float = 0.94) -> bool:
    if source.strip().lower() == output.strip().lower():
        return False
    ratio = difflib.SequenceMatcher(None, source.lower(), output.lower()).ratio()
    return ratio < ceiling


def ordered(text: str, tokens: list[str]) -> bool:
    low = text.lower()
    pos = -1
    for token in tokens:
        nxt = low.find(token.lower(), pos + 1)
        if nxt < 0:
            return False
        pos = nxt
    return True


cases = [
    {
        "id": "paraphrase_1",
        "kind": "paraphrase",
        "source": "On Tuesday, engineer Mira Chen delivered seven sealed medical kits to the Nile clinic in Cairo before sunrise.",
        "prompt": (
            "Paraphrase this sentence without changing any fact. Use exactly one sentence and at most 28 words. "
            "Do not copy it verbatim.\n"
            "On Tuesday, engineer Mira Chen delivered seven sealed medical kits to the Nile clinic in Cairo before sunrise."
        ),
        "anchors": ["Tuesday", "Mira Chen", "seven", "medical kits", "Nile clinic", "Cairo", "sunrise"],
        "max_words": 28,
    },
    {
        "id": "paraphrase_2",
        "kind": "paraphrase",
        "source": "At 06:15, the solar ferry crossed Lake Nasser carrying twelve battery modules for Station Delta.",
        "prompt": (
            "Rewrite the sentence in different wording while preserving every fact. One sentence, no more than 24 words, "
            "and do not reproduce the source verbatim.\n"
            "At 06:15, the solar ferry crossed Lake Nasser carrying twelve battery modules for Station Delta."
        ),
        "anchors": ["06:15", "solar ferry", "Lake Nasser", "twelve", "battery modules", "Station Delta"],
        "max_words": 24,
    },
    {
        "id": "simplify_1",
        "kind": "simplify",
        "source": (
            "Although the observatory's backup generator had remained unused for eighteen months, technician Salma Idris "
            "started it at 14:20 on Friday so that Telescope A could continue tracking comet KX-41 during the grid outage."
        ),
        "prompt": (
            "Simplify the sentence for a 12-year-old reader. Keep every named fact and number. Use one sentence and at most 27 words.\n"
            "Although the observatory's backup generator had remained unused for eighteen months, technician Salma Idris "
            "started it at 14:20 on Friday so that Telescope A could continue tracking comet KX-41 during the grid outage."
        ),
        "anchors": ["eighteen months", "Salma Idris", "14:20", "Friday", "Telescope A", "KX-41", "grid outage"],
        "max_words": 27,
    },
    {
        "id": "simplify_2",
        "kind": "simplify",
        "source": (
            "Because the eastern valve registered 82 degrees Celsius, operator Yusuf closed Pump 3 before transferring "
            "the remaining 45 liters of coolant to Tank B."
        ),
        "prompt": (
            "Make this easier to understand without losing any fact. Use one sentence and at most 24 words.\n"
            "Because the eastern valve registered 82 degrees Celsius, operator Yusuf closed Pump 3 before transferring "
            "the remaining 45 liters of coolant to Tank B."
        ),
        "anchors": ["eastern valve", "82", "Yusuf", "Pump 3", "45", "coolant", "Tank B"],
        "max_words": 24,
    },
    {
        "id": "summarize_1",
        "kind": "summarize",
        "prompt": (
            "Summarize the report in exactly one sentence of at most 30 words while preserving the key facts.\n"
            "Report: The Falcon archive contains 240 glass negatives. Curator Lina Omar digitized 60 of them on Monday. "
            "The remaining 180 negatives are scheduled for scanning in Lab 4 next week."
        ),
        "anchors": ["Falcon archive", "240", "Lina Omar", "60", "Monday", "180", "Lab 4", "next week"],
        "max_words": 30,
    },
    {
        "id": "summarize_2",
        "kind": "summarize",
        "prompt": (
            "Give a one-sentence summary of at most 30 words. Preserve the quantities, place, and outcome.\n"
            "Report: A storm delayed Train 8 outside Luxor for 35 minutes. Engineers inspected two signal boxes. "
            "No damage was found, and Train 8 reached Aswan at 21:10."
        ),
        "anchors": ["Train 8", "Luxor", "35", "two", "No damage", "Aswan", "21:10"],
        "max_words": 30,
    },
    {
        "id": "story_1",
        "kind": "story",
        "prompt": (
            "Write a coherent 3-to-6 sentence microstory of 45 to 130 words. "
            "The story must first mention ORION-7 finding a BRASS-KEY, then later mention ORION-7 crossing HARBOR-9, "
            "and finally mention ORION-7 returning the BRASS-KEY. Keep those exact tokens."
        ),
        "ordered": ["ORION-7", "BRASS-KEY", "ORION-7", "HARBOR-9", "ORION-7", "BRASS-KEY"],
        "min_words": 45,
        "max_words": 130,
    },
    {
        "id": "story_2",
        "kind": "story",
        "prompt": (
            "Write a coherent 3-to-6 sentence microstory of 45 to 130 words. "
            "First, NORA-2 discovers MAP-17 in GARDEN-5. Later she uses MAP-17 to reach TOWER-6. "
            "At the end, NORA-2 gives MAP-17 to ILYA-4. Keep every uppercase token exact and preserve that event order."
        ),
        "ordered": ["NORA-2", "MAP-17", "GARDEN-5", "MAP-17", "TOWER-6", "NORA-2", "MAP-17", "ILYA-4"],
        "min_words": 45,
        "max_words": 130,
    },
    {
        "id": "paraphrase_3",
        "kind": "paraphrase",
        "source": "Researcher Amina Farouk stored nine lunar soil samples in Vault C at 18:40 after the spectrometer calibration finished.",
        "prompt": (
            "Paraphrase this sentence without changing any fact. Use exactly one sentence and at most 27 words. "
            "Do not copy it verbatim.\n"
            "Researcher Amina Farouk stored nine lunar soil samples in Vault C at 18:40 after the spectrometer calibration finished."
        ),
        "anchors": ["Amina Farouk", "nine", "lunar soil samples", "Vault C", "18:40", "spectrometer calibration"],
        "max_words": 27,
    },
    {
        "id": "simplify_3",
        "kind": "simplify",
        "source": (
            "Following three consecutive pressure alerts, supervisor Karim Hassan redirected 28 cubic meters of water "
            "from Reservoir 2 to Basin 7 at 09:05 to protect the northern pipeline."
        ),
        "prompt": (
            "Make this easier to understand for a 12-year-old without losing any fact. Use one sentence and at most 26 words.\n"
            "Following three consecutive pressure alerts, supervisor Karim Hassan redirected 28 cubic meters of water "
            "from Reservoir 2 to Basin 7 at 09:05 to protect the northern pipeline."
        ),
        "anchors": ["three", "Karim Hassan", "28", "Reservoir 2", "Basin 7", "09:05", "northern pipeline"],
        "max_words": 26,
    },
    {
        "id": "summarize_3",
        "kind": "summarize",
        "prompt": (
            "Summarize the report in exactly one sentence of at most 31 words while preserving the key facts.\n"
            "Report: Museum Delta received 96 ceramic fragments from Site R. Conservator Huda Nabil catalogued 40 fragments on Wednesday. "
            "The other 56 will be photographed in Room 12 on Friday."
        ),
        "anchors": ["Museum Delta", "96", "Site R", "Huda Nabil", "40", "Wednesday", "56", "Room 12", "Friday"],
        "max_words": 31,
    },
    {
        "id": "story_3",
        "kind": "story",
        "prompt": (
            "Write a coherent 3-to-6 sentence microstory of 45 to 130 words. "
            "First, VEGA-3 finds CRYSTAL-8 beside GATE-2. Later VEGA-3 carries CRYSTAL-8 through CANYON-4. "
            "At the end, VEGA-3 places CRYSTAL-8 inside ARCHIVE-6. Keep every uppercase token exact and preserve that event order."
        ),
        "ordered": ["VEGA-3", "CRYSTAL-8", "GATE-2", "VEGA-3", "CRYSTAL-8", "CANYON-4", "VEGA-3", "CRYSTAL-8", "ARCHIVE-6"],
        "min_words": 45,
        "max_words": 130,
    },
]

results = []
for case in cases:
    output = chat(case["prompt"])
    wc = len(words(output))
    checks: dict[str, bool] = {}

    if case["kind"] in {"paraphrase", "simplify", "summarize"}:
        checks["anchors_preserved"] = contains_all(output, case["anchors"])
        checks["one_sentence"] = one_sentence(output)
        checks["word_limit"] = wc <= case["max_words"]
    if case["kind"] == "paraphrase":
        checks["surface_changed"] = surface_changed(case["source"], output)
    if case["kind"] == "simplify":
        checks["shorter_than_source"] = wc < len(words(case["source"]))
    if case["kind"] == "story":
        sentence_count = len([p for p in re.split(r"(?<=[.!?])\s+", output.strip()) if p.strip()])
        checks["required_event_order"] = ordered(output, case["ordered"])
        checks["sentence_range"] = 3 <= sentence_count <= 6
        checks["word_range"] = case["min_words"] <= wc <= case["max_words"]
        checks["nontrivial_lexical_mass"] = len({w.lower() for w in words(output)}) >= 28

    passed = all(checks.values())
    results.append(
        {
            "id": case["id"],
            "kind": case["kind"],
            "pass": passed,
            "checks": checks,
            "word_count": wc,
            "output": output,
        }
    )

summary = {
    "schema": "PROJECT_BRAIN_LOCAL_QWEN_SEMANTIC_TEXT_NONTERMINAL_VERIFICATION_V1",
    "model_file": "Qwen3.5-9B-M-TS-Q4_K_M.gguf",
    "model_sha256": "f41c0a0c0e43bf721fb2da29374cd1a97271bac0bab08a9dc42964525e82350c",
    "model_bytes": 5060174144,
    "llama_cpp_commit": "bec4772f6a2527d371557b5d2032641e5ff7619c",
    "terminal_case_exposure": 0,
    "incremental_spend_usd": 0,
    "passed": sum(1 for row in results if row["pass"]),
    "required": len(results),
    "results": results,
}
summary["status"] = "PASS" if summary["passed"] == summary["required"] else "FAIL"
print(json.dumps(summary, sort_keys=True))
assert summary["status"] == "PASS", json.dumps(summary, indent=2, sort_keys=True)
