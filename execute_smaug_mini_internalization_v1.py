#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
import sys
import urllib.parse
import urllib.request

HF_REPO = "abacusai/Smaug-Mini"
HF_REVISION = "2750fd9f1e67e004111a53a6d9a39c15fbbd33ef"
CARRIER_REPO = "moxnixmdj/verification-capsule-runner"
RELEASE_TAG = "project-brain-smaug-mini-2750fd9-v1"
CHUNK_BYTES = 1_800_000_000
BUF_BYTES = 8 * 1024 * 1024
MANIFEST_NAME = "project-brain-smaug-mini-2750fd9-manifest-v1.json"
RECEIPT_NAME = "project-brain-smaug-mini-2750fd9-producer-receipt-v1.json"

def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    p = subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and p.returncode != 0:
        raise RuntimeError(f"command failed {args!r}: {p.stderr[-4000:]}")
    return p

def fetch_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "ProjectBrain-Smaug-Internalizer/1"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))

def hf_model_info():
    url = f"https://huggingface.co/api/models/{HF_REPO}/revision/{HF_REVISION}?blobs=true"
    data = fetch_json(url)
    siblings = data.get("siblings")
    if not isinstance(siblings, list) or not siblings:
        raise RuntimeError("HF_SIBLINGS_MISSING")
    return data, siblings

def ensure_release():
    p = run("gh", "release", "view", RELEASE_TAG, "--repo", CARRIER_REPO, check=False)
    if p.returncode == 0:
        return
    run(
        "gh", "release", "create", RELEASE_TAG,
        "--repo", CARRIER_REPO,
        "--draft",
        "--target", "main",
        "--title", f"Project Brain Smaug-Mini {HF_REVISION[:9]} learned-state carrier",
        "--notes", (
            "Draft zero-spend content-addressed carrier for Project Brain. "
            "Do not publish as capability credit. Source: "
            f"https://huggingface.co/{HF_REPO}/tree/{HF_REVISION}"
        ),
    )

def release_assets():
    raw = run(
        "gh", "api", f"repos/{CARRIER_REPO}/releases/tags/{RELEASE_TAG}",
        "--jq", ".assets[] | [.id,.name,.size,(.digest // \"\")] | @tsv"
    ).stdout
    out = {}
    for line in raw.splitlines():
        if not line.strip():
            continue
        aid, name, size, digest = line.split("\t", 3)
        out[name] = {"id": int(aid), "size": int(size), "digest": digest}
    return out

def delete_asset(asset_id: int):
    run("gh", "api", "-X", "DELETE", f"repos/{CARRIER_REPO}/releases/assets/{asset_id}")

def upload_asset(path: pathlib.Path):
    run("gh", "release", "upload", RELEASE_TAG, str(path), "--repo", CARRIER_REPO)

def safe_asset_name(file_index: int, part_index: int, source_path: str) -> str:
    token = hashlib.sha256(source_path.encode("utf-8")).hexdigest()[:16]
    return f"smaug-{file_index:04d}-part-{part_index:04d}-{token}.bin"

def expected_lfs_sha(sibling: dict) -> str | None:
    lfs = sibling.get("lfs")
    if isinstance(lfs, dict):
        sha = str(lfs.get("sha256") or "").lower()
        if len(sha) == 64:
            return sha
    return None

def expected_size(sibling: dict) -> int | None:
    for value in (
        (sibling.get("lfs") or {}).get("size") if isinstance(sibling.get("lfs"), dict) else None,
        sibling.get("size"),
    ):
        if isinstance(value, int) and value >= 0:
            return value
    return None

def open_source(path: str):
    quoted = urllib.parse.quote(path, safe="/")
    url = f"https://huggingface.co/{HF_REPO}/resolve/{HF_REVISION}/{quoted}?download=true"
    req = urllib.request.Request(url, headers={"User-Agent": "ProjectBrain-Smaug-Internalizer/1"})
    return urllib.request.urlopen(req, timeout=300)

def remote_asset_valid(asset: dict, size: int, sha256: str) -> bool:
    if asset.get("size") != size:
        return False
    digest = str(asset.get("digest") or "")
    if digest:
        return digest.lower() == f"sha256:{sha256}".lower()
    return False

