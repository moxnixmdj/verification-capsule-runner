#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import urllib.request
from pathlib import Path

import numpy as np
import onnxruntime as ort
import sentencepiece as spm

OUT = Path("flan_t5_small_int8_semantic_core_receipt.json")
CACHE = Path("flan_t5_small_int8_artifacts")
CACHE.mkdir(exist_ok=True)

ARTIFACTS = [
    {
        "id": "encoder_int8",
        "url": "https://huggingface.co/onnx-community/flan-t5-small-ONNX/resolve/76988c16f73cadb2c2e13e2d7d85608944223105/onnx/encoder_model_int8.onnx?download=true",
        "path": CACHE / "encoder_model_int8.onnx",
        "bytes": 35720521,
        "sha256": "691c4b521a2aad8ff0d1a94e578f507bbfb7b3d939b5b4d233c4a8043a2388dc",
    },
    {
        "id": "decoder_no_past_int8",
        "url": "https://huggingface.co/onnx-community/flan-t5-small-ONNX/resolve/76988c16f73cadb2c2e13e2d7d85608944223105/onnx/decoder_model_int8.onnx?download=true",
        "path": CACHE / "decoder_model_int8.onnx",
        "bytes": 58862707,
        "sha256": "54e7e2e606115068b979fe83cd64f23ee48b7cfde750f3ca9c48ea493bee5c86",
    },
    {
        "id": "sentencepiece_vocab",
        "url": "https://huggingface.co/google/flan-t5-small/resolve/e48659520aaf0069046c3413e9835d214fefa83c/spiece.model?download=true",
        "path": CACHE / "spiece.model",
        "bytes": 791656,
        "sha256": "d60acb128cf7b7f2536e8f38a5b18a05535c9e14c7a355904270e15b0945ea86",
    },
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def fetch_exact() -> list[dict]:
    rows = []
    for a in ARTIFACTS:
        req = urllib.request.Request(a["url"], headers={"User-Agent": "project-brain-independent-verifier"})
        with urllib.request.urlopen(req, timeout=120) as r, a["path"].open("wb") as f:
            while True:
                chunk = r.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)
        observed = {"bytes": a["path"].stat().st_size, "sha256": sha256(a["path"])}
        assert observed["bytes"] == a["bytes"], (a["id"], observed, a)
        assert observed["sha256"] == a["sha256"], (a["id"], observed, a)
        rows.append({"id": a["id"], **observed})
    return rows


def ort_type_to_numpy(type_name: str):
    if "int64" in type_name:
        return np.int64
    if "int32" in type_name:
        return np.int32
    if "float16" in type_name:
        return np.float16
    if "float" in type_name:
        return np.float32
    raise AssertionError(f"UNSUPPORTED_ORT_INPUT_TYPE:{type_name}")


