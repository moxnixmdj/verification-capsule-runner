#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
import time
import urllib.request
from pathlib import Path

SERVER = "http://127.0.0.1:8080/v1/chat/completions"
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("ROOT1_QWEN35_4B_SEMANTIC_GATE_V1.json")


def ask(prompt: str, max_tokens: int = 180) -> str:
    payload = {
        "messages": [
            {
                "role": "system",
                "content": (
                    "Answer the user's task directly. Do not show reasoning. "
                    "Return only the requested answer, with no preface or commentary."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "max_tokens": max_tokens,
        "stream": False,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        SERVER,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "ProjectBrain-Root1SemanticGate/1"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as response:
        doc = json.load(response)
    text = str(doc["choices"][0]["message"]["content"]).strip()
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.I | re.S).strip()
    return text


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower()).strip()


def wc(s: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", s, flags=re.UNICODE))


def one_sentence(s: str) -> bool:
    core = s.strip()
    # Semicolon/colon are allowed inside the sentence. Count terminal sentence punctuation.
    ends = re.findall(r"[.!?](?:[\"'”’)]*)?(?=\s|$)", core)
    return len(ends) <= 1


def groups(s: str, required_groups: list[list[str]]) -> bool:
    n = norm(s)
    return all(any(term.lower() in n for term in group) for group in required_groups)


def not_verbatim(answer: str, source: str) -> bool:
    a, b = norm(answer), norm(source)
    return a != b and b not in a


CASES = [
    {
        "id": "PARAPHRASE_1",
        "surface": "paraphrase",
        "source": "On Tuesday, Mira moved 12 blue crates from Dock A to Dock B because the east gate was closed.",
        "prompt": (
            'Paraphrase this sentence while preserving every fact, name, number, direction, location, day, color, and causal relation. '
            'Use different wording: "On Tuesday, Mira moved 12 blue crates from Dock A to Dock B because the east gate was closed."'
        ),
        "max_tokens": 90,
        "check": lambda a: (
            groups(a, [["mira"], ["tuesday"], ["12", "twelve"], ["blue"], ["crate"], ["dock a"], ["dock b"], ["east gate"], ["closed", "shut"]])
            and norm(a).find("dock a") < norm(a).find("dock b")
            and not_verbatim(a, "On Tuesday, Mira moved 12 blue crates from Dock A to Dock B because the east gate was closed.")
            and wc(a) <= 42
        ),
    },
    {
        "id": "PARAPHRASE_2",
        "surface": "paraphrase",
        "source": "Dr. Chen stored 3 soil samples in Cairo on Friday at 18°C after a power outage delayed the shipment.",
        "prompt": (
            'Paraphrase this sentence while preserving every fact, name, number, location, day, temperature, temporal relation, and cause. '
            'Use different wording: "Dr. Chen stored 3 soil samples in Cairo on Friday at 18°C after a power outage delayed the shipment."'
        ),
        "max_tokens": 90,
        "check": lambda a: (
            groups(a, [["chen"], ["3", "three"], ["soil"], ["sample"], ["cairo"], ["friday"], ["18°c", "18 °c", "18 degrees c", "18 degrees celsius"], ["power outage", "power failure"], ["delay"], ["shipment"]])
            and not_verbatim(a, "Dr. Chen stored 3 soil samples in Cairo on Friday at 18°C after a power outage delayed the shipment.")
            and wc(a) <= 46
        ),
    },
    {
        "id": "SIMPLIFY_1",
        "surface": "simplify",
        "prompt": (
            'Rewrite this for a 10-year-old in one short sentence without losing the scientific meaning: '
            '"Through photosynthesis, plants convert light energy into chemical energy stored in sugars."'
        ),
        "max_tokens": 80,
        "check": lambda a: groups(a, [["plant"], ["light"], ["energy"], ["sugar"]]) and one_sentence(a) and wc(a) <= 28,
    },
    {
        "id": "SIMPLIFY_2",
        "surface": "simplify",
        "prompt": (
            'Rewrite this for a 10-year-old in one short sentence without losing the scientific meaning: '
            '"Evaporation occurs when liquid water gains enough energy for molecules to escape into the air as water vapor."'
        ),
        "max_tokens": 80,
        "check": lambda a: (
            groups(a, [["water"], ["liquid"], ["air"], ["vapor", "gas"], ["energy", "heat", "warm"]])
            and one_sentence(a)
            and wc(a) <= 30
        ),
    },
    {
        "id": "SUMMARY_1",
        "surface": "summarize",
        "prompt": (
            'Summarize the following in one concise sentence while preserving every decision-relevant fact: '
            '"Orion Labs received $3 million in funding on Monday. The company said the money will expand its battery recycling pilot. '
            'It plans to double the pilot\'s processing capacity by December."'
        ),
        "max_tokens": 100,
        "check": lambda a: (
            groups(a, [["orion"], ["3 million", "$3 million", "$3m"], ["monday"], ["battery"], ["recycl"], ["double", "twice"], ["capacity"], ["december"]])
            and one_sentence(a)
            and wc(a) <= 38
        ),
    },
    {
        "id": "SUMMARY_2",
        "surface": "summarize",
        "prompt": (
            'Summarize the following in one concise sentence while preserving every decision-relevant fact: '
            '"Harborside Council approved 8 electric buses on Wednesday. The buses will serve 2 routes linking three schools with the city hospital. '
            'Service is scheduled to begin in March."'
        ),
        "max_tokens": 100,
        "check": lambda a: (
            groups(a, [["harborside"], ["8", "eight"], ["electric"], ["bus"], ["wednesday"], ["2", "two"], ["route"], ["three", "3"], ["school"], ["hospital"], ["march"]])
            and one_sentence(a)
            and wc(a) <= 40
        ),
    },
    {
        "id": "STORY_1",
        "surface": "story_generation",
        "prompt": (
            "Write a compact 40-80 word story about a fox named Rill who finds a broken compass beside a bridge, repairs it, "
            "and returns it to its owner. The three events must happen in that order."
        ),
        "max_tokens": 150,
        "check": lambda a: (
            groups(a, [["rill"], ["fox"], ["compass"], ["bridge"], ["broken", "cracked", "damaged"], ["repair", "fix", "mend"], ["owner", "traveler", "traveller"]])
            and 40 <= wc(a) <= 80
            and min([i for i in [norm(a).find("compass")] if i >= 0], default=10**9)
                < min([i for i in [norm(a).find("repair"), norm(a).find("fix"), norm(a).find("mend")] if i >= 0], default=10**9)
                < min([i for i in [norm(a).find("owner"), norm(a).find("traveler"), norm(a).find("traveller")] if i >= 0], default=10**9)
        ),
    },
    {
        "id": "STORY_2",
        "surface": "story_generation",
        "prompt": (
            "Write a compact 40-80 word story about an owl named Toma who discovers an unlit lantern at an old mill, replaces its damaged wick, "
            "lights it, and gives the working lantern back to a beekeeper. The events must happen in that order."
        ),
        "max_tokens": 150,
        "check": lambda a: (
            groups(a, [["toma"], ["owl"], ["lantern"], ["mill"], ["wick"], ["light"], ["beekeeper"]])
            and 40 <= wc(a) <= 80
            and norm(a).find("wick") < norm(a).rfind("light") < norm(a).find("beekeeper")
        ),
    },
]


def main() -> int:
    results = []
    surface_totals: dict[str, dict[str, int]] = {}
    for case in CASES:
        start = time.time()
        try:
            answer = ask(case["prompt"], case["max_tokens"])
            error = None
            passed = bool(case["check"](answer))
        except Exception as exc:
            answer = ""
            error = f"{type(exc).__name__}: {exc}"
            passed = False
        elapsed = round(time.time() - start, 3)
        surface = case["surface"]
        surface_totals.setdefault(surface, {"pass": 0, "total": 0})
        surface_totals[surface]["total"] += 1
        surface_totals[surface]["pass"] += int(passed)
        results.append(
            {
                "id": case["id"],
                "surface": surface,
                "pass": passed,
                "answer": answer,
                "word_count": wc(answer),
                "elapsed_seconds": elapsed,
                "error": error,
            }
        )
        print(json.dumps(results[-1], ensure_ascii=False), flush=True)

    passed_count = sum(int(x["pass"]) for x in results)
    required_surfaces = {"paraphrase", "simplify", "summarize", "story_generation"}
    all_surfaces_perfect = (
        set(surface_totals) == required_surfaces
        and all(v["pass"] == v["total"] and v["total"] >= 2 for v in surface_totals.values())
    )
    status = "PASS" if passed_count == len(CASES) and all_surfaces_perfect else "FAIL"
    doc = {
        "schema": "PROJECT_BRAIN_ROOT1_QWEN35_4B_SEMANTIC_GATE_V1",
        "status": status,
        "date": "2026-10-04",
        "candidate": {
            "model": "Qwen/Qwen3.5-4B",
            "quantization_repo": "bartowski/Qwen_Qwen3.5-4B-GGUF",
            "quantization_revision": "ba06320255db2dbec194dad738d066be90dabf29",
            "file": "Qwen_Qwen3.5-4B-Q4_K_M.gguf",
            "bytes": 3013027808,
            "sha256": "13c16f426047e2de38cd075bdade4a7bcbc8c774384876f677740cda65f8a983",
            "llama_cpp_commit": "7fe450e19305b828c199d602c23a8337aaa1f03b",
            "temperature": 0,
        },
        "gate": {
            "kind": "MEANING_SENSITIVE_SYNTHETIC_NONTERMINAL_FILTER",
            "surfaces": sorted(required_surfaces),
            "cases_total": len(CASES),
            "cases_pass": passed_count,
            "surface_results": surface_totals,
            "pass_rule": "8_OF_8_AND_2_OF_2_ON_EACH_REQUIRED_SURFACE",
        },
        "terminal_case_content_used": False,
        "fresh_terminal_reality_consumed": 0,
        "incremental_spend_usd": 0,
        "results": results,
        "interpretation": (
            "PASS keeps this exact 4B configuration alive as the byte-minimal semantic-core candidate. "
            "FAIL falsifies this exact prompt/runtime configuration on at least one required nonterminal semantic surface. "
            "Neither outcome alone establishes Opus 5.5 parity."
        ),
        "hard_nonclaims": [
            "NO_LIVEBENCH_TERMINAL_SCORE_CREDIT",
            "NO_OPUS55_PARITY_CLAIM",
            "NO_FAMILY_OR_OWNERSHIP_PROMOTION",
            "NO_CLAIM_THIS_SYNTHETIC_GATE_EXHAUSTS_GENERAL_SEMANTIC_CAPABILITY",
        ],
    }
    OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(doc, ensure_ascii=False), flush=True)
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
