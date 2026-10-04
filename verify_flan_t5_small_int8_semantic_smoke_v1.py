#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import urllib.request
from pathlib import Path

import numpy as np
import onnxruntime as ort
import sentencepiece as spm

REV_ONNX = "76988c16f73cadb2c2e13e2d7d85608944223105"
REV_TOK = "e48659520aaf0069046c3413e9835d214fefa83c"
FILES = {
    "encoder": {
        "url": f"https://huggingface.co/onnx-community/flan-t5-small-ONNX/resolve/{REV_ONNX}/onnx/encoder_model_int8.onnx?download=true",
        "bytes": 35720521,
        "sha256": "691c4b521a2aad8ff0d1a94e578f507bbfb7b3d939b5b4d233c4a8043a2388dc",
        "path": "encoder_model_int8.onnx",
    },
    "decoder": {
        "url": f"https://huggingface.co/onnx-community/flan-t5-small-ONNX/resolve/{REV_ONNX}/onnx/decoder_model_int8.onnx?download=true",
        "bytes": 58862707,
        "sha256": "54e7e2e606115068b979fe83cd64f23ee48b7cfde750f3ca9c48ea493bee5c86",
        "path": "decoder_model_int8.onnx",
    },
    "spiece": {
        "url": f"https://huggingface.co/google/flan-t5-small/resolve/{REV_TOK}/spiece.model?download=true",
        "bytes": 791656,
        "sha256": "d60acb128cf7b7f2536e8f38a5b18a05535c9e14c7a355904270e15b0945ea86",
        "path": "spiece.model",
    },
}
PROBES = {
    "paraphrase": "Paraphrase: The careful scientist checked the measurement twice before publishing the result.",
    "simplify": "Simplify this sentence: Because the storm damaged several power lines, technicians restored electricity in stages so hospitals could receive power first.",
    "summarize": "Summarize: Mara noticed the river rising after two days of rain. She warned the village, helped move supplies uphill, and the old bridge was closed before the flood arrived.",
    "story": "Write a short story about a robot named Nilo who finds a lost brass key in a quiet library and returns it to its owner.",
}

def fetch(spec: dict, root: Path) -> Path:
    dst = root / spec["path"]
    req = urllib.request.Request(spec["url"], headers={"User-Agent": "project-brain-public-verifier"})
    with urllib.request.urlopen(req, timeout=180) as r, dst.open("wb") as f:
        while True:
            chunk = r.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
    data = dst.read_bytes()
    assert len(data) == spec["bytes"], (dst.name, len(data), spec["bytes"])
    got = hashlib.sha256(data).hexdigest()
    assert got == spec["sha256"], (dst.name, got, spec["sha256"])
    return dst

def input_names(session: ort.InferenceSession) -> list[str]:
    return [x.name for x in session.get_inputs()]

def run_encoder(session, ids: np.ndarray, mask: np.ndarray) -> np.ndarray:
    feed = {}
    for name in input_names(session):
        if name == "input_ids":
            feed[name] = ids
        elif name == "attention_mask":
            feed[name] = mask
        else:
            raise AssertionError(f"UNEXPECTED_ENCODER_INPUT:{name}")
    outputs = session.run(None, feed)
    assert outputs and outputs[0].ndim == 3
    return outputs[0]

def run_decoder(session, dec_ids: np.ndarray, enc: np.ndarray, enc_mask: np.ndarray) -> np.ndarray:
    feed = {}
    for name in input_names(session):
        if name == "input_ids":
            feed[name] = dec_ids
        elif name in ("encoder_hidden_states", "encoder_outputs"):
            feed[name] = enc
        elif name in ("encoder_attention_mask", "attention_mask"):
            feed[name] = enc_mask
        else:
            raise AssertionError(f"UNEXPECTED_DECODER_INPUT:{name}")
    outputs = session.run(None, feed)
    assert outputs and outputs[0].ndim == 3
    return outputs[0]

