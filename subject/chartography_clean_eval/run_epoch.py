from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path

import pyarrow.parquet as pq
from huggingface_hub import hf_hub_download
from PIL import Image

from chartography_deterministic_lower_bound_scorer_v1 import score_lower_bound

_JSON = re.compile(r"\{[^{}]*\}", re.S)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def crop_image(src: Path, dst: Path, box: tuple[int, int, int, int]) -> dict:
    left, top, right, bottom = box
    if any(type(v) is not int for v in box):
        raise ValueError("CROP_COORDINATES_MUST_BE_INTEGERS")
    with Image.open(src) as im:
        w, h = im.size
        if left < 0 or top < 0 or right <= left or bottom <= top:
            raise ValueError("INVALID_CROP_BOX")
        if right > w or bottom > h:
            raise ValueError("CROP_BOX_OUT_OF_BOUNDS")
        out = im.crop(box)
        dst.parent.mkdir(parents=True, exist_ok=True)
        out.save(dst)
        return {
            "input_size": [w, h],
            "output_size": [out.size[0], out.size[1]],
            "box": list(box),
            "output_sha256": sha256_file(dst),
        }


def run_python_tool(code: str, current_image: Path, workdir: Path) -> dict:
    """Run model-authored analysis code in an isolated no-network Linux namespace.

    Only system runtime libraries and this tool-call directory are visible.
    Benchmark caches, gold answers, repository files, credentials, and model
    weights are not mounted into the namespace.
    """
    tool_dir = workdir.resolve()
    tool_dir.mkdir(parents=True, exist_ok=True)
    image_copy = tool_dir / "current_image.png"
    with Image.open(current_image) as im:
        im.save(image_copy)
    code_path = tool_dir / "tool.py"
    code_path.write_text(code)
    cp = subprocess.run(
        [
            "bwrap", "--unshare-all", "--new-session", "--die-with-parent",
            "--clearenv",
            "--setenv", "PATH", "/usr/bin:/bin",
            "--setenv", "HOME", "/tmp",
            "--ro-bind", "/usr", "/usr",
            "--ro-bind", "/bin", "/bin",
            "--ro-bind", "/lib", "/lib",
            "--ro-bind", "/lib64", "/lib64",
            "--proc", "/proc",
            "--dev", "/dev",
            "--tmpfs", "/tmp",
            "--bind", str(tool_dir), "/work",
            "--chdir", "/work",
            "/usr/bin/python3", "/work/tool.py",
        ],
        text=True,
        capture_output=True,
        timeout=90,
        env={"PATH": "/usr/bin:/bin"},
    )
    return {
        "returncode": cp.returncode,
        "stdout": cp.stdout[-6000:],
        "stderr": cp.stderr[-2000:],
        "stdout_sha256": hashlib.sha256(cp.stdout.encode()).hexdigest(),
        "stderr_sha256": hashlib.sha256(cp.stderr.encode()).hexdigest(),
    }


def extract_action(stdout: str) -> dict | None:
    """Parse the last complete JSON action line.

    Line-wise JSON parsing is deliberate: Python tool code may itself contain
    braces, which makes regex-based object extraction unsound.
    """
    candidates = [x.strip() for x in stdout.splitlines() if x.strip()]
    if stdout.strip() not in candidates:
        candidates.append(stdout.strip())
    for raw in reversed(candidates):
        try:
            obj = json.loads(raw)
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        if set(obj) == {"final"} and isinstance(obj.get("final"), str) and obj["final"].strip():
            return {"kind": "final", "answer": obj["final"].strip()}
        if set(obj) == {"tool", "left", "top", "right", "bottom"} and obj.get("tool") == "crop":
            vals = [obj[k] for k in ("left", "top", "right", "bottom")]
            if all(type(v) is int for v in vals):
                return {"kind": "crop", "box": tuple(vals)}
        if set(obj) == {"tool", "code"} and obj.get("tool") == "python" and isinstance(obj.get("code"), str):
            return {"kind": "python", "code": obj["code"]}
    return None

def fallback_final(stdout: str) -> str:
    lines = [re.sub(r"\s+", " ", x).strip() for x in stdout.splitlines() if x.strip()]
    return lines[-1] if lines else ""


