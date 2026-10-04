#!/usr/bin/env python3
from __future__ import annotations

import ast
from collections import Counter, defaultdict
import hashlib
import json
import re
import urllib.request
from pathlib import Path
from typing import Any, Callable

import pyarrow.parquet as pq

SCHEMA = "INDEPENDENT_LIVEBENCH_LEGACY_PREDECESSOR_COMPILER_REPLAY_SOL_V1"
REV = "4f7ab12f0d47848da31de92bd7cc3d7d4acfe695"
SHA256 = "57cbc3a738f7a95b234125965929247e7781ce6c5216bdea1d18548f4b10e98c"
BYTES = 277319
ROWS = 200
URL = (
    "https://huggingface.co/datasets/livebench/instruction_following/resolve/"
    + REV + "/data/test-00000-of-00001.parquet?download=true"
)

LANG = {
    "English":"en","Spanish":"es","Portuguese":"pt","Arabic":"ar","Hindi":"hi",
    "French":"fr","Russian":"ru","German":"de","Japanese":"ja","Italian":"it",
    "Bengali":"bn","Ukrainian":"uk","Thai":"th","Urdu":"ur","Tamil":"ta",
    "Telugu":"te","Bulgarian":"bg","Korean":"ko","Polish":"pl","Hebrew":"he",
    "Persian":"fa","Vietnamese":"vi","Nepali":"ne","Swahili":"sw","Kannada":"kn",
    "Marathi":"mr","Gujarati":"gu","Punjabi":"pa","Malayalam":"ml","Finnish":"fi",
}

def lit_list(s: str) -> list[str]:
    v = ast.literal_eval(s)
    if not isinstance(v, (list, tuple)) or not all(isinstance(x, str) for x in v):
        raise ValueError("string list required")
    return list(v)

def ident(s: str) -> str:
    return s.strip()

def integer(s: str) -> int:
    return int(s)

SPECS: dict[str, tuple[str, dict[str, Callable[[str], Any]]]] = {
    "keywords:existence": (
        r"Include keywords (?P<keywords>\[[^\n]*?\]) in the response\.",
        {"keywords": lit_list},
    ),
    "keywords:frequency": (
        r"In your response, the word (?P<keyword>.+?) should appear (?P<relation>less than|at least) (?P<frequency>\d+) times\.",
        {"keyword": ident, "relation": ident, "frequency": integer},
    ),
    "keywords:forbidden_words": (
        r"Do not include keywords (?P<forbidden_words>\[[^\n]*?\]) in the response\.",
        {"forbidden_words": lit_list},
    ),
    "keywords:letter_frequency": (
        r"In your response, the letter (?P<letter>[A-Za-z]) should appear (?P<let_relation>less than|at least) (?P<let_frequency>\d+) times\.",
        {"letter": lambda x: x.lower(), "let_relation": ident, "let_frequency": integer},
    ),
    "language:response_language": (
        r"Your ENTIRE response should be in (?P<language_name>[A-Za-z]+) language, no other language is allowed\.",
        {"language_name": ident},
    ),
    "length_constraints:number_sentences": (
        r"Your response should contain (?P<relation>less than|at least) (?P<num_sentences>\d+) sentences\.",
        {"relation": ident, "num_sentences": integer},
    ),
    "length_constraints:number_paragraphs": (
        r"There should be (?P<num_paragraphs>\d+) paragraphs\. Paragraphs are separated with the markdown divider: \*\*\*",
        {"num_paragraphs": integer},
    ),
    "length_constraints:number_words": (
        r"Answer with (?P<relation>less than|at least) (?P<num_words>\d+) words\.",
        {"relation": ident, "num_words": integer},
    ),
    "length_constraints:nth_paragraph_first_word": (
        r"There should be (?P<num_paragraphs>\d+) paragraphs\. Paragraphs and only paragraphs are separated with each other by two new lines as if it was '\\\\n\\\\n' in python\. Paragraph (?P<nth_paragraph>\d+) must start with word (?P<first_word>[^.\s]+)\.",
        {"num_paragraphs": integer, "nth_paragraph": integer, "first_word": lambda x: x.lower()},
    ),
    "detectable_content:number_placeholders": (
        r"The response must contain at least (?P<num_placeholders>\d+) placeholders represented by square brackets, such as \[address\]\.",
        {"num_placeholders": integer},
    ),
    "detectable_content:postscript": (
        r"At the end of your response, please explicitly add a postscript starting with (?P<postscript_marker>P\.P\.S|P\.S\.)",
        {"postscript_marker": ident},
    ),
    "detectable_format:number_bullet_lists": (
        r"Your answer must contain exactly (?P<num_bullets>\d+) bullet points\.",
        {"num_bullets": integer},
    ),
    "detectable_format:constrained_response": (
        r"Answer with one of the following options: \('My answer is yes\.', 'My answer is no\.', 'My answer is maybe\.'\)",
        {},
    ),
    "detectable_format:number_highlighted_sections": (
        r"Highlight at least (?P<num_highlights>\d+) sections in your answer with markdown, i\.e\. \*highlighted section\*\.",
        {"num_highlights": integer},
    ),
    "detectable_format:multiple_sections": (
        r"Your response must have (?P<num_sections>\d+) sections\. Mark the beginning of each section with (?P<section_spliter>Section|SECTION) X, such as:",
        {"num_sections": integer, "section_spliter": ident},
    ),
    "detectable_format:json_format": (
        r"Entire output should be wrapped in JSON format\. You can use markdown ticks such as ```\.",
        {},
    ),
    "detectable_format:title": (
        r"Your answer must contain a title, wrapped in double angular brackets, such as <<poem of joy>>\.",
        {},
    ),
    "combination:two_responses": (
        r"Give two different responses\. Responses and only responses should be separated by 6 asterisk symbols: \*\*\*\*\*\*\.",
        {},
    ),
    "combination:repeat_prompt": (
        r"First repeat the request word for word without change, then give your answer \(1\. do not say any words or characters before repeating the request; 2\. the request you need to repeat does not include this sentence\)",
        {},
    ),
    "startend:end_checker": (
        r"Finish your response with this exact phrase (?P<end_phrase>.+?)\. No other words should follow this phrase\.",
        {"end_phrase": ident},
    ),
    "change_case:capital_word_frequency": (
        r"In your response, words with all capital letters should appear (?P<capital_relation>less than|at least) (?P<capital_frequency>\d+) times\.",
        {"capital_relation": ident, "capital_frequency": integer},
    ),
    "change_case:english_capital": (
        r"Your entire response should be in English, and in all capital letters\.",
        {},
    ),
    "change_case:english_lowercase": (
        r"Your entire response should be in English, and in all lowercase letters\. No capital letters are allowed\.",
        {},
    ),
    "punctuation:no_comma": (
        r"In your entire response, refrain from the use of any commas\.",
        {},
    ),
    "startend:quotation": (
        r"Wrap your entire response with double quotation marks\.",
        {},
    ),
}

