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
from dataclasses import asdict, dataclass
from typing import Any

import requests
from huggingface_hub import HfApi, hf_hub_url

SCHEMA = "PROJECT_BRAIN_SMAUG_MINI_RELEASE_INTERNALIZATION_MANIFEST_V1"
REPO_ID = os.environ.get("MODEL_ID", "abacusai/Smaug-Mini")
REVISION = os.environ.get("MODEL_REVISION", "2750fd9f1e67e004111a53a6d9a39c15fbbd33ef")
TAG = os.environ.get("RELEASE_TAG", "project-brain-smaug-mini-2750fd9-v1")
GH_REPO = os.environ["GITHUB_REPOSITORY"]
GITHUB_SHA = os.environ["GITHUB_SHA"]
CHUNK_BYTES = int(os.environ.get("CHUNK_BYTES", "1800000000"))
WORK = pathlib.Path(os.environ.get("RUNNER_TEMP", ".")) / "smaug-internalize"
MANIFEST_NAME = "PROJECT_BRAIN_SMAUG_MINI_2750FD9_INTERNALIZATION_MANIFEST.json"
RECEIPT_NAME = "PROJECT_BRAIN_SMAUG_MINI_2750FD9_PRODUCER_RECEIPT.json"
MAX_ASSET_BYTES = 2 * 1024 * 1024 * 1024
MAX_ASSETS = 1000


class FailClosed(RuntimeError):
    pass


def run(*args: str, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        check=True,
        text=True,
        capture_output=capture,
    )


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


def ensure_release() -> None:
    probe = subprocess.run(
        ["gh", "release", "view", TAG, "--repo", GH_REPO, "--json", "isDraft,tagName"],
        text=True,
        capture_output=True,
    )
    if probe.returncode == 0:
        state = json.loads(probe.stdout)
        if not state.get("isDraft"):
            raise FailClosed("TARGET_RELEASE_ALREADY_PUBLISHED__RUN_VERIFIER_ONLY")
        return
    run(
        "gh", "release", "create", TAG,
        "--repo", GH_REPO,
        "--target", GITHUB_SHA,
        "--draft",
        "--title", "Project Brain Smaug Mini exact learned-state mirror",
        "--notes",
        (
            "Exact content-addressed mirror of abacusai/Smaug-Mini at revision "
            + REVISION
            + ". Draft until producer asset-set checks pass. Capability credit: zero pending independent verification."
        ),
    )


def upload(path: pathlib.Path) -> None:
    if path.stat().st_size >= MAX_ASSET_BYTES:
        raise FailClosed(f"ASSET_TOO_LARGE:{path.name}:{path.stat().st_size}")
    run("gh", "release", "upload", TAG, str(path), "--repo", GH_REPO, "--clobber")


def sanitize_lfs_sha(entry: Any) -> str | None:
    lfs = obj_value(entry, "lfs")
    value = obj_value(lfs, "sha256")
    if isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{64}", value):
        return value.lower()
    return None


