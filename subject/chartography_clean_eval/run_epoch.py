from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.request
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
    """Run model-authored analysis code in a no-network read-only container.

    The container receives only the current chart and per-call scratch files.
    Benchmark caches, gold answers, repository files, credentials, and model
    weights are not mounted or passed as environment variables.
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
            "docker", "run", "--rm",
            "--network", "none",
            "--read-only",
            "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges",
            "--pids-limit", "64",
            "--memory", "768m",
            "--cpus", "1",
            "--tmpfs", "/tmp:rw,nosuid,nodev,size=128m",
            "-v", f"{tool_dir}:/work:rw",
            "-w", "/work",
            "brain-chartography-tool-v1",
            "python", "/work/tool.py",
        ],
        text=True,
        capture_output=True,
        timeout=90,
        env={"PATH": "/usr/local/bin:/usr/bin:/bin"},
    )
    return {
        "returncode": cp.returncode,
        "stdout": cp.stdout[-6000:],
        "stderr": cp.stderr[-2000:],
        "stdout_sha256": hashlib.sha256(cp.stdout.encode()).hexdigest(),
        "stderr_sha256": hashlib.sha256(cp.stderr.encode()).hexdigest(),
    }


def _action_from_obj(obj: object) -> dict | None:
    if not isinstance(obj, dict):
        return None
    if set(obj) == {"final"} and isinstance(obj.get("final"), str) and obj["final"].strip():
        return {"kind": "final", "answer": obj["final"].strip()}
    if set(obj) == {"tool", "left", "top", "right", "bottom"} and obj.get("tool") == "crop":
        vals = [obj[k] for k in ("left", "top", "right", "bottom")]
        if all(type(v) is int for v in vals):
            return {"kind": "crop", "box": tuple(vals)}
    if set(obj) == {"tool", "code"} and obj.get("tool") == "python" and isinstance(obj.get("code"), str):
        return {"kind": "python", "code": obj["code"]}
    return None


def extract_action(stdout: str) -> dict | None:
    """Return the last valid complete JSON action embedded in model output.

    JSONDecoder is used instead of regex or line-only parsing so Python code
    may contain nested braces, strings, or newlines without corrupting the
    action boundary.
    """
    decoder = json.JSONDecoder()
    found: list[tuple[int, dict]] = []
    for i, ch in enumerate(stdout):
        if ch != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(stdout[i:])
        except Exception:
            continue
        action = _action_from_obj(obj)
        if action is not None:
            found.append((i, action))
    return found[-1][1] if found else None

def fallback_final(stdout: str) -> str:
    lines = [re.sub(r"\s+", " ", x).strip() for x in stdout.splitlines() if x.strip()]
    return lines[-1] if lines else ""


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "crop",
            "description": "Crop the current chart to a smaller rectangle so labels, thin lines, and intersections can be inspected at higher effective resolution.",
            "parameters": {
                "type": "object",
                "properties": {
                    "left": {"type": "integer"},
                    "top": {"type": "integer"},
                    "right": {"type": "integer"},
                    "bottom": {"type": "integer"},
                },
                "required": ["left", "top", "right", "bottom"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "python",
            "description": "Measure the current chart offline using Python. /work/current_image.png is available with Pillow, NumPy, SciPy, Matplotlib, and OpenCV. Use it for axis calibration, pixel/color tracing, line/intersection detection, geometric measurement, or calculations. Print concise measurements only.",
            "parameters": {
                "type": "object",
                "properties": {"code": {"type": "string"}},
                "required": ["code"],
                "additionalProperties": False,
            },
        },
    },
]


def _native_tool_action(tool_call: dict) -> dict:
    fn = tool_call.get("function") or {}
    name = fn.get("name")
    args = fn.get("arguments", {})
    if isinstance(args, str):
        args = json.loads(args)
    if not isinstance(args, dict):
        return {"kind": "error", "answer": ""}
    if name == "crop":
        try:
            vals = tuple(int(args[k]) for k in ("left", "top", "right", "bottom"))
        except Exception:
            return {"kind": "error", "answer": ""}
        return {"kind": "crop", "box": vals}
    if name == "python" and isinstance(args.get("code"), str) and args["code"].strip():
        return {"kind": "python", "code": args["code"]}
    return {"kind": "error", "answer": ""}


def _image_part(image: Path) -> dict:
    with Image.open(image) as im:
        fmt = (im.format or "PNG").upper()
    mime = {"PNG": "image/png", "JPEG": "image/jpeg", "JPG": "image/jpeg", "WEBP": "image/webp"}.get(fmt, "image/png")
    return {
        "type": "image_url",
        "image_url": {"url": "data:" + mime + ";base64," + base64.b64encode(image.read_bytes()).decode("ascii")},
    }


def _call_native_model(
    *,
    server_url: str,
    messages: list[dict],
    seed: int,
    require_tool: bool,
    timeout_s: int,
    image_sha256: str,
) -> tuple[dict, dict]:
    payload = {
        "temperature": 0.0,
        "top_k": 1,
        "top_p": 1.0,
        "seed": seed,
        "max_tokens": 1024,
        "parallel_tool_calls": False,
        "tools": TOOLS,
        "tool_choice": "required" if require_tool else "auto",
        "messages": messages,
    }
    req = urllib.request.Request(
        server_url,
        data=json.dumps(payload, separators=(",", ":")).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            raw_bytes = resp.read()
        body = json.loads(raw_bytes)
        choice = body["choices"][0]
        msg = choice["message"]
        error_class = None
        http_status = 200
    except Exception as exc:
        raw_bytes = str(exc).encode()
        choice = {}
        msg = {"role": "assistant", "content": "", "tool_calls": []}
        error_class = type(exc).__name__
        http_status = getattr(exc, "code", None)

    receipt = {
        "returncode": 0 if error_class is None else 1,
        "http_status": http_status,
        "error_class": error_class,
        "response_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "seed": seed,
        "image_sha256": image_sha256,
        "wall_seconds": round(time.time() - started, 3),
        "finish_reason": choice.get("finish_reason"),
        "tool_call_count": len(msg.get("tool_calls") or []),
        "required_tool": require_tool,
    }
    return msg, receipt


def solve_one(
    *,
    server_url: str,
    image: Path,
    question: str,
    workdir: Path,
    seed: int,
    max_crops: int,
    timeout_s: int,
) -> dict:
    workdir.mkdir(parents=True, exist_ok=True)
    current = image
    with Image.open(current) as im:
        w, h = im.size

    messages: list[dict] = [{
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": (
                    "Solve this professional chart-reading question from the chart image. "
                    "Use measurement tools rather than eyeballing. The first turn must use a tool. "
                    "Python runs offline and can inspect /work/current_image.png with Pillow, NumPy, SciPy, Matplotlib, and OpenCV. "
                    "When tool measurements are decisive, trust them rather than contradicting them by visual guess. "
                    f"Current image size is {w}x{h}. "
                    "When enough evidence has been gathered, return only the substantive final answer with required units. "
                    f"QUESTION: {question}"
                ),
            },
            _image_part(current),
        ],
    }]

    transcript: list[dict] = []
    calls: list[dict] = []
    max_tool_turns = max_crops

    for turn in range(max_tool_turns + 2):
        msg, call_receipt = _call_native_model(
            server_url=server_url,
            messages=messages,
            seed=seed + turn,
            require_tool=(turn == 0),
            timeout_s=timeout_s,
            image_sha256=sha256_file(current),
        )
        calls.append(call_receipt)

        if call_receipt["error_class"] is not None:
            return {
                "status": "MODEL_ERROR",
                "answer": "",
                "error_class": call_receipt["error_class"],
                "crop_calls": sum(1 for x in transcript if x.get("tool") == "crop"),
                "transcript": transcript,
                "calls": calls,
            }

        tool_calls = msg.get("tool_calls") or []
        content = (msg.get("content") or "").strip()

        if tool_calls:
            if len(tool_calls) != 1:
                return {
                    "status": "MULTIPLE_TOOL_CALLS",
                    "answer": "",
                    "crop_calls": sum(1 for x in transcript if x.get("tool") == "crop"),
                    "transcript": transcript,
                    "calls": calls,
                }
            if turn >= max_tool_turns:
                return {
                    "status": "TOOL_LIMIT",
                    "answer": "",
                    "crop_calls": sum(1 for x in transcript if x.get("tool") == "crop"),
                    "transcript": transcript,
                    "calls": calls,
                }

            call = tool_calls[0]
            call_id = call.get("id") or f"call_{turn:04d}"
            try:
                action = _native_tool_action(call)
            except Exception as exc:
                return {
                    "status": "BAD_TOOL_CALL",
                    "answer": "",
                    "error_class": type(exc).__name__,
                    "crop_calls": sum(1 for x in transcript if x.get("tool") == "crop"),
                    "transcript": transcript,
                    "calls": calls,
                }

            # Preserve actual assistant native-tool message so subsequent turns
            # receive the tool call in the format expected by the chat template.
            messages.append({
                "role": "assistant",
                "content": msg.get("content"),
                "tool_calls": tool_calls,
            })

            if action["kind"] == "python":
                code = action["code"]
                try:
                    rec = run_python_tool(code, current, workdir / f"python_{turn:02d}")
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
                    "code_sha256": hashlib.sha256(code.encode()).hexdigest(),
                    **rec,
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": json.dumps({
                        "returncode": rec["returncode"],
                        "stdout": rec["stdout"],
                        "stderr": rec["stderr"],
                    }, separators=(",", ":")),
                })
                continue

            if action["kind"] == "crop":
                dst = workdir / f"crop_{turn:02d}.png"
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
                messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": json.dumps({
                        "status": "ok",
                        "crop_size": rec["output_size"],
                    }, separators=(",", ":")),
                })
                current = dst
                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                f"Here is the crop you requested, size {rec['output_size'][0]}x{rec['output_size'][1]}. "
                                "Continue from the accumulated evidence."
                            ),
                        },
                        _image_part(current),
                    ],
                })
                continue

            return {
                "status": "BAD_TOOL_CALL",
                "answer": "",
                "crop_calls": sum(1 for x in transcript if x.get("tool") == "crop"),
                "transcript": transcript,
                "calls": calls,
            }

        if turn == 0:
            return {
                "status": "REQUIRED_TOOL_NOT_CALLED",
                "answer": "",
                "crop_calls": 0,
                "transcript": transcript,
                "calls": calls,
            }

        if content:
            return {
                "status": "FINAL",
                "answer": content,
                "crop_calls": sum(1 for x in transcript if x.get("tool") == "crop"),
                "transcript": transcript,
                "calls": calls,
            }

        return {
            "status": "EMPTY_FINAL",
            "answer": "",
            "crop_calls": sum(1 for x in transcript if x.get("tool") == "crop"),
            "transcript": transcript,
            "calls": calls,
        }

    return {
        "status": "NO_VALID_FINAL",
        "answer": "",
        "crop_calls": sum(1 for x in transcript if x.get("tool") == "crop"),
        "transcript": transcript,
        "calls": calls,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--epoch", type=int, required=True)
    ap.add_argument("--dataset-repo", required=True)
    ap.add_argument("--dataset-rev", required=True)
    ap.add_argument("--server-url", required=True)
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
            server_url=args.server_url,
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
