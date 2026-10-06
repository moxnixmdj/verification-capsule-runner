#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
from typing import Any

from huggingface_hub import HfApi

MODEL_ID = os.environ.get("MODEL_ID", "abacusai/Smaug-Mini")
REVISION = os.environ.get("MODEL_REVISION", "2750fd9f1e67e004111a53a6d9a39c15fbbd33ef")
TAG = os.environ.get("RELEASE_TAG", "project-brain-smaug-mini-2750fd9-v1")
GH_REPO = os.environ["GITHUB_REPOSITORY"]
WORK = pathlib.Path(os.environ.get("RUNNER_TEMP", ".")) / "smaug-verify"
MANIFEST_NAME = "PROJECT_BRAIN_SMAUG_MINI_2750FD9_INTERNALIZATION_MANIFEST.json"
VERIFY_RECEIPT_NAME = "PROJECT_BRAIN_SMAUG_MINI_2750FD9_INDEPENDENT_VERIFY_RECEIPT.json"


class FailClosed(RuntimeError):
    pass


def run(*args: str, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(list(args), check=True, text=True, capture_output=capture)


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def obj_value(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def lfs_sha(entry: Any) -> str | None:
    lfs = obj_value(entry, "lfs")
    value = obj_value(lfs, "sha256")
    if isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{64}", value):
        return value.lower()
    return None


def download_asset(name: str) -> pathlib.Path:
    dest = WORK / name
    dest.unlink(missing_ok=True)
    run("gh", "release", "download", TAG, "--repo", GH_REPO, "--pattern", name, "--dir", str(WORK))
    if not dest.is_file():
        raise FailClosed(f"ASSET_DOWNLOAD_MISSING:{name}")
    return dest


def public_source_index() -> dict[str, dict[str, Any]]:
    info = HfApi().model_info(MODEL_ID, revision=REVISION, files_metadata=True)
    observed_sha = str(obj_value(info, "sha", "") or "")
    if observed_sha != REVISION:
        raise FailClosed(f"PUBLIC_REVISION_MISMATCH:{observed_sha}!={REVISION}")
    rows: dict[str, dict[str, Any]] = {}
    for entry in list(obj_value(info, "siblings", []) or []):
        path = obj_value(entry, "rfilename")
        if not isinstance(path, str) or not path:
            raise FailClosed("PUBLIC_SOURCE_FILENAME_INVALID")
        rows[path] = {
            "size": None if obj_value(entry, "size") is None else int(obj_value(entry, "size")),
            "lfs_sha256": lfs_sha(entry),
        }
    return rows


def main() -> int:
    shutil.rmtree(WORK, ignore_errors=True)
    WORK.mkdir(parents=True)

    release = json.loads(run(
        "gh", "release", "view", TAG, "--repo", GH_REPO,
        "--json", "isDraft,tagName,url",
        capture=True,
    ).stdout)
    if release.get("isDraft"):
        raise FailClosed("RELEASE_STILL_DRAFT")
    if release.get("tagName") != TAG:
        raise FailClosed("RELEASE_TAG_MISMATCH")

    manifest_path = download_asset(MANIFEST_NAME)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "PROJECT_BRAIN_SMAUG_MINI_RELEASE_INTERNALIZATION_MANIFEST_V1":
        raise FailClosed("MANIFEST_SCHEMA_INVALID")
    if manifest.get("model_id") != MODEL_ID or manifest.get("revision") != REVISION:
        raise FailClosed("MANIFEST_SOURCE_IDENTITY_MISMATCH")
    if manifest.get("carrier_repository") != GH_REPO or manifest.get("release_tag") != TAG:
        raise FailClosed("MANIFEST_CARRIER_IDENTITY_MISMATCH")

    public = public_source_index()
    manifest_files = manifest.get("files")
    if not isinstance(manifest_files, list) or not manifest_files:
        raise FailClosed("MANIFEST_FILES_INVALID")
    manifest_paths = [row.get("path") for row in manifest_files]
    if len(manifest_paths) != len(set(manifest_paths)):
        raise FailClosed("MANIFEST_DUPLICATE_SOURCE_PATH")
    if set(manifest_paths) != set(public):
        missing = sorted(set(public) - set(manifest_paths))
        extra = sorted(set(manifest_paths) - set(public))
        raise FailClosed(f"MANIFEST_PUBLIC_FILESET_MISMATCH:missing={missing[:10]}:extra={extra[:10]}")

    total_bytes = 0
    total_assets = 0
    verified_files = 0
    for row in manifest_files:
        path = row["path"]
        expected_file_size = int(row["bytes"])
        expected_file_sha = str(row["sha256"]).lower()
        chunks = row.get("chunks")
        if not isinstance(chunks, list) or (expected_file_size > 0 and not chunks):
            raise FailClosed(f"CHUNK_LIST_INVALID:{path}")
        if [int(c["order"]) for c in chunks] != list(range(len(chunks))):
            raise FailClosed(f"CHUNK_ORDER_INVALID:{path}")

        whole = hashlib.sha256()
        observed_file_size = 0
        for chunk in chunks:
            name = str(chunk["asset_name"])
            expected_chunk_size = int(chunk["bytes"])
            expected_chunk_sha = str(chunk["sha256"]).lower()
            asset = download_asset(name)
            observed_size = asset.stat().st_size
            if observed_size != expected_chunk_size:
                raise FailClosed(f"CHUNK_SIZE_MISMATCH:{name}:{observed_size}!={expected_chunk_size}")
            observed_sha = sha256_file(asset)
            if observed_sha != expected_chunk_sha:
                raise FailClosed(f"CHUNK_SHA256_MISMATCH:{name}:{observed_sha}!={expected_chunk_sha}")
            with asset.open("rb") as f:
                for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
                    whole.update(block)
                    observed_file_size += len(block)
            asset.unlink()
            total_assets += 1

        observed_file_sha = whole.hexdigest()
        if observed_file_size != expected_file_size:
            raise FailClosed(f"FILE_SIZE_MISMATCH:{path}:{observed_file_size}!={expected_file_size}")
        if observed_file_sha != expected_file_sha:
            raise FailClosed(f"FILE_SHA256_MISMATCH:{path}:{observed_file_sha}!={expected_file_sha}")

        source = public[path]
        if source["size"] is not None and observed_file_size != source["size"]:
            raise FailClosed(f"PUBLIC_SIZE_MISMATCH:{path}:{observed_file_size}!={source['size']}")
        if source["lfs_sha256"] and observed_file_sha != source["lfs_sha256"]:
            raise FailClosed(f"PUBLIC_LFS_SHA256_MISMATCH:{path}:{observed_file_sha}!={source['lfs_sha256']}")
        manifest_lfs = row.get("source_lfs_sha256")
        if manifest_lfs != source["lfs_sha256"]:
            raise FailClosed(f"MANIFEST_PUBLIC_LFS_BINDING_MISMATCH:{path}")
        total_bytes += observed_file_size
        verified_files += 1

    if verified_files != int(manifest["file_count"]):
        raise FailClosed("VERIFIED_FILE_COUNT_MISMATCH")
    if total_assets != int(manifest["data_asset_count"]):
        raise FailClosed("VERIFIED_ASSET_COUNT_MISMATCH")
    if total_bytes != int(manifest["total_source_bytes"]):
        raise FailClosed("VERIFIED_TOTAL_BYTES_MISMATCH")

    receipt = {
        "schema": "PROJECT_BRAIN_SMAUG_MINI_RELEASE_INDEPENDENT_RECONSTRUCTION_RECEIPT_V1",
        "status": "PASS",
        "model_id": MODEL_ID,
        "revision": REVISION,
        "carrier_repository": GH_REPO,
        "release_tag": TAG,
        "release_url": release.get("url"),
        "manifest_sha256": sha256_file(manifest_path),
        "verified_file_count": verified_files,
        "verified_data_asset_count": total_assets,
        "verified_total_source_bytes": total_bytes,
        "public_revision_exact": True,
        "public_file_set_exact": True,
        "chunk_sha256_exact": True,
        "concatenated_file_sha256_exact": True,
        "public_lfs_sha256_exact_where_available": True,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "acceptance_credit_delta": 0,
        "hard_nonclaim": "INDEPENDENT_BYTE_OWNERSHIP_VERIFICATION_DOES_NOT_BY_ITSELF_PROVE_THE_STORED_EXECUTION_FORM_RETains_THE_PUBLISHED_LIVEBENCH_SCORE",
    }
    receipt_path = WORK / VERIFY_RECEIPT_NAME
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    run("gh", "release", "upload", TAG, str(receipt_path), "--repo", GH_REPO, "--clobber")

    summary = pathlib.Path(os.environ.get("GITHUB_STEP_SUMMARY", WORK / "summary.md"))
    summary.write_text(
        "## Smaug Mini independent reconstruction\n"
        f"- revision: {REVISION}\n"
        f"- verified files: {verified_files}\n"
        f"- verified bytes: {total_bytes}\n"
        f"- verified data assets: {total_assets}\n"
        "- state: PASS for exact stored bytes; semantic execution-form qualification remains separate\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL_CLOSED: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