def stream_one(index: int, entry: Any) -> dict[str, Any]:
    filename = obj_value(entry, "rfilename")
    if not isinstance(filename, str) or not filename:
        raise FailClosed(f"INVALID_SOURCE_FILENAME:{index}")
    expected_size = obj_value(entry, "size")
    if expected_size is not None:
        expected_size = int(expected_size)
    source_lfs_sha256 = sanitize_lfs_sha(entry)

    url = hf_hub_url(REPO_ID, filename=filename, revision=REVISION)
    whole = hashlib.sha256()
    total = 0
    chunks: list[dict[str, Any]] = []
    chunk_index = 0
    chunk_path: pathlib.Path | None = None
    chunk_file = None
    chunk_hash = None
    chunk_size = 0

    def open_chunk() -> None:
        nonlocal chunk_path, chunk_file, chunk_hash, chunk_size
        asset_name = f"f{index:04d}_c{chunk_index:04d}.bin"
        chunk_path = WORK / asset_name
        chunk_file = chunk_path.open("wb")
        chunk_hash = hashlib.sha256()
        chunk_size = 0

    def close_upload_chunk() -> None:
        nonlocal chunk_index, chunk_path, chunk_file, chunk_hash, chunk_size
        if chunk_file is None or chunk_path is None or chunk_hash is None:
            return
        chunk_file.close()
        if chunk_size <= 0:
            chunk_path.unlink(missing_ok=True)
            chunk_file = None
            return
        digest = chunk_hash.hexdigest()
        if sha256_file(chunk_path) != digest:
            raise FailClosed(f"LOCAL_CHUNK_REHASH_MISMATCH:{chunk_path.name}")
        upload(chunk_path)
        chunks.append({
            "asset_name": chunk_path.name,
            "bytes": chunk_size,
            "sha256": digest,
            "order": chunk_index,
        })
        chunk_path.unlink()
        chunk_index += 1
        chunk_file = None
        chunk_path = None
        chunk_hash = None
        chunk_size = 0

    with requests.get(url, stream=True, allow_redirects=True, timeout=(30, 300)) as response:
        response.raise_for_status()
        for block in response.iter_content(chunk_size=8 * 1024 * 1024):
            if not block:
                continue
            pos = 0
            while pos < len(block):
                if chunk_file is None:
                    open_chunk()
                assert chunk_file is not None and chunk_hash is not None
                room = CHUNK_BYTES - chunk_size
                take = min(room, len(block) - pos)
                piece = block[pos:pos + take]
                chunk_file.write(piece)
                chunk_hash.update(piece)
                whole.update(piece)
                chunk_size += take
                total += take
                pos += take
                if chunk_size == CHUNK_BYTES:
                    close_upload_chunk()
        close_upload_chunk()

    if expected_size is not None and total != expected_size:
        raise FailClosed(f"SOURCE_SIZE_MISMATCH:{filename}:{total}!={expected_size}")
    whole_digest = whole.hexdigest()
    if source_lfs_sha256 and whole_digest != source_lfs_sha256:
        raise FailClosed(f"SOURCE_LFS_SHA256_MISMATCH:{filename}:{whole_digest}!={source_lfs_sha256}")
    if not chunks and total:
        raise FailClosed(f"NO_CHUNKS_EMITTED:{filename}")
    return {
        "path": filename,
        "source_url": url,
        "bytes": total,
        "sha256": whole_digest,
        "source_lfs_sha256": source_lfs_sha256,
        "chunks": chunks,
    }


