#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

H100_MAX_BYTES = 100_000_000
LFS_PREFIX = b"version https://git-lfs.github.com/spec/v1"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def record(path: Path, root: Path) -> dict:
    data_head = path.read_bytes()[:128]
    if data_head.startswith(LFS_PREFIX):
        raise RuntimeError(f"LFS_POINTER_NOT_MATERIALIZED:{path.relative_to(root)}")
    return {
        "path": str(path.relative_to(root)),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--upstream-commit", required=True)
    ap.add_argument("--out", default="shadow250m_byte_audit_v1.json")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    body = root / "deployment" / "shadow250m_instruct.shdw"
    vocab = root / "deployment" / "fp131072.npy"
    tokenizer_dir = root / "tokenizer"

    for path in (body, vocab, tokenizer_dir):
        if not path.exists():
            raise SystemExit(f"MISSING_REQUIRED_ARTIFACT:{path}")

    tokenizer_files = sorted(p for p in tokenizer_dir.rglob("*") if p.is_file())
    if not tokenizer_files:
        raise SystemExit("TOKENIZER_FILES_MISSING")

    body_rec = record(body, root)
    vocab_rec = record(vocab, root)
    tok_recs = [record(p, root) for p in tokenizer_files]

    persistent = body_rec["bytes"] + vocab_rec["bytes"] + sum(x["bytes"] for x in tok_recs)
    result = {
        "schema": "PROJECT_BRAIN_H100_SHADOW250M_BYTE_AUDIT_V1",
        "status": "PASS_H100_PERSISTENT_ARTIFACT_BYTE_GATE" if persistent <= H100_MAX_BYTES else "FAIL_H100_PERSISTENT_ARTIFACT_BYTE_GATE",
        "upstream": {
            "repository": "QLNI/SHADOW-250M-Instruct",
            "commit": args.upstream_commit,
        },
        "accounting_policy": {
            "h100_max_bytes_inclusive": H100_MAX_BYTES,
            "count_model_body": True,
            "count_binary_vocabulary_even_if_declared_nontrainable": True,
            "count_entire_tokenizer_directory_conservatively": True,
            "exclude_runtime_executables_and_source_code_from_learned_state": True,
            "reason": "H100 counts persistent semantic/learned representation; non-semantic executable machinery is measured separately.",
        },
        "artifacts": {
            "model_body": body_rec,
            "binary_vocabulary": vocab_rec,
            "tokenizer_files": tok_recs,
        },
        "persistent_semantic_bytes": persistent,
        "remaining_h100_bytes": H100_MAX_BYTES - persistent,
        "under_h100": persistent <= H100_MAX_BYTES,
        "execution_performed": False,
        "third_party_binary_executed": False,
        "capability_test_performed": False,
        "hard_nonclaims": [
            "BYTE_FIT_DOES_NOT_PROVE_CAPABILITY",
            "NO_SHADOW_BENCHMARK_CLAIM_IS_INDEPENDENTLY_VERIFIED_HERE",
            "NO_RUNTIME_SECURITY_CLAIM",
            "NO_H100_TERMINAL_OR_ACCEPTANCE_CREDIT",
        ],
        "accounting": {
            "incremental_spend_usd": 0,
            "terminal_cases_consumed": 0,
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        },
    }
    Path(args.out).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "status": result["status"],
        "persistent_semantic_bytes": persistent,
        "remaining_h100_bytes": result["remaining_h100_bytes"],
        "tokenizer_file_count": len(tok_recs),
    }, indent=2))
    if not result["under_h100"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
