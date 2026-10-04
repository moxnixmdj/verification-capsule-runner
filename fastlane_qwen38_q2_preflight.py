#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import platform
import urllib.request
from pathlib import Path

REPO_ID = "unsloth/Qwen3.8-27B-GGUF"
REVISION = "313447f"
FILENAME = "Qwen3.8-27B-UD-Q2_K_XL.gguf"
EXPECTED_BYTES = 9_828_981_664
EXPECTED_SHA256 = "fd4730dd8aad070517978752b63d530aeb1740d2283cab9fa24f1e404032ddb0"
MIN_DISK_MARGIN_BYTES = 2_000_000_000
MIN_RAM_TOTAL_BYTES = 15_000_000_000
MIN_RAM_AVAILABLE_BYTES = 10_000_000_000


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "project-brain-qwen38-q2-preflight/1"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def head(url: str) -> dict[str, str]:
    req = urllib.request.Request(
        url,
        method="HEAD",
        headers={"User-Agent": "project-brain-qwen38-q2-preflight/1"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return {k.lower(): v for k, v in r.headers.items()}


def meminfo() -> dict[str, int]:
    out: dict[str, int] = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        if ":" not in line:
            continue
        key, raw = line.split(":", 1)
        fields = raw.strip().split()
        if not fields:
            continue
        value = int(fields[0])
        if len(fields) > 1 and fields[1].lower() == "kb":
            value *= 1024
        out[key] = value
    return out


def fs_free(path: str) -> int:
    st = os.statvfs(path)
    return st.f_bavail * st.f_frsize


def parse_lfs_sha(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip().strip('"')
    if value.startswith("sha256:"):
        value = value.split(":", 1)[1]
    return value.lower()


def main() -> int:
    api = (
        f"https://huggingface.co/api/models/{REPO_ID}/revision/{REVISION}"
        "?blobs=true"
    )
    meta = fetch_json(api)
    resolved_sha = str(meta.get("sha") or "")
    siblings = meta.get("siblings") or []
    match = next((x for x in siblings if x.get("rfilename") == FILENAME), None)
    assert match is not None, "TARGET_FILE_NOT_IN_PINNED_REVISION"

    lfs = match.get("lfs") or {}
    api_size = lfs.get("size", match.get("size"))
    api_sha = parse_lfs_sha(lfs.get("sha256") or lfs.get("oid"))

    resolve_url = f"https://huggingface.co/{REPO_ID}/resolve/{REVISION}/{FILENAME}"
    headers = head(resolve_url)
    head_size_raw = (
        headers.get("x-linked-size")
        or headers.get("content-length")
    )
    head_size = int(head_size_raw) if head_size_raw and head_size_raw.isdigit() else None
    head_sha = parse_lfs_sha(
        headers.get("x-linked-etag")
        or headers.get("etag")
    )

    observed_sizes = [x for x in (api_size, head_size) if isinstance(x, int)]
    assert observed_sizes, "NO_REMOTE_SIZE_EVIDENCE"
    assert all(x == EXPECTED_BYTES for x in observed_sizes), observed_sizes

    observed_shas = [x for x in (api_sha, head_sha) if x and len(x) == 64]
    assert observed_shas, "NO_REMOTE_SHA256_EVIDENCE"
    assert all(x == EXPECTED_SHA256 for x in observed_shas), observed_shas

    mi = meminfo()
    ram_total = mi["MemTotal"]
    ram_available = mi["MemAvailable"]
    cwd_free = fs_free(os.getcwd())
    root_free = fs_free("/")
    max_free = max(cwd_free, root_free)
    disk_margin = max_free - EXPECTED_BYTES

    disk_preflight = disk_margin >= MIN_DISK_MARGIN_BYTES
    ram_total_preflight = ram_total >= MIN_RAM_TOTAL_BYTES
    ram_available_preflight = ram_available >= MIN_RAM_AVAILABLE_BYTES
    prerequisite_pass = disk_preflight and ram_total_preflight and ram_available_preflight

    receipt = {
        "schema": "PROJECT_BRAIN_QWEN38_Q2_STANDARD_RUNNER_PREFLIGHT_V1",
        "status": "PASS" if prerequisite_pass else "FAIL",
        "subject": {
            "repository": REPO_ID,
            "requested_revision": REVISION,
            "resolved_revision_sha": resolved_sha,
            "filename": FILENAME,
            "expected_bytes": EXPECTED_BYTES,
            "expected_sha256": EXPECTED_SHA256,
        },
        "remote_identity": {
            "api_size": api_size,
            "head_size": head_size,
            "api_sha256": api_sha,
            "head_sha256": head_sha,
            "size_match": all(x == EXPECTED_BYTES for x in observed_sizes),
            "sha256_match": all(x == EXPECTED_SHA256 for x in observed_shas),
            "model_bytes_downloaded": 0,
        },
        "runner": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "cpu_count": os.cpu_count(),
            "workspace_free_bytes": cwd_free,
            "root_free_bytes": root_free,
            "max_observed_free_bytes": max_free,
            "model_file_bytes": EXPECTED_BYTES,
            "post_model_disk_margin_bytes": disk_margin,
            "ram_total_bytes": ram_total,
            "ram_available_bytes": ram_available,
        },
        "gates": {
            "minimum_disk_margin_bytes": MIN_DISK_MARGIN_BYTES,
            "disk_preflight_pass": disk_preflight,
            "minimum_ram_total_bytes": MIN_RAM_TOTAL_BYTES,
            "ram_total_preflight_pass": ram_total_preflight,
            "minimum_ram_available_bytes": MIN_RAM_AVAILABLE_BYTES,
            "ram_available_preflight_pass": ram_available_preflight,
        },
        "deductions": [
            "EXACT_CURRENT_Q2_REMOTE_IDENTITY_IS_VERIFIED_WITHOUT_DOWNLOADING_MODEL_BYTES",
            "STANDARD_RUNNER_RESOURCE_PRECONDITIONS_ARE_MEASURED_ON_THIS_RUN",
        ],
        "hard_nonclaims": [
            "NO_MODEL_LOAD_OR_INFERENCE_OCCURRED",
            "NO_CLAIM_LLAMA_CPP_COMPATIBILITY",
            "NO_CLAIM_Q2_LIVEBENCH_OR_AUTOMATIONBENCH_SCORE",
            "NO_CAPABILITY_ACCEPTANCE_OR_OWNERSHIP_CREDIT",
            "NO_TERMINAL_CASE_EXPOSURE",
        ],
        "accounting": {
            "incremental_spend_usd": 0,
            "model_bytes_downloaded": 0,
            "terminal_cases_consumed": 0,
            "acceptance_credit_delta": 0,
        },
    }
    Path("qwen38_q2_standard_runner_preflight_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0 if prerequisite_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
# fastlane trigger after workflow installation
