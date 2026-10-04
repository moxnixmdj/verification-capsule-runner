#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path

LLAMA_COMMIT = "0504396140d1c882f5f6ee34466a42db7ae90114"
HF_REV = "313447f"
BASE_URL = "https://huggingface.co/unsloth/Qwen3.8-27B-GGUF/resolve/" + HF_REV
CANDIDATES = [
    {
        "name": "Q3_K_XL",
        "file": "Qwen3.8-27B-UD-Q3_K_XL.gguf",
        "sha256": "8c2a45ff85e7674ca185ec8eb6cdeab0e617ed9d8018caed0b64380eb2a67a5e",
        "nominal_bytes": 13_100_000_000,
    },
    {
        "name": "Q2_K_XL",
        "file": "Qwen3.8-27B-UD-Q2_K_XL.gguf",
        "sha256": "fd4730dd8aad070517978752b63d530aeb1740d2283cab9fa24f1e404032ddb0",
        "nominal_bytes": 9_828_981_664,
    },
]
RECEIPT = Path("qwen38_quant_zero_cost_fit_receipt.json")


def run(cmd, *, timeout=None, check=True, capture=True):
    return subprocess.run(
        cmd,
        text=True,
        capture_output=capture,
        timeout=timeout,
        check=check,
    )


def mem_available_bytes() -> int:
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) * 1024
    except Exception:
        pass
    return 0


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            block = f.read(16 * 1024 * 1024)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def download(url: str, dest: Path) -> int:
    req = urllib.request.Request(url, headers={"User-Agent": "project-brain-qwen-fit-probe"})
    total = 0
    with urllib.request.urlopen(req, timeout=120) as src, dest.open("wb") as out:
        while True:
            block = src.read(16 * 1024 * 1024)
            if not block:
                break
            out.write(block)
            total += len(block)
    return total


def write_receipt(receipt: dict) -> None:
    RECEIPT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")