def list_remote_assets(release_id: int) -> list[dict[str, Any]]:
    result = run(
        "gh", "api", "--paginate",
        f"repos/{GH_REPO}/releases/{release_id}/assets?per_page=100",
        capture=True,
    )
    # --paginate can return adjacent JSON arrays. Ask gh to flatten with jq.
    flat = subprocess.run(
        [
            "gh", "api", "--paginate",
            f"repos/{GH_REPO}/releases/{release_id}/assets?per_page=100",
            "--jq", ".[] | {name: .name, size: .size, id: .id, digest: .digest}",
        ],
        check=True,
        text=True,
        capture_output=True,
    ).stdout
    out = []
    for line in flat.splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def main() -> int:
    if not (0 < CHUNK_BYTES < MAX_ASSET_BYTES):
        raise FailClosed(f"INVALID_CHUNK_BYTES:{CHUNK_BYTES}")
    shutil.rmtree(WORK, ignore_errors=True)
    WORK.mkdir(parents=True)

    api = HfApi()
    info = api.model_info(REPO_ID, revision=REVISION, files_metadata=True)
    observed_sha = str(obj_value(info, "sha", "") or "")
    if observed_sha != REVISION:
        raise FailClosed(f"REVISION_NOT_EXACT:{observed_sha}!={REVISION}")
    siblings = list(obj_value(info, "siblings", []) or [])
    siblings.sort(key=lambda x: str(obj_value(x, "rfilename", "")))
    if not siblings:
        raise FailClosed("SOURCE_REVISION_EMPTY")

    ensure_release()

    files: list[dict[str, Any]] = []
    for i, entry in enumerate(siblings):
        files.append(stream_one(i, entry))

    data_asset_count = sum(len(x["chunks"]) for x in files)
    if data_asset_count >= MAX_ASSETS - 2:
        raise FailClosed(f"ASSET_COUNT_TOO_HIGH:{data_asset_count}")

    manifest = {
        "schema": SCHEMA,
        "model_id": REPO_ID,
        "revision": REVISION,
        "carrier_repository": GH_REPO,
        "release_tag": TAG,
        "chunk_bytes": CHUNK_BYTES,
        "file_count": len(files),
        "data_asset_count": data_asset_count,
        "total_source_bytes": sum(x["bytes"] for x in files),
        "files": files,
        "license_declared": "apache-2.0",
        "capability_credit_delta": 0,
        "acceptance_credit_delta": 0,
        "hard_nonclaim": "STORED_BYTES_ARE_NOT_CAPABILITY_ACCEPTANCE_UNTIL_THE_EXACT_STORED_INFERENCE_FORM_IS_SEPARATELY_QUALIFIED",
    }
    manifest_path = WORK / MANIFEST_NAME
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest_sha = sha256_file(manifest_path)
    upload(manifest_path)

    release = json.loads(run(
        "gh", "api", f"repos/{GH_REPO}/releases/tags/{TAG}", capture=True
    ).stdout)
    release_id = int(release["id"])
    remote_assets = list_remote_assets(release_id)
    remote_by_name = {a["name"]: a for a in remote_assets}
    expected_data = {
        c["asset_name"]: c["bytes"]
        for f in files
        for c in f["chunks"]
    }
    missing = sorted(set(expected_data) - set(remote_by_name))
    wrong_sizes = sorted(
        name for name, size in expected_data.items()
        if name in remote_by_name and int(remote_by_name[name]["size"]) != int(size)
    )
    if missing or wrong_sizes:
        raise FailClosed(f"REMOTE_ASSET_SET_INVALID:missing={missing[:10]}:wrong_sizes={wrong_sizes[:10]}")
    if MANIFEST_NAME not in remote_by_name:
        raise FailClosed("REMOTE_MANIFEST_MISSING")

    receipt = {
        "schema": "PROJECT_BRAIN_SMAUG_MINI_RELEASE_INTERNALIZATION_PRODUCER_RECEIPT_V1",
        "status": "PRODUCER_PASS__INDEPENDENT_RECONSTRUCTION_REQUIRED",
        "model_id": REPO_ID,
        "revision": REVISION,
        "release_tag": TAG,
        "release_id": release_id,
        "manifest_asset_name": MANIFEST_NAME,
        "manifest_sha256": manifest_sha,
        "file_count": len(files),
        "data_asset_count": data_asset_count,
        "total_source_bytes": manifest["total_source_bytes"],
        "all_lfs_source_hashes_checked_where_available": True,
        "remote_name_size_set_verified": True,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "acceptance_credit_delta": 0,
    }
    receipt_path = WORK / RECEIPT_NAME
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    upload(receipt_path)

    # Re-check producer-required assets after receipt upload, then publish atomically.
    remote_assets = list_remote_assets(release_id)
    remote_names = {a["name"] for a in remote_assets}
    if not set(expected_data).issubset(remote_names) or MANIFEST_NAME not in remote_names or RECEIPT_NAME not in remote_names:
        raise FailClosed("FINAL_REMOTE_ASSET_SET_INVALID")
    run("gh", "release", "edit", TAG, "--repo", GH_REPO, "--draft=false", "--latest=false")

    summary = pathlib.Path(os.environ.get("GITHUB_STEP_SUMMARY", WORK / "summary.md"))
    summary.write_text(
        "## Smaug Mini internalization producer\n"
        f"- revision: \`{REVISION}\`\n"
        f"- files: {len(files)}\n"
        f"- source bytes: {manifest['total_source_bytes']}\n"
        f"- data assets: {data_asset_count}\n"
        f"- release tag: \`{TAG}\`\n"
        "- state: producer pass; independent reconstruction still required\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL_CLOSED: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
