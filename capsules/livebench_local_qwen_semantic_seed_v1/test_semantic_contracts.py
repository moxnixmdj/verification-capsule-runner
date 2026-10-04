#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from canonical.runtime import local_qwen_semantic_seed_v1 as seed


def words(text: str) -> list[str]:
    return re.findall(r"\b[\w'-]+\b", text, flags=re.UNICODE)


def contains_all(text: str, anchors: list[str]) -> bool:
    low = text.casefold()
    return all(a.casefold() in low for a in anchors)


@dataclass(frozen=True)
class Contract:
    kind: str
    prompt: str
    anchors: tuple[str, ...]
    source: str | None = None
    max_words: int | None = None
    ending: str | None = None


contracts = [
    Contract(
        "paraphrase",
        "Paraphrase the following sentence. Preserve the marker facts ORION, MARS, 2031, and 48 exactly. "
        "Do not repeat the original sentence verbatim. Original: ORION reached MARS in 2031 and transmitted 48 images.",
        ("ORION", "MARS", "2031", "48"),
        "ORION reached MARS in 2031 and transmitted 48 images.",
    ),
    Contract(
        "paraphrase",
        "Paraphrase this sentence while preserving IMANI, CEDAR, LAKE-NERA, and TUESDAY exactly. "
        "Do not copy the original sentence verbatim. Original: IMANI planted CEDAR trees beside LAKE-NERA on TUESDAY.",
        ("IMANI", "CEDAR", "LAKE-NERA", "TUESDAY"),
        "IMANI planted CEDAR trees beside LAKE-NERA on TUESDAY.",
    ),
    Contract(
        "paraphrase",
        "Paraphrase this sentence while preserving COPPER, 12, TRAINS, and WINTER exactly. "
        "Do not copy it verbatim. Original: A COPPER bridge can carry 12 TRAINS per hour during WINTER.",
        ("COPPER", "12", "TRAINS", "WINTER"),
        "A COPPER bridge can carry 12 TRAINS per hour during WINTER.",
    ),
    Contract(
        "simplify",
        "Rewrite this for a young reader in at most 18 words. Preserve VALVE, 120-KPA, and CHAMBER exactly. "
        "Text: Because atmospheric pressure can fluctuate unpredictably, the technician cautiously adjusted the VALVE "
        "until the CHAMBER stabilized at precisely 120-KPA before the experiment continued.",
        ("VALVE", "120-KPA", "CHAMBER"),
        max_words=18,
    ),
    Contract(
        "simplify",
        "Simplify this in at most 16 words. Preserve MINA, LIBRARY, and 6-PM exactly. "
        "Text: Despite an unexpectedly complicated sequence of transit delays, MINA ultimately arrived at the LIBRARY "
        "shortly before the scheduled 6-PM meeting.",
        ("MINA", "LIBRARY", "6-PM"),
        max_words=16,
    ),
    Contract(
        "simplify",
        "Simplify this in at most 16 words. Preserve SENSOR, BATTERY, and 14-PERCENT exactly. "
        "Text: After repeatedly sampling the environment throughout the afternoon, the SENSOR reported that the BATTERY "
        "had declined to 14-PERCENT, prompting an immediate recharge.",
        ("SENSOR", "BATTERY", "14-PERCENT"),
        max_words=16,
    ),
    Contract(
        "summarize",
        "Summarize the passage in one sentence of at most 22 words. Preserve ATLAS, 7-SAMPLES, and ICELAND exactly. "
        "Passage: The ATLAS expedition crossed a volcanic plain in ICELAND. The team collected 7-SAMPLES from separate "
        "vents. The samples were sealed and sent to the laboratory that evening.",
        ("ATLAS", "7-SAMPLES", "ICELAND"),
        max_words=22,
    ),
    Contract(
        "summarize",
        "Summarize in one sentence of at most 22 words. Preserve LUMA-SCHOOL, 240-STUDENTS, and SOLAR-PANELS exactly. "
        "Passage: LUMA-SCHOOL serves 240-STUDENTS. Its roof was renovated during summer. SOLAR-PANELS now provide most "
        "daytime electricity and reduce demand from the grid.",
        ("LUMA-SCHOOL", "240-STUDENTS", "SOLAR-PANELS"),
        max_words=22,
    ),
    Contract(
        "summarize",
        "Summarize in one sentence of at most 22 words. Preserve PROJECT-CEDAR, 2-MILLION-EUROS, and 2028 exactly. "
        "Passage: PROJECT-CEDAR received 2-MILLION-EUROS for a rural clinic. Construction begins next spring. "
        "The clinic is scheduled to open in 2028 after equipment testing.",
        ("PROJECT-CEDAR", "2-MILLION-EUROS", "2028"),
        max_words=22,
    ),
    Contract(
        "story_generation",
        "Write a very short story of 2 to 4 sentences. It must include NIA, BLUE-KEY, and OBSERVATORY exactly. "
        "NIA must use the BLUE-KEY to open the OBSERVATORY. End exactly with: THE-STARS-ANSWERED.",
        ("NIA", "BLUE-KEY", "OBSERVATORY"),
        ending="THE-STARS-ANSWERED.",
    ),
    Contract(
        "story_generation",
        "Write a very short story of 2 to 4 sentences. It must include RAFI, BROKEN-COMPASS, and DESERT-WELL exactly. "
        "RAFI must reach the DESERT-WELL while carrying the BROKEN-COMPASS. End exactly with: WATER-WAS-FOUND.",
        ("RAFI", "BROKEN-COMPASS", "DESERT-WELL"),
        ending="WATER-WAS-FOUND.",
    ),
    Contract(
        "story_generation",
        "Write a very short story of 2 to 4 sentences. It must include MIRA-7, GLASS-SEED, and MOON-GARDEN exactly. "
        "MIRA-7 must plant the GLASS-SEED in the MOON-GARDEN. End exactly with: THE-FIRST-LEAF-OPENED.",
        ("MIRA-7", "GLASS-SEED", "MOON-GARDEN"),
        ending="THE-FIRST-LEAF-OPENED.",
    ),
]


