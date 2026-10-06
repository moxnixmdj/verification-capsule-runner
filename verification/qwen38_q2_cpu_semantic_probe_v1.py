#!/usr/bin/env python3
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

RAW = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
OUT = Path(sys.argv[2])

def section(label: str, next_label: str | None) -> str:
    if next_label:
        m = re.search(rf"{label}\s*:\s*(.*?)(?=\n\s*{next_label}\s*:)", RAW, re.I | re.S)
    else:
        m = re.search(rf"{label}\s*:\s*(.*)$", RAW, re.I | re.S)
    return (m.group(1).strip() if m else "")

para = section("PARAPHRASE", "SIMPLIFY")
simp = section("SIMPLIFY", "SUMMARY")
summ = section("SUMMARY", "STORY")
story = section("STORY", None)

source_para = "On Tuesday, Mira moved 12 blue crates from Dock A to Dock B because the east gate was closed."

checks = {
    "four_labels_present": all(re.search(rf"(?mi)^\s*{x}\s*:", RAW) for x in ("PARAPHRASE","SIMPLIFY","SUMMARY","STORY")),
    "paraphrase_nonempty": bool(para),
    "paraphrase_preserves_mira": "mira" in para.lower(),
    "paraphrase_preserves_12": bool(re.search(r"\b12\b", para)),
    "paraphrase_preserves_docks": "dock a" in para.lower() and "dock b" in para.lower(),
    "paraphrase_not_verbatim_source": source_para.lower() not in para.lower(),
    "simplify_semantic_anchors": all(x in simp.lower() for x in ("plant","light","sugar")),
    "summary_semantic_anchors": all(x in summ.lower() for x in ("orion","battery")) and bool(re.search(r"(?:\$\s*)?3\s+million", summ, re.I)),
    "story_semantic_anchors": all(x in story.lower() for x in ("rill","compass","bridge")),
    "story_nontrivial": len(re.findall(r"\b\w+\b", story)) >= 20,
}
passed = all(checks.values())
doc = {
    "schema": "PROJECT_BRAIN_QWEN38_Q2_CPU_SEMANTIC_SMOKE_V1",
    "status": "PASS" if passed else "FAIL",
    "terminal_case_content_used": False,
    "synthetic_nonterminal_only": True,
    "semantic_surface": ["paraphrase","simplify","summarize","story_generation"],
    "checks": checks,
    "sections": {
        "paraphrase": para,
        "simplify": simp,
        "summary": summ,
        "story": story,
    },
    "hard_nonclaim": "This is an execution/semantic smoke probe only. It does not prove LiveBench >= Opus 5.5, quantization parity, ownership, acceptance, or terminal closure."
}
OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps(doc, indent=2, ensure_ascii=False))
raise SystemExit(0 if passed else 1)