COMPILED = {k: re.compile(v[0], flags=re.DOTALL) for k, v in SPECS.items()}
REPEAT_MARKER = (
    "First repeat the request word for word without change,"
    " then give your answer (1. do not say any words or characters"
    " before repeating the request; 2. the request you need to repeat"
    " does not include this sentence)"
)

def compile_visible(prompt: str) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for iid, pat in COMPILED.items():
        for m in pat.finditer(prompt):
            slots = {}
            converters = SPECS[iid][1]
            for k, raw in m.groupdict().items():
                if raw is not None:
                    slots[k] = converters[k](raw)
            if iid == "language:response_language":
                name = slots.pop("language_name")
                if name not in LANG:
                    raise ValueError("unknown language")
                slots["language"] = LANG[name]
                slots["language_name"] = name
            if iid == "combination:repeat_prompt":
                positions = [x.start() for x in re.finditer(re.escape(REPEAT_MARKER), prompt)]
                if len(positions) != 1:
                    raise ValueError("repeat marker multiplicity")
                prefix = prompt[:positions[0]].strip()
                if not prefix:
                    raise ValueError("empty repeat prefix")
                slots["prompt_to_repeat"] = prefix
            found.append({"instruction_id": iid, "slots": slots, "start": m.start(), "end": m.end()})
    found.sort(key=lambda x: (x["start"], x["end"], x["instruction_id"]))
    ids = [x["instruction_id"] for x in found]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate instruction family")
    return found

def norm(v: Any) -> Any:
    if hasattr(v, "tolist"):
        return norm(v.tolist())
    if isinstance(v, tuple):
        return [norm(x) for x in v]
    if isinstance(v, list):
        return [norm(x) for x in v]
    if isinstance(v, dict):
        return {str(k): norm(x) for k, x in v.items()}
    return v

def nonnull(v: Any) -> dict[str, Any]:
    if v is None:
        return {}
    return {str(k): norm(x) for k, x in dict(v).items() if x is not None}