def invoke_model(
    *,
    cli: Path,
    model: Path,
    mmproj: Path,
    image: Path,
    question: str,
    transcript: list[dict],
    seed: int,
    call_index: int,
    timeout_s: int,
) -> tuple[dict, dict]:
    with Image.open(image) as im:
        w, h = im.size
    prior = []
    for x in transcript[-6:]:
        if x.get("tool") == "crop":
            prior.append({"tool": "crop", "box": x["box"], "output_size": x["output_size"]})
        elif x.get("tool") == "python":
            prior.append({
                "tool": "python",
                "returncode": x["returncode"],
                "stdout": x["stdout"],
                "stderr": x["stderr"],
            })
    prompt = (
        "You are solving one professional chart-reading question. "
        "You may inspect the CURRENT image directly. You have two tools: crop and isolated Python analysis. "
        "Return exactly one JSON object and nothing else. "
        "Crop: "
        '{"tool":"crop","left":INTEGER,"top":INTEGER,"right":INTEGER,"bottom":INTEGER}. '
        "Python: "
        '{"tool":"python","code":"PYTHON CODE"}. '
        "Python runs offline in an isolated container that can read /work/current_image.png and has "
        "Python 3, Pillow, NumPy, SciPy, Matplotlib, and OpenCV. Print only measurements you need. "
        "It cannot access the benchmark, network, credentials, model files, or any golden answers. "
        "Coordinates are pixel coordinates in the CURRENT image with origin at top-left, "
        f"whose size is {w}x{h}. "
        "When ready answer using "
        '{"final":"SUBSTANTIVE ANSWER"}. '
        "The final field must contain only the answer you commit to, preserving any units needed by the question. "
        "Do not mention this tool protocol in the final answer. "
        f"Previous tool receipts: {json.dumps(prior, separators=(',', ':'))}\n"
        f"QUESTION: {question}"
    )
    cp = subprocess.run(
        [
            str(cli),
            "-m", str(model),
            "--mmproj", str(mmproj),
            "--no-mmproj-offload",
            "--image", str(image),
            "-p", prompt,
            "-n", "384",
            "-t", "4",
            "--seed", str(seed + call_index),
            "--temp", "0.2",
        ],
        text=True,
        capture_output=True,
        timeout=timeout_s,
    )
    raw = cp.stdout.strip()
    action = extract_action(raw)
    receipt = {
        "returncode": cp.returncode,
        "stdout_sha256": hashlib.sha256(cp.stdout.encode()).hexdigest(),
        "stderr_sha256": hashlib.sha256(cp.stderr.encode()).hexdigest(),
        "seed": seed + call_index,
        "image_sha256": sha256_file(image),
    }
    if cp.returncode != 0:
        return {"kind": "error", "answer": ""}, receipt
    if action is not None:
        return action, receipt
    # Fail open only on formatting, never on semantics: the raw last line becomes
    # the candidate final answer and must still pass the strict lower-bound scorer.
    return {"kind": "final", "answer": fallback_final(raw)}, receipt


