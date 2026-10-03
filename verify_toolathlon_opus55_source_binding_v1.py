from __future__ import annotations

import hashlib
import io
import json
import re
import urllib.request

from pypdf import PdfReader

SOURCE_URL = "https://www-cdn.anthropic.com/fc1b44717c85dc068bc6ba5024219938094694bd/Claude%20Opus%205.5%20System%20Card.pdf"


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def main() -> int:
    request = urllib.request.Request(
        SOURCE_URL,
        headers={"User-Agent": "project-brain-independent-source-verifier/1.0"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        data = response.read()
        content_type = str(response.headers.get("Content-Type") or "")
    if not data.startswith(b"%PDF"):
        raise AssertionError("FIRST_PARTY_SOURCE_NOT_PDF")
    if len(data) < 1_000_000:
        raise AssertionError("FIRST_PARTY_PDF_UNEXPECTEDLY_SMALL")

    pdf_sha256 = hashlib.sha256(data).hexdigest()
    reader = PdfReader(io.BytesIO(data))
    pages: list[tuple[int, str]] = []
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if "Toolathlon" in text:
            pages.append((index, _norm(text)))
    if not pages:
        raise AssertionError("TOOLATHLON_SECTION_NOT_FOUND")

    section = " ".join(text for _, text in pages)
    required_literals = [
        "Toolathlon",
        "Claude Opus 5.5",
        "77.8",
        "82.4",
        "72.2",
        "26.9",
        "108 tasks",
        "three trials",
        "Pass@1",
        "more than 600 tools",
        "32 applications",
    ]
    missing = [literal for literal in required_literals if literal not in section]
    if missing:
        raise AssertionError("MISSING_FIRST_PARTY_LITERALS:" + ",".join(missing))

    # Load-bearing semantic boundary: the first-party Toolathlon reporting binds
    # execution success (Pass@1/Pass@3/Pass^3) and turn count. It does not
    # publish a separate Opus valid_route_top1 score. Do not manufacture one.
    toolathlon_metric_literals = {
        "pass_at_1": "77.8",
        "pass_at_3": "82.4",
        "pass_cubed": "72.2",
        "avg_turns": "26.9",
    }

    verdict = {
        "schema": "PROJECT_BRAIN_OPUS55_TOOLATHLON_SOURCE_BINDING_PUBLIC_VERDICT_V1",
        "source_url": SOURCE_URL,
        "source_owner": "Anthropic",
        "source_kind": "FIRST_PARTY_SYSTEM_CARD_PDF",
        "pdf_sha256": pdf_sha256,
        "pdf_bytes": len(data),
        "pdf_pages": len(reader.pages),
        "toolathlon_pages": [page for page, _ in pages],
        "facts": {
            "benchmark": "Toolathlon-Verified",
            "task_count": 108,
            "opus55_pass_at_1_percent": 77.8,
            "opus55_pass_at_3_percent": 82.4,
            "opus55_pass_cubed_percent": 72.2,
            "opus55_avg_assistant_turns": 26.9,
            "trial_count": 3,
            "tool_count_lower_bound": 600,
            "application_count": 32,
        },
        "published_toolathlon_metrics_bound": toolathlon_metric_literals,
        "valid_route_top1_separately_published_by_this_source": False,
        "claim_boundary": "THIS_RECEIPT_BINDS_OPUS55_TOOLATHLON_EXECUTION_METRICS_ONLY__IT_DOES_NOT_BIND_A_SEPARATE_VALID_ROUTE_TOP1_COMPARATOR",
        "tool_discovery_acceptance_granted": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "incremental_spend_usd": 0,
    }
    print(json.dumps(verdict, indent=2, sort_keys=True))
    with open("OPUS55_TOOLATHLON_SOURCE_BINDING_PUBLIC_VERDICT_V1.json", "w", encoding="utf-8") as f:
        json.dump(verdict, f, indent=2, sort_keys=True)
        f.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
