#!/usr/bin/env python3
from __future__ import annotations

import hashlib, json, re, urllib.request
from pathlib import Path
from collections import Counter
import pyarrow.parquet as pq

HF_URL = "https://huggingface.co/datasets/livebench/instruction_following/resolve/0868379c4b5cf62aeacaf8be4f08fced815c81bb/data/test-00000-of-00001.parquet"
HF_SHA256 = "a9bb97bbaf8788142c310bcb33d50e2f6f5df8cbd8b8c3db677816b06f0f4f25"
HF_BYTES = 537024
IFBENCH_URL = "https://raw.githubusercontent.com/allenai/IFBench/1c40f0c10d9b5c5c2f10a175a28007ebb64f7f4d/data/IFBench_test.jsonl"
IFBENCH_BLOB = "a8e343ed928d8b4e649b9dba651fed7757ccacc3"

RELEASES = {
    "2024-06-24","2024-07-26","2024-08-31","2024-11-25","2025-04-02",
    "2025-04-25","2025-05-30","2025-11-25","2025-12-23","2026-01-08","2026-06-25",
}
TARGET_RELEASE = "2026-06-25"

def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent":"project-brain-independent-verifier"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read()

def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def canon_scalar(v):
    if isinstance(v, bool):
        return ("bool", str(v))
    if isinstance(v, int):
        return ("int", str(v))
    if isinstance(v, float) and v.is_integer():
        return ("int", str(int(v)))
    s = str(v)
    if re.fullmatch(r"[+-]?\d+", s):
        return ("int", str(int(s)))
    return ("str", s)

def main() -> int:
    hf = fetch(HF_URL)
    assert len(hf) == HF_BYTES, len(hf)
    assert hashlib.sha256(hf).hexdigest() == HF_SHA256
    Path("/tmp/livebench_if.parquet").write_bytes(hf)

    raw = fetch(IFBENCH_URL)
    assert git_blob_sha(raw) == IFBENCH_BLOB
    public = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    assert len(public) == 300
    public_keys = [row.get("key") for row in public]
    assert all(k is not None for k in public_keys)
    assert len(public_keys) == len({canon_scalar(k) for k in public_keys})

    # Metadata-only terminal/public-population read. No turns, prompts, kwargs, or instruction text.
    cols = ["question_id","task","livebench_release_date","livebench_removal_date"]
    table = pq.read_table("/tmp/livebench_if.parquet", columns=cols)
    rows = table.to_pylist()
    assert len(rows) == 400
    active = []
    for r in rows:
        rd = r["livebench_release_date"]
        rd = rd.strftime("%Y-%m-%d") if hasattr(rd, "strftime") else str(rd)
        rem = r["livebench_removal_date"] or ""
        if rd in RELEASES and (rem == "" or rem > TARGET_RELEASE):
            active.append(r)
    assert len(active) == 200
    assert Counter(r["task"] for r in active) == {
        "paraphrase":50,"simplify":50,"story_generation":50,"summarize":50
    }

    active_ids = [r["question_id"] for r in active]
    assert len(active_ids) == len({canon_scalar(x) for x in active_ids})

    pk = {canon_scalar(k) for k in public_keys}
    aid = {canon_scalar(x) for x in active_ids}
    exact_intersection = len(pk & aid)

    # Structural-only transforms, declared before observing values.
    def numeric_tail(v):
        s = str(v)
        m = re.search(r"(\d+)$", s)
        return ("int", str(int(m.group(1)))) if m else None

    active_tail = [numeric_tail(x) for x in active_ids]
    tail_set = {x for x in active_tail if x is not None}
    tail_intersection = len(pk & tail_set)

    # Shape summaries reveal no IDs or prompt content.
    def shape(v):
        s = str(v)
        s = re.sub(r"\d", "#", s)
        s = re.sub(r"[A-Za-z]", "A", s)
        return s[:80]

    summary = {
        "schema":"PROJECT_BRAIN_LIVEBENCH_PUBLIC_ROW_ID_BINDING_AUDIT_V1",
        "status":"PASS_AUDIT_COMPLETED",
        "hf_sha256":HF_SHA256,
        "ifbench_git_blob_sha":IFBENCH_BLOB,
        "hf_rows":len(rows),
        "active_hf_rows":len(active),
        "public_ifbench_rows":len(public),
        "active_question_id_type_counts":dict(Counter(type(x).__name__ for x in active_ids)),
        "public_key_type_counts":dict(Counter(type(x).__name__ for x in public_keys)),
        "active_question_id_shape_counts":dict(Counter(shape(x) for x in active_ids)),
        "public_key_shape_counts":dict(Counter(shape(x) for x in public_keys)),
        "exact_canonical_id_intersection_count":exact_intersection,
        "exact_canonical_active_subset_of_public_keys":aid <= pk,
        "numeric_tail_intersection_count":tail_intersection,
        "numeric_tail_active_subset_of_public_keys":len(tail_set)==len(aid) and tail_set <= pk,
        "prompts_or_turns_loaded":False,
        "kwargs_loaded":False,
        "instruction_text_loaded":False,
        "acceptance_credit_delta":0,
    }
    Path("livebench_public_row_id_binding_audit_receipt.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
