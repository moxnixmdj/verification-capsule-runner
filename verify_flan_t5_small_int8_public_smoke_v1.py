from __future__ import annotations

import hashlib
import json
import os
import socket
import urllib.request
from pathlib import Path

import numpy as np
import onnxruntime as ort
import sentencepiece as spm

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / ".cache_flan_t5_small_int8"
CACHE.mkdir(exist_ok=True)

ARTIFACTS = [
    {
        "id": "encoder_int8",
        "url": "https://huggingface.co/onnx-community/flan-t5-small-ONNX/resolve/76988c16f73cadb2c2e13e2d7d85608944223105/onnx/encoder_model_int8.onnx",
        "path": CACHE / "encoder_model_int8.onnx",
        "bytes": 35720521,
        "sha256": "691c4b521a2aad8ff0d1a94e578f507bbfb7b3d939b5b4d233c4a8043a2388dc",
    },
    {
        "id": "decoder_no_past_int8",
        "url": "https://huggingface.co/onnx-community/flan-t5-small-ONNX/resolve/76988c16f73cadb2c2e13e2d7d85608944223105/onnx/decoder_model_int8.onnx",
        "path": CACHE / "decoder_model_int8.onnx",
        "bytes": 58862707,
        "sha256": "54e7e2e606115068b979fe83cd64f23ee48b7cfde750f3ca9c48ea493bee5c86",
    },
    {
        "id": "sentencepiece_vocab",
        "url": "https://huggingface.co/google/flan-t5-small/resolve/e48659520aaf0069046c3413e9835d214fefa83c/spiece.model",
        "path": CACHE / "spiece.model",
        "bytes": 791656,
        "sha256": "d60acb128cf7b7f2536e8f38a5b18a05535c9e14c7a355904270e15b0945ea86",
    },
]

EXPECTED_TOTAL = 95_374_884
MAX_LEARNED_BYTES = 100_000_000


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download_exact(item: dict) -> None:
    req = urllib.request.Request(item["url"], headers={"User-Agent": "brain-independent-verifier/1"})
    with urllib.request.urlopen(req, timeout=120) as r, item["path"].open("wb") as out:
        while True:
            chunk = r.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
    size = item["path"].stat().st_size
    digest = sha256_file(item["path"])
    assert size == item["bytes"], (item["id"], size, item["bytes"])
    assert digest == item["sha256"], (item["id"], digest, item["sha256"])


class NetworkDisabled:
    def __enter__(self):
        self._orig_socket = socket.socket
        self._orig_create_connection = socket.create_connection

        def blocked(*args, **kwargs):
            raise RuntimeError("NETWORK_DISABLED_AFTER_PREFETCH")

        socket.socket = blocked
        socket.create_connection = blocked

    def __exit__(self, exc_type, exc, tb):
        socket.socket = self._orig_socket
        socket.create_connection = self._orig_create_connection


def _session(path: Path) -> ort.InferenceSession:
    so = ort.SessionOptions()
    so.intra_op_num_threads = max(1, min(4, os.cpu_count() or 1))
    so.inter_op_num_threads = 1
    return ort.InferenceSession(str(path), sess_options=so, providers=["CPUExecutionProvider"])


