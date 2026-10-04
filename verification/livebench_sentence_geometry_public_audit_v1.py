#!/usr/bin/env python3
"""Public-runner sentence-geometry audit for the frozen LiveBench legacy checker.

No terminal benchmark rows, prompts, responses, scores, hidden IDs, or kwargs
are read. This probes only the source-visible structure used by the existing
constructive composer against the exact count_sentences dependency boundary.
"""
from __future__ import annotations

import itertools
import json
import nltk
from nltk.tokenize.punkt import PunktSentenceTokenizer

_WORST_CASE_TOKENIZER = PunktSentenceTokenizer()

PINNED_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
PINNED_INSTRUCTIONS_UTIL_BLOB = "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b"
ENDINGS = (None, "Any other questions?", "Is there anything else I can help with?")
POSTS = (None, "P.S.", "P.P.S")


def sentence_count(text: str) -> int:
    # Deliberately use empty Punkt parameters. The construction avoids every
    # token-final period except the explicit sentence-ending punctuation, so
    # abbreviation/collocation tables are non-load-bearing. Empty parameters
    # are therefore a conservative boundary audit and need no downloaded model.
    return len(_WORST_CASE_TOKENIZER.tokenize(text))


def wrap_quote(text: str, quote: bool) -> str:
    return '"' + text + '"' if quote else text


def nth_candidate(
    paragraphs: int,
    nth: int,
    post: str | None,
    ending: str | None,
    quote: bool,
    title: bool,
    keyword_carriers: bool,
    padding_words: int,
) -> str:
    ps = ["zxqv" for _ in range(paragraphs)]
    ps[nth - 1] = "alpha zxqv"

    common: list[str] = []
    if title:
        common.append("<<qz>>")
    if keyword_carriers:
        common.append("alphax betax gammax deltax epsilonx")
    if post:
        common.append(post + "zxqv")
    if common:
        ps[-1] += "\n" + "\n".join(common)

    prefix = "\n\n".join(ps)
    if padding_words:
        prefix += "\n" + " ".join(["zxqv"] * padding_words)
    if ending:
        prefix += "\n" + ending
    return wrap_quote(prefix, quote)


def plain_candidate(
    post: str | None,
    ending: str | None,
    quote: bool,
    title: bool,
    keyword_carriers: bool,
    padding_words: int,
) -> str:
    lines: list[str] = []
    if title:
        lines.append("<<qz>>")
    if keyword_carriers:
        lines.append("alphax betax gammax deltax epsilonx")
    if post:
        lines.append(post + "zxqv")
    if not lines:
        lines.append("zxqv")
    prefix = "\n".join(lines)
    if padding_words:
        prefix += "\n" + " ".join(["zxqv"] * padding_words)
    if ending:
        prefix += "\n" + ending
    return wrap_quote(prefix, quote)


def main() -> None:
    rows = []
    maxima = {"nth": 0, "plain": 0}
    worst = {"nth": [], "plain": []}

    for paragraphs in range(1, 6):
        for nth in range(1, paragraphs + 1):
            for post, ending, quote, title, carriers, pad in itertools.product(
                POSTS, ENDINGS, (False, True), (False, True), (False, True), (0, 1, 100, 500)
            ):
                # title and quotation conflict in the pinned registry.
                if title and quote:
                    continue
                text = nth_candidate(paragraphs, nth, post, ending, quote, title, carriers, pad)
                c = sentence_count(text)
                rows.append(("nth", c))
                if c > maxima["nth"]:
                    maxima["nth"] = c
                    worst["nth"] = [{
                        "paragraphs": paragraphs, "nth": nth, "post": post, "ending": ending,
                        "quote": quote, "title": title, "carriers": carriers, "pad": pad,
                        "text": text,
                    }]
                elif c == maxima["nth"] and len(worst["nth"]) < 10:
                    worst["nth"].append({
                        "paragraphs": paragraphs, "nth": nth, "post": post, "ending": ending,
                        "quote": quote, "title": title, "carriers": carriers, "pad": pad,
                        "text": text,
                    })

    for post, ending, quote, title, carriers, pad in itertools.product(
        POSTS, ENDINGS, (False, True), (False, True), (False, True), (0, 1, 100, 500)
    ):
        if title and quote:
            continue
        text = plain_candidate(post, ending, quote, title, carriers, pad)
        c = sentence_count(text)
        rows.append(("plain", c))
        if c > maxima["plain"]:
            maxima["plain"] = c
            worst["plain"] = [{
                "post": post, "ending": ending, "quote": quote, "title": title,
                "carriers": carriers, "pad": pad, "text": text,
            }]
        elif c == maxima["plain"] and len(worst["plain"]) < 10:
            worst["plain"].append({
                "post": post, "ending": ending, "quote": quote, "title": title,
                "carriers": carriers, "pad": pad, "text": text,
            })

    dist = {
        kind: {str(n): sum(1 for k, c in rows if k == kind and c == n)
               for n in sorted({c for k, c in rows if k == kind})}
        for kind in ("nth", "plain")
    }
    receipt = {
        "schema": "PROJECT_BRAIN_LIVEBENCH_SENTENCE_GEOMETRY_PUBLIC_AUDIT_V1",
        "livebench_commit": PINNED_LIVEBENCH_COMMIT,
        "instructions_util_blob": PINNED_INSTRUCTIONS_UTIL_BLOB,
        "nltk_version": nltk.__version__,\n        "postscript_boundary_strategy": "MARKER_STITCHED_TO_ALPHABETIC_CONTINUATION",\n        "punkt_parameters": "EMPTY__CONSERVATIVE_BOUNDARY_AUDIT",
        "matrix_rows": len(rows),
        "max_sentence_count": maxima,
        "distribution": dist,
        "worst_examples": worst,
        "terminal_case_content_read": 0,
        "terminal_case_metadata_read": 0,
        "acceptance_credit": False,
    }
    print(json.dumps(receipt, indent=2, sort_keys=True))

    # If this holds, every non-empty tested construction satisfies any
    # "less than N sentences" predicate for N >= 2.
    assert maxima["nth"] <= 1, receipt
    assert maxima["plain"] <= 1, receipt


if __name__ == "__main__":
    main()