def main() -> None:
    p = Path("/tmp/livebench-predecessor.parquet")
    raw = urllib.request.urlopen(URL, timeout=120).read()
    assert len(raw) == BYTES, (len(raw), BYTES)
    assert hashlib.sha256(raw).hexdigest() == SHA256
    p.write_bytes(raw)

    rows = pq.read_table(
        p, columns=["turns", "instruction_id_list", "kwargs", "livebench_release_date"]
    ).to_pylist()
    assert len(rows) == ROWS

    id_exact = kw_exact = all_exact = 0
    exp_total = Counter()
    got_total = Counter()
    missing = Counter()
    extra = Counter()
    kw_mismatch = Counter()
    releases = Counter()

    for row in rows:
        turns = list(row.get("turns") or [])
        assert len(turns) == 1
        prompt = str(turns[0])
        exp_ids = [str(x) for x in (row.get("instruction_id_list") or [])]
        exp_kwargs = list(row.get("kwargs") or [])
        assert len(exp_ids) == len(exp_kwargs)

        got = compile_visible(prompt)
        got_ids = [x["instruction_id"] for x in got]
        ec, gc = Counter(exp_ids), Counter(got_ids)
        exp_total.update(exp_ids)
        got_total.update(got_ids)
        missing.update(ec - gc)
        extra.update(gc - ec)
        ids_ok = ec == gc
        if ids_ok:
            id_exact += 1

        params_ok = ids_ok
        by_id = defaultdict(list)
        for item in got:
            by_id[item["instruction_id"]].append(item)
        if ids_ok:
            for iid, rawkw in zip(exp_ids, exp_kwargs):
                target = nonnull(rawkw)
                candidates = by_id.get(iid) or []
                if len(candidates) != 1:
                    params_ok = False
                    kw_mismatch[iid] += 1
                    continue
                slots = norm(candidates[0]["slots"])
                projection = {k: slots.get(k) for k in target}
                if projection != target:
                    params_ok = False
                    kw_mismatch[iid] += 1
        if params_ok:
            kw_exact += 1
        if ids_ok and params_ok:
            all_exact += 1
        releases[str(row.get("livebench_release_date"))] += 1

    result = {
        "schema": SCHEMA,
        "status": (
            "PASS__200_OF_200_VISIBLE_ID_AND_SCORE_KWARG_RECOVERY"
            if all_exact == ROWS
            else "FAIL_CLOSED__PREDECESSOR_REPLAY_MISMATCH"
        ),
        "bindings": {
            "hf_repository": "livebench/instruction_following",
            "revision": REV,
            "parquet_sha256": SHA256,
            "parquet_bytes": BYTES,
            "brain_v1_git_blob": "e986035ff68b53c0dc7a7eb478f6e3d8882214aa",
            "brain_v2_git_blob": "0e7519f4f2b7d40084effc83a5bef814ee7fd487",
            "brain_audit_git_blob": "6c6f951b7e4d42e86138a94dfce089f6acc77619",
            "implementation": "INDEPENDENT_REIMPLEMENTATION_FROM_PINNED_PUBLIC_DESCRIPTION_GRAMMAR",
        },
        "population": {
            "rows": len(rows),
            "release_histogram": dict(sorted(releases.items())),
            "expected_instruction_instances": sum(exp_total.values()),
            "detected_instruction_instances": sum(got_total.values()),
        },
        "recovery": {
            "id_exact_rows": id_exact,
            "kwargs_exact_rows": kw_exact,
            "all_exact_rows": all_exact,
            "all_exact_fraction": all_exact / len(rows),
        },
        "aggregate_diagnostics": {
            "expected_by_instruction_id": dict(sorted(exp_total.items())),
            "detected_by_instruction_id": dict(sorted(got_total.items())),
            "missing_by_instruction_id": dict(sorted(missing.items())),
            "extra_by_instruction_id": dict(sorted(extra.items())),
            "kwarg_mismatch_by_instruction_id": dict(sorted(kw_mismatch.items())),
        },
        "firewall": {
            "active_2024_11_25_terminal_rows_read": 0,
            "active_terminal_prompt_text_emitted": False,
            "predecessor_prompt_text_emitted": False,
            "verifier_labels_used_only_for_removed_predecessor": True,
        },
        "hard_nonclaims": [
            "PREDECESSOR_REPLAY_DOES_NOT_BY_ITSELF_PROVE_ACTIVE_2024_11_25_BYTE_LEVEL_LINEAGE",
            "NO_ACTIVE_TERMINAL_SCORE_OR_ACCEPTANCE_CREDIT",
        ],
    }
    out = Path("livebench_legacy_predecessor_compiler_replay_sol_v1.json")
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "status": result["status"],
        "rows": len(rows),
        "all_exact_rows": all_exact,
        "missing": sum(missing.values()),
        "extra": sum(extra.values()),
        "kwarg_mismatches": sum(kw_mismatch.values()),
    }, sort_keys=True))
    if all_exact != ROWS:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
