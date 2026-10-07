from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WORK = ROOT / "independent_replay_work"
ASSETS = WORK / "model_assets"
IMAGES = WORK / "images"

MODEL_ID = "ahmed-masry/unichart-chartqa-960"
MODEL_REV = "e5eb1e52c1d775e0f3febaddc7fc3559e80cb989"
DONOR_URL = f"https://huggingface.co/{MODEL_ID}/resolve/{MODEL_REV}/pytorch_model.bin?download=true"
DONOR_SHA = "4407db60801a20bcf254946acfee6727491ef1739ad7b4d3abbf87b7c75e7229"
DONOR_BYTES = 809_199_995
PACKED_SHA = "17fc7d37f6c6e8457d53dd93efff365b17850acf5810ba3067bb06c7c226cb14"
PACKED_BYTES = 94_686_795
COMPLETE_BYTES = 99_999_997
PRECOMMIT_SHA = "45ae2e11ba4493ca51d6a17e8341f45f0a140fad58aa833ca550e6a5c734efaa"
CHARTQA_COMMIT = "044eabfc306abfe9340c5741f0093aefc5973d06"

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(4 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()

def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def download(url: str, path: Path, expected_bytes: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and (expected_bytes is None or path.stat().st_size == expected_bytes):
        return
    tmp = path.with_suffix(path.suffix + ".part")
    tmp.unlink(missing_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "project-brain-h100-independent-replay-v1"})
    with urllib.request.urlopen(req, timeout=120) as r, tmp.open("wb") as f:
        total = 0
        while True:
            b = r.read(4 << 20)
            if not b:
                break
            f.write(b)
            total += len(b)
            if total and total % (128 << 20) < (4 << 20):
                print(json.dumps({"download": path.name, "bytes": total}), flush=True)
    if expected_bytes is not None and tmp.stat().st_size != expected_bytes:
        raise RuntimeError(f"DOWNLOAD_SIZE_MISMATCH:{path.name}:{tmp.stat().st_size}!={expected_bytes}")
    tmp.replace(path)

def verify_ancillary() -> dict:
    frozen = json.loads((ROOT / "H100_UNICHART_CHARTQA_RUNTIME_ASSETS_V1.json").read_text())
    assert frozen["donor"]["model"] == MODEL_ID
    assert frozen["donor"]["revision"] == MODEL_REV
    total = 0
    rows = []
    for row in frozen["files"]:
        name = row["name"]
        quoted = urllib.parse.quote(name, safe="/")
        url = f"https://huggingface.co/{MODEL_ID}/resolve/{MODEL_REV}/{quoted}?download=true"
        p = ASSETS / name
        download(url, p, int(row["bytes"]))
        data = p.read_bytes()
        blob = git_blob_sha(data)
        if blob != row["git_blob_sha"]:
            raise RuntimeError(f"ANCILLARY_GIT_BLOB_MISMATCH:{name}:{blob}!={row['git_blob_sha']}")
        if "sha256" in row and hashlib.sha256(data).hexdigest() != row["sha256"]:
            raise RuntimeError(f"ANCILLARY_SHA256_MISMATCH:{name}")
        total += len(data)
        rows.append({"name": name, "bytes": len(data), "git_blob_sha": blob})
    if total != int(frozen["ancillary_total_bytes"]):
        raise RuntimeError(f"ANCILLARY_TOTAL_MISMATCH:{total}!={frozen['ancillary_total_bytes']}")
    return {"total_bytes": total, "files": rows}

def verify_holdout_and_images() -> dict:
    hold_path = ROOT / "H100_UNICHART_FRESH_CAPABILITY_HOLDOUT_V1.json"
    if sha256(hold_path) != PRECOMMIT_SHA:
        raise RuntimeError("HOLDOUT_PRECOMMIT_SHA_MISMATCH")
    hold = json.loads(hold_path.read_text())
    assert hold["status"].startswith("FROZEN_BEFORE_FP32_OR_PACKED_OUTPUTS")
    assert hold["selection"]["total_cases"] == 20
    assert hold["selection"]["unique_images"] == 20
    IMAGES.mkdir(parents=True, exist_ok=True)
    for c in hold["cases"]:
        name = c["imgname"]
        quoted = urllib.parse.quote(name, safe="")
        url = (
            "https://raw.githubusercontent.com/vis-nlp/ChartQA/"
            + CHARTQA_COMMIT
            + "/ChartQA%20Dataset/val/png/"
            + quoted
        )
        p = IMAGES / name
        download(url, p, int(c["image_bytes"]))
        got = sha256(p)
        if got != c["image_sha256"]:
            raise RuntimeError(f"IMAGE_SHA_MISMATCH:{c['id']}:{got}!={c['image_sha256']}")
    return hold

def reconstruct_candidate(donor: Path, packed: Path) -> dict:
    cmd = [
        sys.executable,
        str(ROOT / "mse_affine_structural_packer.py"),
        "--source", str(donor),
        "--output", str(packed),
        "--expected-source-sha256", DONOR_SHA,
        "--ancillary-bytes", "5313202",
        "--result-json", str(WORK / "pack_result.json"),
    ]
    subprocess.run(cmd, check=True, cwd=ROOT, env={**os.environ, "PYTHONPATH": str(ROOT)})
    if packed.stat().st_size != PACKED_BYTES:
        raise RuntimeError(f"PACKED_SIZE_MISMATCH:{packed.stat().st_size}!={PACKED_BYTES}")
    got = sha256(packed)
    if got != PACKED_SHA:
        raise RuntimeError(f"PACKED_SHA_MISMATCH:{got}!={PACKED_SHA}")
    pack_result = json.loads((WORK / "pack_result.json").read_text())
    if int(pack_result["complete_bundle_bytes"]) != COMPLETE_BYTES:
        raise RuntimeError("COMPLETE_BUNDLE_MISMATCH")
    return pack_result

def evaluate(hold: dict, donor: Path, packed: Path, ancillary_total: int) -> dict:
    from transformers import DonutProcessor, VisionEncoderDecoderConfig, VisionEncoderDecoderModel
    from canonical.runtime.h100_unichart_chartqa_preservation_runner_v1 import (
        answer_case,
        load_fp32_donor,
        relaxed_correct,
    )
    from canonical.runtime.h100_unichart_structural_holdout_runner_v1 import load_structural

    # Use the independently verified exact ancillary files, not a moving Hub lookup.
    cfg = VisionEncoderDecoderConfig.from_pretrained(str(ASSETS), local_files_only=True)
    proc = DonutProcessor.from_pretrained(str(ASSETS), local_files_only=True)

    def fresh_model():
        m = VisionEncoderDecoderModel(config=cfg)
        m.eval()
        return m

    cases = hold["cases"]

    fp32_model = fresh_model()
    load_fp32_donor(fp32_model, donor)
    fp32_rows = []
    for i, c in enumerate(cases, 1):
        pred = answer_case(fp32_model, proc, IMAGES / c["imgname"], c["query"])
        ok = relaxed_correct(c["label"], pred)
        fp32_rows.append({"index": i, "id": c["id"], "label": c["label"], "prediction": pred, "correct": ok})
        print(json.dumps({"subject": "fp32", **fp32_rows[-1]}), flush=True)
    fp32_correct = sum(int(x["correct"]) for x in fp32_rows)

    packed_model = fresh_model()
    load_structural(packed_model, packed, PACKED_SHA)
    packed_rows = []
    for i, c in enumerate(cases, 1):
        pred = answer_case(packed_model, proc, IMAGES / c["imgname"], c["query"])
        ok = relaxed_correct(c["label"], pred)
        packed_rows.append({"index": i, "id": c["id"], "label": c["label"], "prediction": pred, "correct": ok})
        print(json.dumps({"subject": "packed", **packed_rows[-1]}), flush=True)
    packed_correct = sum(int(x["correct"]) for x in packed_rows)

    fp32_acc = fp32_correct / 20
    packed_acc = packed_correct / 20
    gate = hold["pass_gate"]
    byte_pass = PACKED_BYTES + ancillary_total <= 100_000_000
    pass_capability = (
        fp32_acc >= float(gate["minimum_fp32_relaxed_accuracy"])
        and packed_acc >= fp32_acc - float(gate["packed_noninferiority_margin_absolute"])
    )
    return {
        "fp32_correct": fp32_correct,
        "fp32_total": 20,
        "fp32_accuracy": fp32_acc,
        "packed_correct": packed_correct,
        "packed_total": 20,
        "packed_accuracy": packed_acc,
        "packed_minus_fp32_accuracy": packed_acc - fp32_acc,
        "fp32_rows": fp32_rows,
        "packed_rows": packed_rows,
        "byte_pass": byte_pass,
        "capability_noninferiority_pass": pass_capability,
        "pass": bool(byte_pass and pass_capability),
    }

def main() -> None:
    WORK.mkdir(exist_ok=True)
    donor = WORK / "pytorch_model.bin"
    packed = WORK / "chartqa_mse_structural.h100uc"

    ancillary = verify_ancillary()
    hold = verify_holdout_and_images()

    download(DONOR_URL, donor, DONOR_BYTES)
    if sha256(donor) != DONOR_SHA:
        raise RuntimeError("DONOR_SHA_MISMATCH")

    pack_result = reconstruct_candidate(donor, packed)
    observed = evaluate(hold, donor, packed, ancillary["total_bytes"])

    receipt = {
        "schema": "PROJECT_BRAIN_H100_UNICHART_FRESH_CAPABILITY_INDEPENDENT_GITHUB_REPLAY_V1",
        "status": "PASS__INDEPENDENT_GITHUB_REPLAY" if observed["pass"] else "FAIL__INDEPENDENT_GITHUB_REPLAY",
        "carrier": "GITHUB_HOSTED_UBUNTU_PYTHON311",
        "independent_of_original_sprite": True,
        "precommit_sha256": PRECOMMIT_SHA,
        "donor_sha256": DONOR_SHA,
        "candidate_sha256": PACKED_SHA,
        "packed_bytes": PACKED_BYTES,
        "ancillary_bytes": ancillary["total_bytes"],
        "complete_bundle_bytes": PACKED_BYTES + ancillary["total_bytes"],
        "h100_budget_bytes": 100_000_000,
        "margin_bytes": 100_000_000 - PACKED_BYTES - ancillary["total_bytes"],
        "pack_result": pack_result,
        "observed": observed,
        "hard_nonclaims": [
            "PUBLIC_CHARTQA_CAPABILITY_PRESERVATION_ONLY",
            "NO_CHARTOGRAPHY_THRESHOLD_CREDIT",
            "NO_GENERAL_OPEN_WORLD_VISION_PROOF",
            "NO_FULL_H100_TERMINAL_CREDIT",
        ],
        "h100_terminal_credit_delta": 0,
    }
    (ROOT / "independent_replay_receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    if not observed["pass"]:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