def _map_inputs(session: ort.InferenceSession, values: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    out = {}
    for meta in session.get_inputs():
        name = meta.name
        if name in values:
            out[name] = values[name]
            continue
        low = name.lower()
        if "encoder_hidden" in low or ("encoder" in low and "hidden" in low):
            out[name] = values["encoder_hidden_states"]
        elif "encoder_attention" in low:
            out[name] = values["encoder_attention_mask"]
        elif "attention_mask" in low:
            out[name] = values["attention_mask"]
        elif "input_ids" in low:
            out[name] = values["input_ids"]
        else:
            raise AssertionError(f"UNMAPPED_INPUT:{name}")
    return out


def generate(sp: spm.SentencePieceProcessor, enc: ort.InferenceSession, dec: ort.InferenceSession, prompt: str, max_new_tokens: int = 64) -> str:
    ids = sp.encode(prompt, out_type=int)
    assert ids, "TOKENIZATION_EMPTY"
    if ids[-1] != 1:
        ids.append(1)
    input_ids = np.asarray([ids], dtype=np.int64)
    attention_mask = np.ones_like(input_ids, dtype=np.int64)

    enc_inputs = _map_inputs(enc, {"input_ids": input_ids, "attention_mask": attention_mask})
    enc_outputs = enc.run(None, enc_inputs)
    assert enc_outputs, "ENCODER_NO_OUTPUT"
    hidden = enc_outputs[0]
    assert hidden.ndim == 3 and hidden.shape[0] == 1

    generated = [0]
    for _ in range(max_new_tokens):
        dec_ids = np.asarray([generated], dtype=np.int64)
        vals = {
            "input_ids": dec_ids,
            "encoder_hidden_states": hidden,
            "encoder_attention_mask": attention_mask,
            "attention_mask": attention_mask,
        }
        dec_inputs = _map_inputs(dec, vals)
        outs = dec.run(None, dec_inputs)
        assert outs, "DECODER_NO_OUTPUT"
        logits = outs[0]
        assert logits.ndim == 3 and logits.shape[0] == 1
        token = int(np.argmax(logits[0, -1, :]))
        if token == 1:
            break
        generated.append(token)

    content_ids = [t for t in generated[1:] if t not in (0, 1)]
    text = sp.decode(content_ids).strip()
    assert text, "EMPTY_GENERATION"
    return text


def concept_hits(text: str, groups: list[list[str]]) -> int:
    low = text.lower()
    return sum(any(word in low for word in group) for group in groups)


def main() -> None:
    for item in ARTIFACTS:
        download_exact(item)

    total = sum(item["path"].stat().st_size for item in ARTIFACTS)
    assert total == EXPECTED_TOTAL, total
    assert total <= MAX_LEARNED_BYTES

    sp = spm.SentencePieceProcessor(model_file=str(CACHE / "spiece.model"))

    probes = [
        {
            "id": "paraphrase",
            "prompt": "Paraphrase while preserving meaning: The committee postponed the meeting because two reports were incomplete.",
            "concepts": [["committee", "group"], ["meeting", "session"], ["report", "document"], ["postpon", "delay"], ["incomplete", "unfinished"]],
            "min_hits": 2,
        },
        {
            "id": "simplify",
            "prompt": "Simplify for a young reader: Although the experiment produced promising preliminary results, the researchers emphasized that further replication was necessary.",
            "concepts": [["experiment", "test"], ["result", "finding"], ["research", "scientist"], ["repeat", "replic", "again"], ["promis", "good"]],
            "min_hits": 2,
        },
        {
            "id": "summarize",
            "prompt": "Summarize in one sentence: A small town installed solar panels on its school, library, and water plant. The project cut electricity bought from the grid and reduced monthly energy bills. Officials plan to use the savings to improve street lighting.",
            "concepts": [["solar", "panel"], ["electric", "energy", "power"], ["bill", "cost", "saving"], ["town", "community"], ["light"]],
            "min_hits": 2,
        },
        {
            "id": "story_generation",
            "prompt": "Write a short story in four sentences about a lost key that is found inside a library book.",
            "concepts": [["key"], ["librar"], ["book"], ["find", "found", "discover"], ["lost", "missing"]],
            "min_hits": 3,
        },
    ]

    results = []
    with NetworkDisabled():
        enc = _session(CACHE / "encoder_model_int8.onnx")
        dec = _session(CACHE / "decoder_model_int8.onnx")
        for probe in probes:
            text = generate(sp, enc, dec, probe["prompt"])
            hits = concept_hits(text, probe["concepts"])
            results.append({
                "id": probe["id"],
                "output": text,
                "concept_hits": hits,
                "min_hits": probe["min_hits"],
                "smoke_pass": hits >= probe["min_hits"],
            })

    all_pass = all(r["smoke_pass"] for r in results)
    receipt = {
        "schema": "PROJECT_BRAIN_FLAN_T5_SMALL_INT8_PUBLIC_SMOKE_RECEIPT_V1",
        "status": "PASS" if all_pass else "FAIL",
        "exact_learned_bytes": total,
        "max_learned_bytes": MAX_LEARNED_BYTES,
        "artifact_hashes_verified": True,
        "network_disabled_after_prefetch": True,
        "external_learned_provider_calls_during_inference": 0,
        "provider": "CPUExecutionProvider",
        "probes": results,
        "hard_nonclaim": "SMOKE_PASS_IS_NOT_LIVEBENCH_ACCEPTANCE_OR_OPUS55_PARITY",
    }
    out = ROOT / "flan_t5_small_int8_public_smoke_receipt.json"
    out.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))
    assert all_pass, "SEMANTIC_SMOKE_FAILED"


if __name__ == "__main__":
    main()