def upload_one_file(file_index: int, sibling: dict, work: pathlib.Path):
    source_path = sibling.get("rfilename")
    if not isinstance(source_path, str) or not source_path:
        raise RuntimeError("HF_PATH_INVALID")
    exp_size = expected_size(sibling)
    exp_lfs = expected_lfs_sha(sibling)

    whole = hashlib.sha256()
    total = 0
    part_index = 0
    parts = []

    with open_source(source_path) as response:
        while True:
            part_path = work / safe_asset_name(file_index, part_index, source_path)
            part_hash = hashlib.sha256()
            written = 0
            with part_path.open("wb") as out:
                while written < CHUNK_BYTES:
                    block = response.read(min(BUF_BYTES, CHUNK_BYTES - written))
                    if not block:
                        break
                    out.write(block)
                    whole.update(block)
                    part_hash.update(block)
                    written += len(block)
                    total += len(block)

            if written == 0:
                part_path.unlink(missing_ok=True)
                break

            part_sha = part_hash.hexdigest()
            assets = release_assets()
            existing = assets.get(part_path.name)
            if existing is not None and not remote_asset_valid(existing, written, part_sha):
                delete_asset(existing["id"])
                existing = None
            if existing is None:
                upload_asset(part_path)

            parts.append({
                "asset": part_path.name,
                "bytes": written,
                "sha256": part_sha,
            })
            part_path.unlink(missing_ok=True)
            part_index += 1

            if written < CHUNK_BYTES:
                break

    whole_sha = whole.hexdigest()
    if exp_size is not None and total != exp_size:
        raise RuntimeError(f"SIZE_MISMATCH:{source_path}:{total}:{exp_size}")
    if exp_lfs is not None and whole_sha != exp_lfs:
        raise RuntimeError(f"LFS_SHA256_MISMATCH:{source_path}:{whole_sha}:{exp_lfs}")

    return {
        "path": source_path,
        "bytes": total,
        "sha256": whole_sha,
        "expected_lfs_sha256": exp_lfs,
        "parts": parts,
    }

def main() -> int:
    if not os.environ.get("GH_TOKEN"):
        raise RuntimeError("GH_TOKEN_REQUIRED")
    if run("gh", "repo", "view", CARRIER_REPO, "--json", "visibility", "--jq", ".visibility").stdout.strip().upper() != "PUBLIC":
        raise RuntimeError("CARRIER_REPO_MUST_BE_PUBLIC")

    ensure_release()
    info, siblings = hf_model_info()

    source_sha = str(info.get("sha") or "")
    if source_sha and source_sha != HF_REVISION:
        raise RuntimeError(f"HF_REVISION_MISMATCH:{source_sha}")

    work = pathlib.Path("_smaug_stream")
    work.mkdir(exist_ok=True)

    files = []
    for i, sibling in enumerate(sorted(siblings, key=lambda x: str(x.get("rfilename") or ""))):
        files.append(upload_one_file(i, sibling, work))

    manifest = {
        "schema": "PROJECT_BRAIN_SMAUG_MINI_RELEASE_ASSET_MANIFEST_V1",
        "status": "PRODUCER_COMPLETE__DRAFT_RELEASE__INDEPENDENT_RECONSTRUCTION_REQUIRED__ZERO_CREDIT",
        "source": {
            "repo_id": HF_REPO,
            "revision": HF_REVISION,
            "observed_api_sha": source_sha or None,
        },
        "carrier": {
            "repository": CARRIER_REPO,
            "release_tag": RELEASE_TAG,
            "draft_required": True,
        },
        "chunk_bytes": CHUNK_BYTES,
        "files": files,
        "total_source_bytes": sum(x["bytes"] for x in files),
        "source_file_count": len(files),
        "release_asset_count_excluding_manifest": sum(len(x["parts"]) for x in files),
        "accounting": {
            "incremental_spend_usd": 0,
            "terminal_cases_consumed": 0,
            "acceptance_credit_delta": 0,
        },
        "hard_nonclaims": [
            "STORAGE_COMPLETION_IS_NOT_CAPABILITY_ACCEPTANCE",
            "NO_TERMINAL_CASES_USED",
            "NO_QUANTIZED_VARIANT_INHERITS_SCORE",
            "INDEPENDENT_RECONSTRUCTION_REQUIRED_BEFORE_INTERNALIZATION_CLOSURE",
        ],
    }

    manifest_path = pathlib.Path(MANIFEST_NAME)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    run("gh", "release", "upload", RELEASE_TAG, str(manifest_path), "--repo", CARRIER_REPO, "--clobber")

    assets = release_assets()
    expected = {p["asset"]: p for f in files for p in f["parts"]}
    missing = sorted(set(expected) - set(assets))
    wrong_size = sorted(
        name for name, rec in expected.items()
        if name in assets and assets[name]["size"] != rec["bytes"]
    )
    if missing or wrong_size:
        raise RuntimeError(f"REMOTE_ASSET_SET_INVALID:missing={missing}:wrong_size={wrong_size}")

    receipt = {
        "schema": "PROJECT_BRAIN_SMAUG_MINI_RELEASE_ASSET_PRODUCER_RECEIPT_V1",
        "status": "PASS__DRAFT_RELEASE_ASSET_NAME_SIZE_SET_VERIFIED__INDEPENDENT_RECONSTRUCTION_REQUIRED",
        "source_revision": HF_REVISION,
        "release_tag": RELEASE_TAG,
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "source_file_count": len(files),
        "source_bytes": manifest["total_source_bytes"],
        "asset_count_excluding_manifest": len(expected),
        "incremental_spend_usd": 0,
        "terminal_cases_consumed": 0,
        "acceptance_credit_delta": 0,
    }
    pathlib.Path(RECEIPT_NAME).write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