def main() -> int:
    receipt = {
        "schema": "PROJECT_BRAIN_QWEN38_QUANT_ZERO_COST_FIT_PROBE_V1",
        "status": "STARTED",
        "incremental_spend_usd": 0,
        "terminal_cases_consumed": 0,
        "pinned_llama_cpp_commit": LLAMA_COMMIT,
        "pinned_hf_transport_revision": HF_REV,
        "candidate_order": [c["name"] for c in CANDIDATES],
        "attempts": [],
    }
    write_receipt(receipt)

    # Free large SDK caches that are irrelevant to this isolated CPU probe.
    for p in [
        "/usr/local/lib/android",
        "/usr/share/dotnet",
        "/opt/ghc",
        "/usr/local/.ghcup",
        "/opt/hostedtoolcache/CodeQL",
    ]:
        try:
            shutil.rmtree(p, ignore_errors=True)
        except Exception:
            pass

    baseline_disk = shutil.disk_usage(".")
    receipt["resource_baseline"] = {
        "disk_free_bytes": baseline_disk.free,
        "mem_available_bytes": mem_available_bytes(),
        "cpu_count": os.cpu_count(),
    }
    write_receipt(receipt)

    src = Path("/tmp/llama.cpp")
    if src.exists():
        shutil.rmtree(src)
    run(["git", "clone", "--filter=blob:none", "--no-checkout", "https://github.com/ggml-org/llama.cpp.git", str(src)], timeout=180)
    run(["git", "-C", str(src), "checkout", "--detach", LLAMA_COMMIT], timeout=120)
    run([
        "cmake", "-S", str(src), "-B", str(src / "build"),
        "-DCMAKE_BUILD_TYPE=Release",
        "-DGGML_NATIVE=OFF",
        "-DLLAMA_CURL=OFF",
        "-DGGML_OPENMP=ON",
        "-DLLAMA_BUILD_SERVER=OFF",
        "-DLLAMA_BUILD_TESTS=OFF",
        "-DLLAMA_BUILD_EXAMPLES=ON",
    ], timeout=180)
    run(["cmake", "--build", str(src / "build"), "--target", "llama-cli", "-j2"], timeout=1200)
    cli_candidates = list((src / "build").rglob("llama-cli"))
    if not cli_candidates:
        raise RuntimeError("LLAMA_CLI_NOT_BUILT")
    cli = Path("/tmp/llama-cli")
    shutil.copy2(cli_candidates[0], cli)
    cli.chmod(0o755)
    shutil.rmtree(src, ignore_errors=True)

    receipt["llama_cli_sha256"] = sha256_file(cli)
    receipt["resource_after_build_cleanup"] = {
        "disk_free_bytes": shutil.disk_usage(".").free,
        "mem_available_bytes": mem_available_bytes(),
    }
    write_receipt(receipt)

    for cand in CANDIDATES:
        attempt = {
            "name": cand["name"],
            "file": cand["file"],
            "expected_sha256": cand["sha256"],
            "nominal_bytes": cand["nominal_bytes"],
            "status": "STARTED",
        }
        receipt["attempts"].append(attempt)
        model = Path("/tmp") / cand["file"]
        model.unlink(missing_ok=True)

        # Keep a conservative 1.2 GB safety margin for filesystem/runtime state.
        free_before = shutil.disk_usage("/tmp").free
        attempt["disk_free_before_download_bytes"] = free_before
        if free_before < cand["nominal_bytes"] + 1_200_000_000:
            attempt["status"] = "HARD_FIT_FAIL_DISK_BEFORE_DOWNLOAD"
            attempt["required_nominal_plus_margin_bytes"] = cand["nominal_bytes"] + 1_200_000_000
            write_receipt(receipt)
            continue

        url = BASE_URL + "/" + cand["file"]
        t0 = time.time()
        try:
            got_bytes = download(url, model)
        except Exception as exc:
            attempt["status"] = "DOWNLOAD_FAILED"
            attempt["error"] = repr(exc)
            write_receipt(receipt)
            continue
        attempt["downloaded_bytes"] = got_bytes
        attempt["download_seconds"] = round(time.time() - t0, 3)
        got_sha = sha256_file(model)
        attempt["observed_sha256"] = got_sha
        if got_sha != cand["sha256"]:
            attempt["status"] = "HASH_MISMATCH"
            model.unlink(missing_ok=True)
            write_receipt(receipt)
            continue

        attempt["mem_available_before_inference_bytes"] = mem_available_bytes()
        cmd = [
            str(cli), "-m", str(model),
            "-p", "Reply with exactly one word: OK",
            "-n", "8", "-c", "256", "-t", str(min(4, os.cpu_count() or 2)),
            "--temp", "0", "--seed", "1", "--no-display-prompt",
        ]
        t1 = time.time()
        try:
            proc = run(cmd, timeout=1200, check=False)
            attempt["returncode"] = proc.returncode
            attempt["stdout_tail"] = proc.stdout[-4000:]
            attempt["stderr_tail"] = proc.stderr[-8000:]
            attempt["inference_seconds"] = round(time.time() - t1, 3)
            attempt["mem_available_after_inference_bytes"] = mem_available_bytes()
            if proc.returncode == 0 and proc.stdout.strip():
                attempt["status"] = "PASS_LOAD_AND_SHORT_GENERATION"
                receipt["status"] = "PASS"
                receipt["selected_subject"] = cand["name"]
                model.unlink(missing_ok=True)
                write_receipt(receipt)
                return 0
            attempt["status"] = "HARD_FIT_OR_RUNTIME_FAIL"
        except subprocess.TimeoutExpired as exc:
            attempt["status"] = "INFERENCE_TIMEOUT"
            attempt["error"] = repr(exc)
        finally:
            model.unlink(missing_ok=True)
            write_receipt(receipt)

    receipt["status"] = "FAIL_CLOSED__NO_CANDIDATE_PASSED_LOAD_AND_SHORT_GENERATION"
    write_receipt(receipt)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
