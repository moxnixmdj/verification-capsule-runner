#!/usr/bin/env python3
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import subprocess
from pathlib import Path

MODEL_SHA256 = "d766661c2e39c3da78d8eddf15287af263dce1eedc1c9c8093ed8e54eb067dbc"
MAX_LEARNED_BYTES = 100_000_000

SYSTEM = "You are a precise text transformation engine. Follow the user's transformation instructions exactly. Return only the requested transformed text, with no preface or commentary."

TASKS = [
    {
        "id": "PARAPHRASE_1",
        "family": "paraphrase",
        "prompt": "Paraphrase this sentence without changing any fact. Use one sentence. Do not copy more than four consecutive words from the source. Source: At dawn, the red drone crossed the glass bridge because its battery was low.",
        "source": "At dawn, the red drone crossed the glass bridge because its battery was low.",
        "required_all": [["red"], ["drone"], ["glass"], ["bridge"], ["dawn"], ["battery"], ["low"]],
        "requires_causal": True,
        "max_sentence_count": 1,
        "max_common_run": 4,
        "max_similarity": 0.90,
    },
    {
        "id": "PARAPHRASE_2",
        "family": "paraphrase",
        "prompt": "Paraphrase this sentence without changing any fact. Use one sentence. Do not copy more than four consecutive words from the source. Source: Nora mailed the blue notebook to Elias on Friday after the train arrived.",
        "source": "Nora mailed the blue notebook to Elias on Friday after the train arrived.",
        "required_all": [["nora"], ["blue"], ["notebook"], ["elias"], ["friday"], ["train"]],
        "requires_temporal": True,
        "max_sentence_count": 1,
        "max_common_run": 4,
        "max_similarity": 0.90,
    },
    {
        "id": "SIMPLIFY_1",
        "family": "simplify",
        "prompt": "Rewrite in simple everyday English using one short sentence. Preserve every fact. Source: Despite the precipitation being exceptionally heavy, the hikers continued their ascent toward the summit.",
        "source": "Despite the precipitation being exceptionally heavy, the hikers continued their ascent toward the summit.",
        "required_any_groups": [["rain", "precipitation"], ["hikers"], ["continued", "kept"], ["climb", "ascent", "climbing"], ["summit", "top"]],
        "requires_contrast": True,
        "max_sentence_count": 1,
        "max_words": 18,
        "max_similarity": 0.88,
    },
    {
        "id": "SIMPLIFY_2",
        "family": "simplify",
        "prompt": "Rewrite in simple everyday English using one short sentence. Preserve every fact. Source: The physician recommended that Omar consume additional fluids because the fever had caused dehydration.",
        "source": "The physician recommended that Omar consume additional fluids because the fever had caused dehydration.",
        "required_any_groups": [["doctor", "physician"], ["omar"], ["drink", "consume"], ["fluid", "fluids", "water"], ["fever"], ["dehydration", "dehydrated"]],
        "requires_causal": True,
        "max_sentence_count": 1,
        "max_words": 18,
        "max_similarity": 0.88,
    },
    {
        "id": "SUMMARIZE_1",
        "family": "summarize",
        "prompt": "Summarize the passage in one sentence of at most 20 words. Include the main action, place, time, and outcome. Omit irrelevant details. Passage: Maya installed a solar pump at the village well on Tuesday. The pump restored water flow after a three-day outage. She wore a green scarf. A delivery truck passed at noon.",
        "source": "Maya installed a solar pump at the village well on Tuesday. The pump restored water flow after a three-day outage. She wore a green scarf. A delivery truck passed at noon.",
        "required_any_groups": [["maya"], ["solar"], ["pump"], ["village", "well"], ["tuesday"], ["water"], ["restored", "restore", "flow"]],
        "forbidden": ["green", "scarf", "truck", "noon"],
        "max_sentence_count": 1,
        "max_words": 20,
    },
    {
        "id": "SUMMARIZE_2",
        "family": "summarize",
        "prompt": "Summarize the passage in one sentence of at most 20 words. Keep the experiment, date, and measured result. Omit irrelevant details. Passage: Orion Labs tested a copper battery on Monday. It retained 82 percent capacity after 500 cycles. The test bench was beside a window. Engineers logged the result in a red folder.",
        "source": "Orion Labs tested a copper battery on Monday. It retained 82 percent capacity after 500 cycles. The test bench was beside a window. Engineers logged the result in a red folder.",
        "required_any_groups": [["orion"], ["copper"], ["battery"], ["monday"], ["82"], ["500"], ["capacity"], ["cycles", "cycle"]],
        "forbidden": ["window", "red", "folder"],
        "max_sentence_count": 1,
        "max_words": 20,
    },
    {
        "id": "STORY_1",
        "family": "story",
        "prompt": "Write exactly four sentences. Keep this event order: Mira finds a brass key; she uses it to open a blue door; behind the door she frees an injured owl; the story ends with the owl flying into moonlight. Return only the story.",
        "required_any_groups": [["mira"], ["brass"], ["key"], ["blue"], ["door"], ["injured"], ["owl"], ["moonlight"]],
        "ordered": ["key", "door", "owl", "moonlight"],
        "exact_sentence_count": 4,
    },
    {
        "id": "STORY_2",
        "family": "story",
        "prompt": "Write exactly five sentences. Keep this event order: Theo repairs a broken radio during a storm; he hears a distress call; he maps the caller to a lighthouse; he bicycles there; he helps the stranded keeper. Return only the story.",
        "required_any_groups": [["theo"], ["radio"], ["storm"], ["distress"], ["call"], ["lighthouse"], ["bicycle", "bicycles", "bike", "cycles"], ["keeper"]],
        "ordered": ["radio", "distress", "lighthouse", "bicy", "keeper"],
        "exact_sentence_count": 5,
    },
]

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9]+(?:['-][A-Za-z0-9]+)?", text.lower())

def sentence_count(text: str) -> int:
    return len([x for x in re.split(r"(?<=[.!?])\s+", text.strip()) if x.strip()])

def longest_common_word_run(a: str, b: str) -> int:
    aa, bb = words(a), words(b)
    m = 0
    prev = [0] * (len(bb) + 1)
    for x in aa:
        cur = [0]
        for j, y in enumerate(bb, 1):
            v = prev[j - 1] + 1 if x == y else 0
            cur.append(v)
            m = max(m, v)
        prev = cur
    return m

def has_any(text: str, options: list[str]) -> bool:
    low = text.lower()
    return any(re.search(r"\b" + re.escape(x.lower()) + r"\b", low) for x in options)

def validate(task: dict, output: str) -> tuple[bool, list[str], dict]:
    errors: list[str] = []
    low = output.lower().strip()
    wc = len(words(output))
    sc = sentence_count(output)

    if not low:
        errors.append("EMPTY")
    if "<|im_" in low:
        errors.append("CHAT_TOKEN_LEAK")

    for group in task.get("required_all", []):
        if not has_any(output, group):
            errors.append("MISSING:" + "/".join(group))
    for group in task.get("required_any_groups", []):
        if not has_any(output, group):
            errors.append("MISSING:" + "/".join(group))
    for tok in task.get("forbidden", []):
        if has_any(output, [tok]):
            errors.append("FORBIDDEN:" + tok)

    if task.get("requires_causal") and not has_any(output, ["because", "due", "since", "caused", "so"]):
        errors.append("CAUSAL_LINK_MISSING")
    if task.get("requires_temporal") and not has_any(output, ["after", "following", "once", "when"]):
        errors.append("TEMPORAL_LINK_MISSING")
    if task.get("requires_contrast") and not has_any(output, ["despite", "although", "even", "but"]):
        errors.append("CONTRAST_MISSING")

    if "max_sentence_count" in task and sc > task["max_sentence_count"]:
        errors.append(f"TOO_MANY_SENTENCES:{sc}")
    if "exact_sentence_count" in task and sc != task["exact_sentence_count"]:
        errors.append(f"SENTENCE_COUNT:{sc}!={task['exact_sentence_count']}")
    if "max_words" in task and wc > task["max_words"]:
        errors.append(f"TOO_MANY_WORDS:{wc}")

    source = task.get("source")
    similarity = None
    common_run = None
    if source:
        similarity = difflib.SequenceMatcher(None, " ".join(words(source)), " ".join(words(output))).ratio()
        if similarity > task.get("max_similarity", 1.0):
            errors.append(f"TOO_SIMILAR:{similarity:.3f}")
        common_run = longest_common_word_run(source, output)
        if "max_common_run" in task and common_run > task["max_common_run"]:
            errors.append(f"COMMON_RUN:{common_run}")

    ordered_positions = {}
    if "ordered" in task:
        cursor = -1
        for token in task["ordered"]:
            idx = low.find(token, cursor + 1)
            ordered_positions[token] = idx
            if idx < 0 or idx <= cursor:
                errors.append("ORDER:" + token)
                break
            cursor = idx

    return not errors, errors, {
        "word_count": wc,
        "sentence_count": sc,
        "similarity": similarity,
        "longest_common_word_run": common_run,
        "ordered_positions": ordered_positions,
    }

def build_prompt(user_prompt: str) -> str:
    return (
        "<|im_start|>system\n" + SYSTEM + "<|im_end|>\n"
        "<|im_start|>user\n" + user_prompt + "<|im_end|>\n"
        "<|im_start|>assistant\n"
    )

def generate(cli: Path, model: Path, prompt: str) -> str:
    cmd = [
        str(cli), "-m", str(model), "-p", build_prompt(prompt),
        "-n", "180", "--temp", "0", "--top-k", "1", "--seed", "1",
        "--no-display-prompt", "--log-disable",
    ]
    proc = subprocess.run(cmd, text=True, capture_output=True, timeout=120)
    if proc.returncode != 0:
        raise RuntimeError("LLAMA_CLI_FAILED:" + proc.stderr[-2000:])
    out = proc.stdout.strip()
    out = out.split("<|im_end|>", 1)[0].strip()
    return out

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--llama-cli", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--result", default="semantic-core-result.json")
    args = ap.parse_args()

    cli = Path(args.llama_cli)
    model = Path(args.model)
    if not cli.is_file():
        raise SystemExit("LLAMA_CLI_NOT_FOUND")
    if not model.is_file():
        raise SystemExit("MODEL_NOT_FOUND")

    size = model.stat().st_size
    digest = sha256_file(model)
    asset_pass = size == EXPECTED_BYTES and digest == MODEL_SHA256

    rows = []
    for task in TASKS:
        try:
            output = generate(cli, model, task["prompt"])
            passed, errors, metrics = validate(task, output)
        except Exception as exc:
            output = ""
            passed = False
            errors = [type(exc).__name__ + ":" + str(exc)]
            metrics = {}
        rows.append({
            "id": task["id"],
            "family": task["family"],
            "pass": passed,
            "errors": errors,
            "output": output,
            "metrics": metrics,
        })

    by_family = {}
    for fam in sorted({x["family"] for x in rows}):
        fr = [x for x in rows if x["family"] == fam]
        by_family[fam] = {"passed": sum(x["pass"] for x in fr), "total": len(fr)}

    passed = sum(x["pass"] for x in rows)
    family_floor = all(v["passed"] >= 1 for v in by_family.values())
    candidate_gate = asset_pass and passed >= 7 and family_floor

    result = {
        "schema": "PROJECT_BRAIN_ROOT1_QWEN35_4B_SEMANTIC_CORE_PUBLIC_PREFLIGHT_V1",
        "candidate": {
            "upstream": "HuggingFaceTB/SmolLM2-135M-Instruct",
            "quantized_artifact": "bartowski/SmolLM2-135M-Instruct-GGUF/SmolLM2-135M-Instruct-IQ4_XS.gguf",
            "sha256": digest,
            "bytes": size,
            "expected_bytes": EXPECTED_BYTES,
            "asset_pass": asset_pass,
        },
        "score": {"passed": passed, "total": len(rows), "by_family": by_family},
        "candidate_gate": candidate_gate,
        "rows": rows,
        "hard_nonclaims": [
            "REUSED_FROZEN_PUBLIC_SYNTHETIC_PREFLIGHT_IS_NOT_TERMINAL_ACCEPTANCE",
            "PASS_IS_NOT_OPEN_WORLD_SEMANTIC_CAPABILITY_PROOF",
            "PASS_CREATES_ZERO_FAMILY_CAPABILITY_OWNERSHIP_OR_ACCEPTANCE_CREDIT",
            "NO_TERMINAL_LIVEBENCH_CASES_WERE_USED",
        ],
    }
    Path(args.result).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if candidate_gate else 1

if __name__ == "__main__":
    raise SystemExit(main())
