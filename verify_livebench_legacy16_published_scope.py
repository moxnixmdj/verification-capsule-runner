#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

PAPER_URL = "https://proceedings.iclr.cc/paper_files/paper/2025/file/e4a46394ba5378b3f9a186a5b4c650d1-Paper-Conference.pdf"
LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
REGISTRY_URL = f"https://raw.githubusercontent.com/LiveBench/LiveBench/{LIVEBENCH_COMMIT}/livebench/if_runner/instruction_following_eval/instructions_registry.py"
INSTRUCTIONS_URL = f"https://raw.githubusercontent.com/LiveBench/LiveBench/{LIVEBENCH_COMMIT}/livebench/if_runner/instruction_following_eval/instructions.py"
EXPECTED_REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
EXPECTED_INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"

INCLUDED_LABELS = (
    "Include Keywords",
    "Forbidden Words",
    "Number Paragraphs",
    "Number Words",
    "Number Sentences",
    "Number Paragraphs + First Word in i-th Paragraph",
    "Postscript",
    "Number Bullets",
    "Title",
    "Multiple Sections",
    "JSON Format",
    "Repeat Prompt",
    "Two Responses",
    "End Checker",
    "Quotation",
    "No Commas",
)
EXCLUDED_LABELS = (
    "Keyword Frequency",
    "Letter Frequency",
    "Response Language",
    "Number Placeholders",
    "Choose From",
    "Minimum Number Highlighted Section",
    "All Uppercase",
    "All Lowercase",
    "Frequency of All-capital Words",
)
INCLUDED_IDS = (
    "keywords:existence",
    "keywords:forbidden_words",
    "length_constraints:number_paragraphs",
    "length_constraints:number_words",
    "length_constraints:number_sentences",
    "length_constraints:nth_paragraph_first_word",
    "detectable_content:postscript",
    "detectable_format:number_bullet_lists",
    "detectable_format:title",
    "detectable_format:multiple_sections",
    "detectable_format:json_format",
    "combination:repeat_prompt",
    "combination:two_responses",
    "startend:end_checker",
    "startend:quotation",
    "punctuation:no_comma",
)
EXCLUDED_IDS = (
    "keywords:frequency",
    "keywords:letter_frequency",
    "language:response_language",
    "detectable_content:number_placeholders",
    "detectable_format:constrained_response",
    "detectable_format:number_highlighted_sections",
    "change_case:english_capital",
    "change_case:english_lowercase",
    "change_case:capital_word_frequency",
)

def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "project-brain-independent-verifier/1"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()

def git_blob_sha(data: bytes) -> str:
    h = hashlib.sha1()
    h.update(f"blob {len(data)}\0".encode())
    h.update(data)
    return h.hexdigest()

def norm(s: str) -> str:
    s = s.replace("–", "-").replace("—", "-").replace("’", "'")
    return re.sub(r"\s+", " ", s).strip()

def row_has_livebench_tick(line: str) -> bool:
    # pdftotext -layout keeps the two rightmost boolean columns.  A LiveBench
    # member row has two check marks; an excluded IFEval-only row has one.
    return line.count("✓") >= 2

def main() -> None:
    registry = fetch(REGISTRY_URL)
    instructions = fetch(INSTRUCTIONS_URL)
    assert git_blob_sha(registry) == EXPECTED_REGISTRY_BLOB
    assert git_blob_sha(instructions) == EXPECTED_INSTRUCTIONS_BLOB
    registry_text = registry.decode("utf-8")
    for iid in INCLUDED_IDS + EXCLUDED_IDS:
        assert repr(iid) in registry_text or ('"' + iid + '"') in registry_text or ("'" + iid + "'") in registry_text
    assert len(INCLUDED_IDS) == 16
    assert len(EXCLUDED_IDS) == 9
    assert len(set(INCLUDED_IDS) | set(EXCLUDED_IDS)) == 25
    assert not (set(INCLUDED_IDS) & set(EXCLUDED_IDS))

    pdf = fetch(PAPER_URL)
    assert len(pdf) > 500_000
    assert pdf.startswith(b"%PDF")

    with tempfile.TemporaryDirectory() as td:
        pdf_path = Path(td) / "paper.pdf"
        txt_path = Path(td) / "paper.txt"
        pdf_path.write_bytes(pdf)
        subprocess.run(
            ["pdftotext", "-layout", "-f", "19", "-l", "19", str(pdf_path), str(txt_path)],
            check=True,
        )
        page = txt_path.read_text(encoding="utf-8", errors="replace")

    page_n = norm(page)
    assert "The list of 25 instructions" in page_n
    assert "16 that are both" in page_n and "LiveBench" in page_n

    # Reconstruct table membership from the actual conference PDF layout.
    # Labels that wrap across lines are checked over a normalized sliding window.
    lines = [norm(x) for x in page.splitlines() if norm(x)]
    joined = "\n".join(lines)

    def find_row(label: str) -> str:
        words = label.split()
        # Direct line first.
        for line in lines:
            if label.lower() in line.lower():
                return line
        # Wrapped labels: combine up to 3 consecutive physical lines.
        for width in (2, 3):
            for i in range(len(lines) - width + 1):
                combo = norm(" ".join(lines[i:i+width]))
                if all(w.lower().rstrip(".,") in combo.lower() for w in words):
                    return combo
        raise AssertionError("TABLE_LABEL_NOT_FOUND:" + label)

    inclusion_rows = {}
    exclusion_rows = {}
    for label in INCLUDED_LABELS:
        row = find_row(label)
        if not row_has_livebench_tick(row):
            raise AssertionError("EXPECTED_LIVEBENCH_TICK_MISSING:" + label + "::" + row)
        inclusion_rows[label] = row
    for label in EXCLUDED_LABELS:
        row = find_row(label)
        if row_has_livebench_tick(row):
            raise AssertionError("UNEXPECTED_LIVEBENCH_TICK:" + label + "::" + row)
        if "✓" not in row:
            raise AssertionError("IFEVAL_TICK_MISSING:" + label + "::" + row)
        exclusion_rows[label] = row

    print("LIVEBENCH_LEGACY16_PUBLISHED_SCOPE_VERIFICATION=PASS")
    print("paper_sha256=" + hashlib.sha256(pdf).hexdigest())
    print("registry_blob_sha=" + git_blob_sha(registry))
    print("instructions_blob_sha=" + git_blob_sha(instructions))
    print("published_livebench_types=16")
    print("published_excluded_legacy_types=9")
    print("legacy_union=25")
    print("terminal_rows_decoded=0")
    print("terminal_instruction_id_lists_decoded=0")
    print("terminal_kwargs_decoded=0")
    print("deduction=FROZEN_LEGACY25_UPPER_BOUND_REDUCES_TO_PUBLISHED_LIVEBENCH16_DESIGN_SURFACE")

if __name__ == "__main__":
    main()