def generate(sp, encoder, decoder, text: str, max_new_tokens: int = 64) -> dict:
    encoded = list(sp.encode(text, out_type=int)) + [1]
    ids = np.asarray([encoded], dtype=np.int64)
    mask = np.ones_like(ids, dtype=np.int64)
    enc = run_encoder(encoder, ids, mask)
    generated = [0]
    for _ in range(max_new_tokens):
        dec_ids = np.asarray([generated], dtype=np.int64)
        logits = run_decoder(decoder, dec_ids, enc, mask)
        token = int(np.argmax(logits[0, -1]))
        if token == 1:
            break
        generated.append(token)
    body = [x for x in generated[1:] if x not in (0, 1)]
    text_out = sp.decode(body).strip()
    return {
        "text": text_out,
        "generated_token_count": len(body),
        "terminated_with_eos": token == 1 if "token" in locals() else False,
    }

def main() -> int:
    root = Path("/tmp/flan_t5_small_int8_verify")
    root.mkdir(parents=True, exist_ok=True)
    paths = {k: fetch(v, root) for k, v in FILES.items()}

    # Network-dependent work is complete here. The remaining execution only
    # consumes the three pinned local artifacts.
    sp = spm.SentencePieceProcessor(model_file=str(paths["spiece"]))
    providers = ["CPUExecutionProvider"]
    encoder = ort.InferenceSession(str(paths["encoder"]), providers=providers)
    decoder = ort.InferenceSession(str(paths["decoder"]), providers=providers)

    outputs = {}
    for task, prompt in PROBES.items():
        result = generate(sp, encoder, decoder, prompt)
        assert result["text"], f"EMPTY_OUTPUT:{task}"
        assert result["generated_token_count"] > 0, f"ZERO_TOKENS:{task}"
        outputs[task] = result
        print(task, json.dumps(result, ensure_ascii=False))

    receipt = {
        "schema": "PROJECT_BRAIN_FLAN_T5_SMALL_INT8_OFFLINE_EXECUTION_SMOKE_V1",
        "status": "PASS_EXECUTION_SMOKE_ONLY__SEMANTIC_QUALITY_NOT_PROMOTED",
        "pinned_public_artifacts": {
            k: {
                "revision": REV_ONNX if k != "spiece" else REV_TOK,
                "bytes": v["bytes"],
                "sha256": v["sha256"],
                "path": v["path"],
            } for k, v in FILES.items()
        },
        "learned_bytes_total": sum(v["bytes"] for v in FILES.values()),
        "runtime": {
            "provider": "CPUExecutionProvider",
            "decoder_mode": "FULL_PREFIX_RECOMPUTATION_NO_PAST",
            "generation": "GREEDY",
            "network_required_after_prefetch": False,
            "unaccounted_external_learned_data_required": False,
        },
        "probe_outputs": outputs,
        "verified_deductions": [
            "EXACT_PINNED_LEARNED_ARTIFACT_SET_FITS_BELOW_100000000_BYTES",
            "ENCODER_DECODER_TOKENIZER_ABI_EXECUTES_END_TO_END",
            "FOUR_PUBLIC_TEXT2TEXT_ROUTES_PRODUCE_NONEMPTY_LOCAL_OUTPUT",
            "NO_SECOND_DECODER_WITH_PAST_LEARNED_ARTIFACT_IS_REQUIRED_FOR_BASIC_GENERATION",
        ],
        "hard_nonclaims": [
            "NONEMPTY_OUTPUT_DOES_NOT_PROVE_SEMANTIC_QUALITY",
            "NO_CLAIM_FLAN_T5_SMALL_EQUALS_OPUS_5_5",
            "NO_LIVEBENCH_ACCEPTANCE_OR_CAPABILITY_CREDIT",
            "NO_TERMINAL_PROMPT_RESPONSE_OR_CASE_READ",
            "NO_CLAIM_PUBLIC_PROBE_OUTPUTS_PASS_A_SEMANTIC_JUDGE",
        ],
        "accounting": {
            "incremental_spend_usd": 0,
            "new_terminal_cases_exposed": 0,
            "acceptance_credit_delta": 0,
        },
    }
    Path("flan_t5_small_int8_offline_execution_smoke_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, sort_keys=True, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