def make_feed(session, values: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    feed = {}
    for inp in session.get_inputs():
        if inp.name not in values:
            raise AssertionError(f"MISSING_INPUT:{inp.name}:{inp.type}:{inp.shape}")
        feed[inp.name] = values[inp.name].astype(ort_type_to_numpy(inp.type), copy=False)
    return feed


def encode(sp: spm.SentencePieceProcessor, text: str) -> list[int]:
    ids = list(sp.encode(text, out_type=int))
    if not ids or ids[-1] != 1:
        ids.append(1)
    return ids


def decode(sp: spm.SentencePieceProcessor, ids: list[int]) -> str:
    clean = [int(x) for x in ids if int(x) not in (0, 1)]
    return sp.decode(clean).strip()


def generate(enc, dec, sp, prompt: str, max_new_tokens: int = 64) -> tuple[str, list[int]]:
    input_ids = np.asarray([encode(sp, prompt)], dtype=np.int64)
    attention = np.ones_like(input_ids, dtype=np.int64)
    enc_values = {
        "input_ids": input_ids,
        "attention_mask": attention,
    }
    enc_outs = enc.run(None, make_feed(enc, enc_values))
    assert enc_outs, "ENCODER_NO_OUTPUTS"
    hidden = enc_outs[0]

    generated = [0]
    for _ in range(max_new_tokens):
        decoder_ids = np.asarray([generated], dtype=np.int64)
        decoder_attention = np.ones_like(decoder_ids, dtype=np.int64)
        values = {
            "input_ids": decoder_ids,
            "decoder_input_ids": decoder_ids,
            "attention_mask": decoder_attention,
            "decoder_attention_mask": decoder_attention,
            "encoder_hidden_states": hidden,
            "encoder_attention_mask": attention,
        }
        outs = dec.run(None, make_feed(dec, values))
        assert outs, "DECODER_NO_OUTPUTS"
        names = [x.name for x in dec.get_outputs()]
        idx = next((i for i, n in enumerate(names) if "logits" in n.lower()), 0)
        logits = np.asarray(outs[idx])
        assert logits.ndim == 3 and logits.shape[0] == 1, (names, [np.asarray(x).shape for x in outs])
        token = int(np.argmax(logits[0, -1]))
        generated.append(token)
        if token == 1:
            break
    return decode(sp, generated), generated


def words(s: str) -> list[str]:
    return [x.strip(".,!?;:()[]{}\"'").lower() for x in s.split() if x.strip(".,!?;:()[]{}\"'")]


def semantic_checks(task: str, source: str, output: str) -> dict:
    ws = words(output)
    ss = set(words(source))
    os_ = set(ws)
    overlap = len(ss & os_) / max(1, len(ss))
    checks = {
        "nonempty": bool(output.strip()),
        "word_count": len(ws),
        "source_vocab_recall": overlap,
    }
    if task == "paraphrase":
        checks.update({
            "not_verbatim": output.strip().lower() != source.strip().lower(),
            "rain_concept_retained": "rain" in os_ or "raining" in os_,
            "home_concept_retained": "home" in os_,
        })
        checks["pass"] = checks["nonempty"] and checks["not_verbatim"] and checks["rain_concept_retained"] and checks["home_concept_retained"]
    elif task == "simplify":
        checks.update({
            "plants_retained": "plants" in os_ or "plant" in os_,
            "sunlight_or_light_retained": bool({"sunlight", "light"} & os_),
            "not_longer_than_source": len(ws) <= len(words(source)),
        })
        checks["pass"] = checks["nonempty"] and checks["plants_retained"] and checks["sunlight_or_light_retained"] and checks["not_longer_than_source"]
    elif task == "summarize":
        checks.update({
            "mission_retained": "mission" in os_,
            "samples_retained": "samples" in os_ or "sample" in os_,
            "shorter_than_source": len(ws) < len(words(source)),
        })
        checks["pass"] = checks["nonempty"] and checks["mission_retained"] and checks["samples_retained"] and checks["shorter_than_source"]
    elif task == "story":
        checks.update({
            "lighthouse_grounding": "lighthouse" in os_,
            "storm_grounding": "storm" in os_ or "stormy" in os_,
            "minimum_story_words": len(ws) >= 12,
        })
        checks["pass"] = checks["nonempty"] and checks["lighthouse_grounding"] and checks["storm_grounding"] and checks["minimum_story_words"]
    else:
        raise AssertionError(task)
    return checks


def main() -> int:
    artifacts = fetch_exact()

    # Hard network cutoff after prefetch. The inference code below has no network
    # calls; this flag is recorded and the sessions use local filesystem paths.
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"

    providers = ["CPUExecutionProvider"]
    enc = ort.InferenceSession(str(CACHE / "encoder_model_int8.onnx"), providers=providers)
    dec = ort.InferenceSession(str(CACHE / "decoder_model_int8.onnx"), providers=providers)
    sp = spm.SentencePieceProcessor(model_file=str(CACHE / "spiece.model"))

    probes = [
        (
            "paraphrase",
            "The boy quickly ran home because rain had started.",
            "Paraphrase the following sentence while keeping its meaning: The boy quickly ran home because rain had started.",
        ),
        (
            "simplify",
            "Photosynthesis is the biochemical process by which plants convert sunlight, water, and carbon dioxide into stored chemical energy.",
            "Simplify this sentence for a young reader: Photosynthesis is the biochemical process by which plants convert sunlight, water, and carbon dioxide into stored chemical energy.",
        ),
        (
            "summarize",
            "The lunar mission launched on Monday, entered orbit on Wednesday, collected rock samples near the southern crater, and returned the samples safely to Earth after twelve days.",
            "Summarize this passage in one short sentence: The lunar mission launched on Monday, entered orbit on Wednesday, collected rock samples near the southern crater, and returned the samples safely to Earth after twelve days.",
        ),
        (
            "story",
            "lighthouse storm",
            "Write a short story about a lighthouse keeper during a storm. Mention both the lighthouse and the storm.",
        ),
    ]

    results = []
    for task, source, prompt in probes:
        output, ids = generate(enc, dec, sp, prompt)
        checks = semantic_checks(task, source, output)
        results.append({
            "task": task,
            "prompt": prompt,
            "source": source,
            "output": output,
            "generated_token_ids": ids,
            "checks": checks,
        })

    receipt = {
        "schema": "PROJECT_BRAIN_FLAN_T5_SMALL_INT8_SEMANTIC_CORE_INDEPENDENT_SMOKE_V1",
        "status": "PASS" if all(r["checks"]["pass"] for r in results) else "SEMANTIC_SMOKE_FAIL",
        "artifact_verification": artifacts,
        "exact_persistent_learned_bytes": sum(x["bytes"] for x in artifacts),
        "runtime": {
            "onnxruntime_version": ort.__version__,
            "sentencepiece_vocab_size": sp.vocab_size(),
            "encoder_inputs": [{"name": x.name, "type": x.type, "shape": x.shape} for x in enc.get_inputs()],
            "encoder_outputs": [{"name": x.name, "type": x.type, "shape": x.shape} for x in enc.get_outputs()],
            "decoder_inputs": [{"name": x.name, "type": x.type, "shape": x.shape} for x in dec.get_inputs()],
            "decoder_outputs": [{"name": x.name, "type": x.type, "shape": x.shape} for x in dec.get_outputs()],
            "network_after_prefetch": False,
            "provider": providers[0],
        },
        "probes": results,
        "hard_nonclaims": [
            "FOUR_SMOKE_PROBES_DO_NOT_PROVE_OPUS_5_5_SEMANTIC_PARITY",
            "PASS_DOES_NOT_PROVE_LIVEBENCH_65_7",
            "NO_TERMINAL_LIVEBENCH_CASES_ARE_READ",
            "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
        ],
        "accounting": {
            "terminal_cases_consumed": 0,
            "incremental_spend_usd": 0,
            "acceptance_credit_delta": 0,
        },
    }
    OUT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))
    return 0 if receipt["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
