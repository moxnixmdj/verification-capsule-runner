#!/usr/bin/env python3
from __future__ import annotations
import json, os, pathlib, shutil

MODEL_BYTES = 9_828_981_664
MODEL_SHA256 = "fd4730dd8aad070517978752b63d530aeb1740d2283cab9fa24f1e404032ddb0"
DISK_RESERVE_BYTES = 1_500_000_000
MEMORY_RESERVE_BYTES = 2_000_000_000

def mem_available_bytes() -> int:
    for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) * 1024
    raise RuntimeError("MemAvailable missing")

disk = shutil.disk_usage(".")
mem = mem_available_bytes()
out = {
    "schema": "PROJECT_BRAIN_QWEN38_Q2_PUBLIC_RUNNER_RESOURCE_PROBE_V1",
    "model_bytes": MODEL_BYTES,
    "model_sha256": MODEL_SHA256,
    "cpu_count": os.cpu_count(),
    "disk_total_bytes": disk.total,
    "disk_free_bytes": disk.free,
    "memory_available_bytes": mem,
    "disk_headroom_after_model_bytes": disk.free - MODEL_BYTES,
    "memory_headroom_after_model_bytes": mem - MODEL_BYTES,
    "download_preflight_pass": disk.free >= MODEL_BYTES + DISK_RESERVE_BYTES,
    "load_preflight_pass_heuristic": mem >= MODEL_BYTES + MEMORY_RESERVE_BYTES,
    "hard_nonclaim": "RESOURCE_PREFLIGHT_IS_NOT_MODEL_LOAD_OR_INFERENCE_FIT_PROOF"
}
print(json.dumps(out, sort_keys=True))
assert out["download_preflight_pass"], out