results = []
for i, c in enumerate(contracts):
    out = seed.generate(c.prompt, timeout_s=180, max_tokens=256)
    text = out["response"].strip()
    checks = {
        "nonempty": bool(text),
        "anchors": contains_all(text, list(c.anchors)),
        "local_transport": out["transport"] == "PINNED_LOCAL_QWEN_LLAMA_CPP_CHAT_COMPLETION",
        "zero_remote_dependencies": out["remote_generation_dependencies"] == 0 and out["api_key_dependencies"] == 0,
    }
    if c.kind == "paraphrase":
        checks["not_verbatim_source"] = text.casefold() != (c.source or "").casefold()
    if c.max_words is not None:
        checks["max_words"] = len(words(text)) <= c.max_words
    if c.kind == "summarize":
        checks["one_sentence_surface"] = len(re.findall(r"[.!?]+(?:\s|$)", text)) <= 1
    if c.ending is not None:
        checks["exact_ending"] = text.endswith(c.ending)

    passed = all(checks.values())
    results.append(
        {
            "index": i,
            "kind": c.kind,
            "passed": passed,
            "checks": checks,
            "word_count": len(words(text)),
            "response": text,
            "duration_s": out["duration_s"],
            "model": out["model"],
        }
    )
    if not passed:
        raise AssertionError(json.dumps(results[-1], ensure_ascii=False, sort_keys=True))

counts = {}
for row in results:
    counts[row["kind"]] = counts.get(row["kind"], 0) + int(row["passed"])

assert counts == {
    "paraphrase": 3,
    "simplify": 3,
    "summarize": 3,
    "story_generation": 3,
}, counts

print(
    json.dumps(
        {
            "schema": "PROJECT_BRAIN_LIVEBENCH_LOCAL_QWEN_SEMANTIC_NONTERMINAL_VERIFICATION_V1",
            "status": "PASS",
            "passes": 12,
            "required_passes": 12,
            "counts": counts,
            "results": results,
            "terminal_case_exposure": 0,
            "terminal_prompt_exposure": 0,
            "incremental_spend_usd": 0,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
)
