#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import shutil
import struct
import subprocess
import sys
import time

MODEL_REPO = "Qwen/Qwen3-VL-4B-Instruct-GGUF"
REV = "594171a9fa4ab2a90f017aa69a323b270cd8d24f"
MODEL = "Qwen3VL-4B-Instruct-Q4_K_M.gguf"
MODEL_SHA256 = "ce6a2eac86eeb49ffacb19d580ddd26c0d42cd0a0386b311158a5bf4a6996ffe"
MMPROJ = "mmproj-Qwen3VL-4B-Instruct-Q8_0.gguf"
MMPROJ_SHA256 = "30ba2c7dd3127a4561b6cba9d13d0f711c91bdb38742e2f56d73c8cb596bd06d"
LLAMA_REPO = "https://github.com/ggml-org/llama.cpp.git"
LLAMA_COMMIT = "a7fb71fab83b474a0892b9a05aaa3a8ddca2729b"
OUT = pathlib.Path("chartography_gguf_preflight_receipt.json")


def run(cmd, cwd=None, timeout=None):
    p = subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    return p


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(8 * 1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def write_bmp(path: pathlib.Path) -> None:
    w = h = 64
    row = w * 3
    pixels = bytearray()
    for y in range(h):
        for x in range(w):
            if 16 <= x < 48 and 16 <= y < 48:
                b, g, r = 255, 0, 0
            else:
                b, g, r = 0, 0, 255
            pixels += bytes((b, g, r))
    file_size = 54 + len(pixels)
    header = bytearray(b"BM")
    header += struct.pack("<IHHI", file_size, 0, 0, 54)
    header += struct.pack("<IIIHHIIIIII", 40, w, h, 1, 24, 0, len(pixels), 2835, 2835, 0, 0)
    path.write_bytes(header + pixels)


def fail(reason, detail=None):
    receipt = {
        "schema": "PROJECT_BRAIN_CHARTOGRAPHY_QWEN3_VL4B_GGUF_PUBLIC_RUNNER_PREFLIGHT_V1",
        "status": "FAIL_CLOSED__" + reason,
        "pass": False,
        "detail": detail,
        "terminal_cases_consumed": 0,
        "incremental_spend_usd": 0,
        "acceptance_credit_delta": 0,
        "fresh_reality_authority": False,
    }
    OUT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    raise SystemExit(1)


def main():
    if os.environ.get("GITHUB_ACTIONS") != "true":
        fail("NOT_GITHUB_ACTIONS")

    cpu = os.cpu_count() or 0
    mem_kib = 0
    for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemTotal:"):
            mem_kib = int(line.split()[1])
            break
    mem_bytes = mem_kib * 1024
    disk0 = shutil.disk_usage(pathlib.Path.cwd())

    if cpu < 4:
        fail("CPU_LT_4", cpu)
    if mem_bytes < 14 * 1024**3:
        fail("RAM_LT_14_GIB", mem_bytes)

    work = pathlib.Path("gguf-preflight-work")
    work.mkdir(exist_ok=True)

    def hf_url(name):
        return f"https://huggingface.co/{MODEL_REPO}/resolve/{REV}/{name}?download=true"

    downloads = []
    for name, expected in [(MODEL, MODEL_SHA256), (MMPROJ, MMPROJ_SHA256)]:
        path = work / name
        t0 = time.time()
        p = run(["curl", "-fL", "--retry", "5", "--retry-all-errors", "-o", str(path), hf_url(name)], timeout=1800)
        if p.returncode != 0:
            fail("DOWNLOAD_FAILED_" + name, p.stderr[-4000:])
        got = sha256(path)
        downloads.append({"file": name, "bytes": path.stat().st_size, "sha256": got, "seconds": round(time.time()-t0, 3)})
        if got != expected:
            fail("SHA256_MISMATCH_" + name, {"expected": expected, "got": got})

    clone = run(["git", "clone", "--filter=blob:none", LLAMA_REPO, str(work / "llama.cpp")], timeout=600)
    if clone.returncode != 0:
        fail("LLAMA_CLONE_FAILED", clone.stderr[-4000:])
    checkout = run(["git", "checkout", LLAMA_COMMIT], cwd=work / "llama.cpp", timeout=120)
    if checkout.returncode != 0:
        fail("LLAMA_CHECKOUT_FAILED", checkout.stderr[-4000:])

    t0 = time.time()
    cfg = run(["cmake", "-B", "build", "-DCMAKE_BUILD_TYPE=Release", "-DGGML_NATIVE=OFF"], cwd=work / "llama.cpp", timeout=600)
    if cfg.returncode != 0:
        fail("CMAKE_CONFIGURE_FAILED", cfg.stderr[-6000:])
    build = run(["cmake", "--build", "build", "--config", "Release", "--target", "llama-mtmd-cli", "-j", str(min(cpu, 4))], cwd=work / "llama.cpp", timeout=1800)
    if build.returncode != 0:
        fail("LLAMA_MTMD_BUILD_FAILED", {"stdout": build.stdout[-6000:], "stderr": build.stderr[-6000:]})
    build_seconds = round(time.time()-t0, 3)

    binary = work / "llama.cpp" / "build" / "bin" / "llama-mtmd-cli"
    if not binary.exists():
        fail("LLAMA_MTMD_BINARY_MISSING", str(binary))

    image = work / "synthetic.bmp"
    write_bmp(image)

    cmd = [
        "/usr/bin/time", "-v", str(binary),
        "-m", str(work / MODEL),
        "--mmproj", str(work / MMPROJ),
        "--image", str(image),
        "-p", "Describe the image briefly. Mention the two visible colors.",
        "-n", "48",
        "--temp", "0",
    ]
    inf = run(cmd, timeout=600)
    if inf.returncode != 0:
        fail("INFERENCE_FAILED", {"stdout": inf.stdout[-8000:], "stderr": inf.stderr[-8000:]})
    if not inf.stdout.strip():
        fail("EMPTY_OUTPUT")

    disk1 = shutil.disk_usage(pathlib.Path.cwd())
    receipt = {
        "schema": "PROJECT_BRAIN_CHARTOGRAPHY_QWEN3_VL4B_GGUF_PUBLIC_RUNNER_PREFLIGHT_V1",
        "status": "PASS__FREE_PUBLIC_RUNNER_RUNTIME_FIT_AND_SYNTHETIC_MULTIMODAL_SMOKE",
        "pass": True,
        "subject": {
            "model_repo": MODEL_REPO,
            "revision": REV,
            "model": MODEL,
            "model_sha256": MODEL_SHA256,
            "mmproj": MMPROJ,
            "mmproj_sha256": MMPROJ_SHA256,
            "llama_cpp_commit": LLAMA_COMMIT,
        },
        "observed": {
            "cpu_count": cpu,
            "mem_total_bytes": mem_bytes,
            "disk_total_bytes": disk0.total,
            "disk_free_before_bytes": disk0.free,
            "disk_free_after_bytes": disk1.free,
            "downloads": downloads,
            "build_seconds": build_seconds,
            "inference_stdout_tail": inf.stdout[-6000:],
            "time_v_stderr_tail": inf.stderr[-6000:],
        },
        "logical_effect": [
            "CHARTOGRAPHY_COMPACT_GGUF_EXECUTION_SUBJECT_RUNTIME_FIT_CLOSED_ON_FREE_PUBLIC_STANDARD_RUNNER",
            "CHARTOGRAPHY_SYNTHETIC_MULTIMODAL_SMOKE_CLOSED",
            "DELETE_BUILDKITE_ACCOUNT_DEPENDENCY_FOR_CHARTOGRAPHY_FIRST_FIT_AND_SYNTHETIC_SMOKE",
        ],
        "hard_nonclaims": [
            "NO_CHARTOGRAPHY_TERMINAL_CASE_READ",
            "NO_CHARTOGRAPHY_SCORE",
            "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
        ],
        "terminal_cases_consumed": 0,
        "incremental_spend_usd": 0,
        "acceptance_credit_delta": 0,
        "fresh_reality_authority": False,
    }
    OUT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