def solve_one(
    *,
    cli: Path,
    model: Path,
    mmproj: Path,
    image: Path,
    question: str,
    workdir: Path,
    seed: int,
    max_crops: int,
    timeout_s: int,
) -> dict:
    current = image
    transcript: list[dict] = []
    calls: list[dict] = []
    for call_index in range(max_crops + 1):
        action, call_receipt = invoke_model(
            cli=cli,
            model=model,
            mmproj=mmproj,
            image=current,
            question=question,
            transcript=transcript,
            seed=seed,
            call_index=call_index,
            timeout_s=timeout_s,
        )
        calls.append(call_receipt)
        if action["kind"] == "final":
            return {
                "status": "FINAL",
                "answer": action["answer"],
                "crop_calls": len(transcript),
                "transcript": transcript,
                "calls": calls,
            }
        if call_index >= max_crops:
            return {
                "status": "NO_VALID_FINAL",
                "answer": "",
                "crop_calls": sum(1 for x in transcript if x.get("tool") == "crop"),
                "transcript": transcript,
                "calls": calls,
            }
        if action["kind"] == "python":
            try:
                rec = run_python_tool(action["code"], current, workdir / f"python_{call_index:02d}")
            except Exception as exc:
                return {
                    "status": "PYTHON_TOOL_ERROR",
                    "answer": "",
                    "error_class": type(exc).__name__,
                    "crop_calls": sum(1 for x in transcript if x.get("tool") == "crop"),
                    "transcript": transcript,
                    "calls": calls,
                }
            transcript.append({
                "tool": "python",
                "code_sha256": hashlib.sha256(action["code"].encode()).hexdigest(),
                **rec,
            })
            continue
        if action["kind"] != "crop":
            return {
                "status": "NO_VALID_FINAL",
                "answer": "",
                "crop_calls": sum(1 for x in transcript if x.get("tool") == "crop"),
                "transcript": transcript,
                "calls": calls,
            }
        dst = workdir / f"crop_{call_index:02d}.png"
        try:
            rec = crop_image(current, dst, action["box"])
        except Exception as exc:
            return {
                "status": "INVALID_CROP",
                "answer": "",
                "error_class": type(exc).__name__,
                "crop_calls": sum(1 for x in transcript if x.get("tool") == "crop"),
                "transcript": transcript,
                "calls": calls,
            }
        transcript.append({"tool": "crop", **rec})
        current = dst
    return {"status": "NO_VALID_FINAL", "answer": "", "crop_calls": len(transcript), "transcript": transcript, "calls": calls}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--epoch", type=int, required=True)
    ap.add_argument("--dataset-repo", required=True)
    ap.add_argument("--dataset-rev", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--mmproj", required=True)
    ap.add_argument("--cli", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-crops", type=int, default=3)
    ap.add_argument("--timeout-seconds", type=int, default=300)
    ap.add_argument("--shard-index", type=int, default=0)
    ap.add_argument("--shard-count", type=int, default=1)
    args = ap.parse_args()

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    cache = outdir / "hf-cache"
    parquet_path = Path(
        hf_hub_download(
            repo_id=args.dataset_repo,
            filename="data.parquet",
            repo_type="dataset",
            revision=args.dataset_rev,
            cache_dir=str(cache),
        )
    )

    # GENERATION PHASE: deliberately project only non-golden columns.
    gen_table = pq.read_table(parquet_path, columns=["task_id", "prompt", "chart_path"])
    all_rows = gen_table.to_pylist()
    if len(all_rows) != 100:
        raise SystemExit(f"EXPECTED_100_TASKS_GOT_{len(all_rows)}")
    if args.shard_count < 1 or not (0 <= args.shard_index < args.shard_count):
        raise SystemExit("INVALID_SHARD")
    indexed_rows = [(i, row) for i, row in enumerate(all_rows) if i % args.shard_count == args.shard_index]

    responses = []
    for index, row in indexed_rows:
        task_id = str(row["task_id"])
        prompt = str(row["prompt"]).strip()
        chart_rel = str(row["chart_path"])
        chart = Path(
            hf_hub_download(
                repo_id=args.dataset_repo,
                filename=chart_rel,
                repo_type="dataset",
                revision=args.dataset_rev,
                cache_dir=str(cache),
            )
        )
        task_work = outdir / "work" / task_id
        base_seed = args.epoch * 1_000_003 + index * 101
        started = time.time()
        solved = solve_one(
            cli=Path(args.cli),
            model=Path(args.model),
            mmproj=Path(args.mmproj),
            image=chart,
            question=prompt,
            workdir=task_work,
            seed=base_seed,
            max_crops=args.max_crops,
            timeout_s=args.timeout_seconds,
        )
        responses.append(
            {
                "task_id": task_id,
                "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                "chart_rel": chart_rel,
                "chart_sha256": sha256_file(chart),
                "answer": solved["answer"],
                "status": solved["status"],
                "crop_calls": solved.get("crop_calls", 0),
                "transcript": solved.get("transcript", []),
                "model_call_receipts": solved.get("calls", []),
                "wall_seconds": round(time.time() - started, 3),
            }
        )
        print(json.dumps({"epoch": args.epoch, "completed": index + 1, "task_id": task_id, "status": solved["status"], "crop_calls": solved.get("crop_calls", 0)}), flush=True)

    responses_path = outdir / "responses.json"
    responses_path.write_text(json.dumps(responses, indent=2, sort_keys=True) + "\n")
    responses_sha = sha256_file(responses_path)

    # SCORING PHASE: golden answers enter only after every response is frozen above.
    grade_table = pq.read_table(parquet_path, columns=["task_id", "golden_answer"])
    gold = {str(x["task_id"]): str(x["golden_answer"]) for x in grade_table.to_pylist()}
    scored = []
    correct = 0
    for row in responses:
        verdict = score_lower_bound(gold[row["task_id"]], row["answer"])
        correct += verdict.score
        scored.append({"task_id": row["task_id"], "score": verdict.score, "reason": verdict.reason})

    result = {
        "schema": "PROJECT_BRAIN_CHARTOGRAPHY_CLEAN_HELDOUT_EPOCH_RESULT_V1",
        "epoch": args.epoch,
        "dataset_repo": args.dataset_repo,
        "dataset_revision": args.dataset_rev,
        "dataset_task_count": len(responses),
        "full_dataset_task_count": 100,
        "shard_index": args.shard_index,
        "shard_count": args.shard_count,
        "responses_sha256": responses_sha,
        "correct_lower_bound": correct,
        "total": len(responses),
        "lower_bound_percent": 100.0 * correct / len(responses),
        "score_rows": scored,
        "gold_loaded_after_response_seal": True,
        "gold_present_in_generation_projection": False,
        "heldout_tuning_performed": False,
        "incremental_spend_usd": 0,
    }
    (outdir / "score.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: result[k] for k in ("epoch", "correct_lower_bound", "total", "lower_bound_percent", "responses_sha256")}, sort_keys=True))


if __name__ == "__main__":
    main()
