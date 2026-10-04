#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
import sys

EXPECTED_SHA256 = "fd4730dd8aad070517978752b63d530aeb1740d2283cab9fa24f1e404032ddb0"
EXPECTED_MIN_BYTES = 9_000_000_000
EXPECTED_MAX_BYTES = 11_000_000_000

def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def main() -> int:
    model = pathlib.Path(os.environ.get("MODEL_PATH", "model.gguf"))
    llama = pathlib.Path(os.environ.get("LLAMA_CLI", "llama-cli"))
    if not model.is_file():
        raise SystemExit("MODEL_MISSING")
    size = model.stat().st_size
    if not (EXPECTED_MIN_BYTES <= size <= EXPECTED_MAX_BYTES):
        raise SystemExit(f"MODEL_SIZE_OUT_OF_RANGE:{size}")
    digest = sha256_file(model)
    if digest != EXPECTED_SHA256:
        raise SystemExit(f"MODEL_SHA256_MISMATCH:{digest}")
    if not llama.is_file():
        raise SystemExit("LLAMA_CLI_MISSING")

    prompt = "Reply with the single word OK."
    cmd = [
        str(llama), "-m", str(model), "-c", "256", "-n", "8",
        "-p", prompt, "--temp", "0", "-t", "4"
    ]
    proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=7200)
    out = proc.stdout.strip()
    result = {
        "schema": "PROJECT_BRAIN_QWEN38_27B_Q2_ZERO_SPEND_LOAD_PROBE_V1",
        "model_sha256": digest,
        "model_bytes": size,
        "llama_cli": str(llama),
        "returncode": proc.returncode,
        "stdout_nonempty": bool(out),
        "stdout_tail": out[-1000:],
        "stderr_tail": proc.stderr[-3000:],
    }
    pathlib.Path("qwen38_q2_probe_result.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if proc.returncode != 0:
        raise SystemExit("LLAMA_INFERENCE_NONZERO")
    if not out:
        raise SystemExit("LLAMA_INFERENCE_EMPTY")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
