#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import platform
import shutil
from datetime import datetime, timezone
from pathlib import Path

MODEL_BYTES = 9_828_981_664
DISK_SAFETY_HEADROOM_BYTES = 2 * 1024**3
MEMORY_SAFETY_HEADROOM_BYTES = 2 * 1024**3

def meminfo_bytes() -> dict[str, int]:
    out: dict[str, int] = {}
    with open("/proc/meminfo", "r", encoding="utf-8") as handle:
        for line in handle:
            key, rest = line.split(":", 1)
            value_kib = int(rest.strip().split()[0])
            out[key] = value_kib * 1024
    return out

def main() -> int:
    disk = shutil.disk_usage("/")
    mem = meminfo_bytes()
    mem_total = mem.get("MemTotal", 0)
    mem_available = mem.get("MemAvailable", 0)

    disk_after_model = disk.free - MODEL_BYTES
    memory_after_weights = mem_available - MODEL_BYTES

    disk_prefit = disk_after_model >= DISK_SAFETY_HEADROOM_BYTES
    memory_weight_prefit = memory_after_weights >= MEMORY_SAFETY_HEADROOM_BYTES

    receipt = {
        "schema": "PROJECT_BRAIN_QWEN38_Q2_STANDARD_PUBLIC_RUNNER_RESOURCE_PREFLIGHT_V1",
        "measured_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": (
            "PASS__DOWNLOAD_STORAGE_PREFLIGHT__MEMORY_WEIGHT_PREFLIGHT"
            if disk_prefit and memory_weight_prefit
            else "MEASURED__RESOURCE_PREFLIGHT_NOT_FULL_PASS"
        ),
        "subject": {
            "repository": "unsloth/Qwen3.8-27B-GGUF",
            "file": "Qwen3.8-27B-UD-Q2_K_XL.gguf",
            "file_bytes": MODEL_BYTES,
            "sha256": "fd4730dd8aad070517978752b63d530aeb1740d2283cab9fa24f1e404032ddb0",
        },
        "runner": {
            "os": platform.platform(),
            "machine": platform.machine(),
            "cpu_count": os.cpu_count(),
            "disk_total_bytes": disk.total,
            "disk_free_bytes_after_checkout": disk.free,
            "mem_total_bytes": mem_total,
            "mem_available_bytes": mem_available,
            "gpu_assumed": False,
        },
        "preflight": {
            "disk_safety_headroom_bytes": DISK_SAFETY_HEADROOM_BYTES,
            "disk_free_after_one_model_copy_bytes": disk_after_model,
            "download_storage_prefit": disk_prefit,
            "memory_safety_headroom_bytes": MEMORY_SAFETY_HEADROOM_BYTES,
            "memory_available_after_weight_bytes_only": memory_after_weights,
            "memory_weight_prefit": memory_weight_prefit,
        },
        "hard_nonclaims": [
            "NO_MODEL_BYTES_DOWNLOADED_BY_THIS_PREFLIGHT",
            "NO_CLAIM_LLAMA_CPP_LOAD_OR_GENERATION_FITS_UNTIL_MEASURED",
            "NO_CLAIM_Q2_PRESERVES_BF16_LIVEBENCH_OR_SEMANTIC_CAPABILITY",
            "NO_ACCEPTANCE_FAMILY_CAPABILITY_OWNERSHIP_OR_TERMINAL_CREDIT",
            "ONE_EPHEMERAL_RUNNER_MEASUREMENT_IS_NOT_A_PERMANENT_RESOURCE_GUARANTEE",
        ],
        "accounting": {
            "incremental_spend_usd": 0,
            "terminal_cases_consumed": 0,
            "model_bytes_downloaded": 0,
        },
    }

    path = Path("qwen38_q2_runner_fit_receipt.json")
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
