#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import sys
import urllib.request

ARTIFACTS = {
    "encoder_model_int8.onnx": {
        "url": "https://huggingface.co/onnx-community/flan-t5-small-ONNX/resolve/76988c16f73cadb2c2e13e2d7d85608944223105/onnx/encoder_model_int8.onnx?download=true",
        "bytes": 35720521,
        "sha256": "691c4b521a2aad8ff0d1a94e578f507bbfb7b3d939b5b4d233c4a8043a2388dc",
    },
    "decoder_model_int8.onnx": {
        "url": "https://huggingface.co/onnx-community/flan-t5-small-ONNX/resolve/76988c16f73cadb2c2e13e2d7d85608944223105/onnx/decoder_model_int8.onnx?download=true",
        "bytes": 58862707,
        "sha256": "54e7e2e606115068b979fe83cd64f23ee48b7cfde750f3ca9c48ea493bee5c86",
    },
    "spiece.model": {
        "url": "https://huggingface.co/google/flan-t5-small/resolve/e48659520aaf0069046c3413e9835d214fefa83c/spiece.model?download=true",
        "bytes": 791656,
        "sha256": "d60acb128cf7b7f2536e8f38a5b18a05535c9e14c7a355904270e15b0945ea86",
    },
}
EXPECTED_TOTAL = 95_374_884
EXPECTED_HEADROOM = 4_625_116
MAX_LEARNED_BYTES = 100_000_000


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_one(path: pathlib.Path, spec: dict) -> dict:
    size = path.stat().st_size
    digest = sha256_file(path)
    if size != spec["bytes"]:
        raise RuntimeError(f"SIZE_MISMATCH:{path.name}:{size}!={spec['bytes']}")
    if digest != spec["sha256"]:
        raise RuntimeError(f"SHA256_MISMATCH:{path.name}:{digest}!={spec['sha256']}")
    return {"bytes": size, "sha256": digest}


def prepare(root: pathlib.Path) -> dict:
    root.mkdir(parents=True, exist_ok=True)
    verified = {}
    for name, spec in ARTIFACTS.items():
        path = root / name
        if not path.exists():
            req = urllib.request.Request(spec["url"], headers={"User-Agent": "project-brain-verifier/1"})
            with urllib.request.urlopen(req, timeout=180) as src, path.open("wb") as dst:
                while True:
                    chunk = src.read(1024 * 1024)
                    if not chunk:
                        break
                    dst.write(chunk)
        verified[name] = verify_one(path, spec)
    total = sum(row["bytes"] for row in verified.values())
    if total != EXPECTED_TOTAL:
        raise RuntimeError(f"LEARNED_TOTAL_MISMATCH:{total}")
    return {
        "prepared": True,
        "learned_bytes_total": total,
        "headroom_bytes": MAX_LEARNED_BYTES - total,
        "artifacts": verified,
    }


def assert_no_external_tensor_data(model_path: pathlib.Path) -> dict:
    import onnx

    model = onnx.load_model(str(model_path), load_external_data=False)
    external = []
    tensors = list(model.graph.initializer)
    tensors.extend(x.values for x in model.graph.sparse_initializer)
    flat = []
    for t in tensors:
        if isinstance(t, (list, tuple)):
            flat.extend(t)
        else:
            flat.append(t)
    for tensor in flat:
        if getattr(tensor, "data_location", 0) == onnx.TensorProto.EXTERNAL or len(getattr(tensor, "external_data", [])):
            external.append(getattr(tensor, "name", "<unnamed>"))
    if external:
        raise RuntimeError("EXTERNAL_TENSOR_DATA:" + ",".join(external[:20]))
    return {"initializer_count": len(flat), "external_initializer_count": 0}


def tensor_payload_fingerprints(model_path: pathlib.Path) -> dict:
    import collections
    import onnx
    from onnx import numpy_helper

    model = onnx.load_model(str(model_path), load_external_data=False)
    counts = collections.Counter()
    bytes_by_fp = {}
    rows = []
    for tensor in model.graph.initializer:
        arr = numpy_helper.to_array(tensor)
        payload = arr.tobytes(order="C")
        h = hashlib.sha256()
        h.update(str(arr.dtype).encode("utf-8"))
        h.update(b"\\0")
        h.update(json.dumps(list(arr.shape)).encode("utf-8"))
        h.update(b"\\0")
        h.update(payload)
        fp = h.hexdigest()
        counts[fp] += 1
        bytes_by_fp[fp] = len(payload)
        rows.append({
            "name": tensor.name,
            "fingerprint": fp,
            "payload_bytes": len(payload),
            "shape": list(arr.shape),
            "dtype": str(arr.dtype),
        })
    return {
        "initializer_payload_bytes": sum(x["payload_bytes"] for x in rows),
        "fingerprint_counts": dict(counts),
        "bytes_by_fingerprint": bytes_by_fp,
        "initializers": rows,
    }


def cross_model_dedup_diagnostic(encoder_path: pathlib.Path, decoder_path: pathlib.Path) -> dict:
    enc = tensor_payload_fingerprints(encoder_path)
    dec = tensor_payload_fingerprints(decoder_path)
    shared = []
    shared_bytes = 0
    for fp in sorted(set(enc["fingerprint_counts"]) & set(dec["fingerprint_counts"])):
        copies = min(enc["fingerprint_counts"][fp], dec["fingerprint_counts"][fp])
        payload_bytes = enc["bytes_by_fingerprint"][fp]
        saving = copies * payload_bytes
        shared_bytes += saving
        shared.append({
            "fingerprint": fp,
            "payload_bytes_each": payload_bytes,
            "cross_model_duplicate_copies": copies,
            "potential_saving_bytes": saving,
        })
    total_payload = enc["initializer_payload_bytes"] + dec["initializer_payload_bytes"]
    return {
        "encoder_initializer_payload_bytes": enc["initializer_payload_bytes"],
        "decoder_initializer_payload_bytes": dec["initializer_payload_bytes"],
        "combined_initializer_payload_bytes": total_payload,
        "cross_model_identical_tensor_groups": len(shared),
        "cross_model_duplicate_payload_bytes": shared_bytes,
        "unique_payload_lower_bound_bytes": total_payload - shared_bytes,
        "shared_groups": shared,
        "interpretation": (
            "Diagnostic only. Nonzero duplicate payload proves byte-identical tensors exist "
            "across the split encoder/decoder artifacts and may be physically deduplicated "
            "only after a separately verified runtime preserves exact semantics."
        ),
    }


def _sp_encode(sp, text: str) -> list[int]:
    ids = list(sp.encode(text, out_type=int))
    if not ids or ids[-1] != 1:
        ids.append(1)
    return ids


def _sp_decode(sp, ids: list[int]) -> str:
    clean = [int(x) for x in ids if int(x) not in (0, 1) and int(x) < sp.get_piece_size()]
    return sp.decode(clean).strip()


def offline_smoke(root: pathlib.Path, receipt_path: pathlib.Path) -> dict:
    import numpy as np
    import onnx
    import onnxruntime as ort
    import sentencepiece as sentencepiece

    verified = {name: verify_one(root / name, spec) for name, spec in ARTIFACTS.items()}
    total = sum(row["bytes"] for row in verified.values())
    if total != EXPECTED_TOTAL or MAX_LEARNED_BYTES - total != EXPECTED_HEADROOM:
        raise RuntimeError("H100_ARITHMETIC_MISMATCH")

    ext = {
        "encoder": assert_no_external_tensor_data(root / "encoder_model_int8.onnx"),
        "decoder": assert_no_external_tensor_data(root / "decoder_model_int8.onnx"),
    }

    dedup = cross_model_dedup_diagnostic(
        root / "encoder_model_int8.onnx",
        root / "decoder_model_int8.onnx",
    )

    sp = sentencepiece.SentencePieceProcessor(model_file=str(root / "spiece.model"))
    if sp.get_piece_size() != 32000:
        raise RuntimeError(f"UNEXPECTED_SENTENCEPIECE_SIZE:{sp.get_piece_size()}")

    so = ort.SessionOptions()
    so.intra_op_num_threads = 2
    so.inter_op_num_threads = 1
    encoder = ort.InferenceSession(str(root / "encoder_model_int8.onnx"), sess_options=so, providers=["CPUExecutionProvider"])
    decoder = ort.InferenceSession(str(root / "decoder_model_int8.onnx"), sess_options=so, providers=["CPUExecutionProvider"])

    encoder_inputs = [x.name for x in encoder.get_inputs()]
    encoder_outputs = [x.name for x in encoder.get_outputs()]
    decoder_inputs = [x.name for x in decoder.get_inputs()]
    decoder_outputs = [x.name for x in decoder.get_outputs()]

    if "input_ids" not in encoder_inputs:
        raise RuntimeError(f"ENCODER_INPUT_ABI_UNEXPECTED:{encoder_inputs}")
    if "input_ids" not in decoder_inputs or "encoder_hidden_states" not in decoder_inputs:
        raise RuntimeError(f"DECODER_INPUT_ABI_UNEXPECTED:{decoder_inputs}")

    def generate(prompt: str, max_new_tokens: int = 64) -> dict:
        enc_ids = np.asarray([_sp_encode(sp, prompt)], dtype=np.int64)
        enc_mask = np.ones_like(enc_ids, dtype=np.int64)
        enc_feed = {}
        for name in encoder_inputs:
            if name == "input_ids":
                enc_feed[name] = enc_ids
            elif name == "attention_mask":
                enc_feed[name] = enc_mask
            else:
                raise RuntimeError(f"UNHANDLED_ENCODER_INPUT:{name}")
        enc_hidden = encoder.run(None, enc_feed)[0]

        generated = [0]
        for _ in range(max_new_tokens):
            dec_ids = np.asarray([generated], dtype=np.int64)
            dec_feed = {}
            for name in decoder_inputs:
                if name == "input_ids":
                    dec_feed[name] = dec_ids
                elif name == "encoder_hidden_states":
                    dec_feed[name] = enc_hidden
                elif name in ("encoder_attention_mask", "attention_mask"):
                    dec_feed[name] = enc_mask
                else:
                    raise RuntimeError(f"UNHANDLED_DECODER_INPUT:{name}")
            outs = decoder.run(None, dec_feed)
            logits = outs[0]
            if logits.ndim != 3 or logits.shape[0] != 1:
                raise RuntimeError(f"LOGITS_SHAPE_UNEXPECTED:{tuple(logits.shape)}")
            token = int(np.argmax(logits[0, -1]))
            generated.append(token)
            if token == 1:
                break
        text = _sp_decode(sp, generated)
        if not text:
            raise RuntimeError("EMPTY_GENERATION")
        return {
            "prompt": prompt,
            "output": text,
            "generated_ids": generated,
            "new_token_count": len(generated) - 1,
        }

    probes = {
        "paraphrase": generate("Paraphrase the following sentence while preserving its meaning: The scientist carefully checked every result before publishing it.", 48),
        "simplify": generate("Rewrite this so a child can understand it: Although the weather deteriorated rapidly, the expedition continued because the team had prepared for severe conditions.", 48),
        "summarize": generate("Summarize: Solar panels convert sunlight into electricity. Their output changes with sunlight intensity, panel angle, temperature, and shading. Batteries can store excess daytime electricity for later use.", 48),
        "story_generation": generate("Write a short story about a child who finds a clock that runs backward.", 80),
    }

    for name, row in probes.items():
        if not row["output"].strip():
            raise RuntimeError(f"EMPTY_PROBE:{name}")

    def norm_words(text: str) -> set[str]:
        import re
        return set(re.findall(r"[a-z]+", text.lower()))

    def has_any(words: set[str], options: set[str]) -> bool:
        return bool(words & options)

    semantic_checks = {}

    p = probes["paraphrase"]["output"]
    pw = norm_words(p)
    semantic_checks["paraphrase"] = {
        "not_verbatim": p.strip().lower() != "the scientist carefully checked every result before publishing it.",
        "agent_retained": has_any(pw, {"scientist", "researcher"}),
        "inspection_retained": has_any(pw, {"check", "checked", "checking", "examine", "examined", "review", "reviewed", "verify", "verified", "inspect", "inspected"}),
        "result_retained": has_any(pw, {"result", "results", "finding", "findings"}),
        "publication_retained": has_any(pw, {"publish", "published", "publishing", "publication", "release", "released", "public"}),
    }
    semantic_checks["paraphrase"]["pass"] = all(semantic_checks["paraphrase"].values())

    s = probes["simplify"]["output"]
    sw = norm_words(s)
    semantic_checks["simplify"] = {
        "weather_retained": has_any(sw, {"weather", "storm", "conditions"}),
        "continuation_retained": has_any(sw, {"continue", "continued", "continuing", "kept", "went"}),
        "preparation_retained": has_any(sw, {"prepare", "prepared", "ready", "planned"}),
        "simpler_length": len(sw) <= 24,
    }
    semantic_checks["simplify"]["pass"] = all(semantic_checks["simplify"].values())

    m = probes["summarize"]["output"]
    mw = norm_words(m)
    semantic_checks["summarize"] = {
        "solar_retained": has_any(mw, {"solar", "sunlight", "sun"}),
        "electricity_retained": has_any(mw, {"electricity", "electric", "power", "energy"}),
        "storage_retained": has_any(mw, {"battery", "batteries", "store", "stores", "stored", "storage"}),
        "short_summary": len(mw) <= 32,
    }
    semantic_checks["summarize"]["pass"] = all(semantic_checks["summarize"].values())

    g = probes["story_generation"]["output"]
    gw = norm_words(g)
    semantic_checks["story_generation"] = {
        "child_retained": has_any(gw, {"child", "boy", "girl", "kid"}),
        "clock_retained": has_any(gw, {"clock", "timepiece", "watch"}),
        "reverse_time_retained": has_any(gw, {"backward", "backwards", "reverse", "reversed"}),
        "minimum_story_length": len(gw) >= 20,
    }
    semantic_checks["story_generation"]["pass"] = all(semantic_checks["story_generation"].values())

    semantic_smoke_pass = all(x["pass"] for x in semantic_checks.values())

    receipt = {
        "schema": "PROJECT_BRAIN_FLAN_T5_SMALL_INT8_SEMANTIC_SMOKE_V1",
        "status": (
            "PASS__RESOURCE_EXECUTION_AND_MINIMUM_SEMANTIC_SMOKE"
            if semantic_smoke_pass
            else "FAIL__MINIMUM_SEMANTIC_SMOKE"
        ),
        "network_phase": "ARTIFACT_PREFETCH_COMPLETED_BEFORE_OFFLINE_EXECUTION",
        "offline_execution_required": True,
        "learned_bytes_total": total,
        "h100_max_bytes": MAX_LEARNED_BYTES,
        "headroom_bytes": MAX_LEARNED_BYTES - total,
        "artifacts": verified,
        "onnx_external_data": ext,
        "cross_model_tensor_dedup_diagnostic": dedup,
        "abi": {
            "encoder_inputs": encoder_inputs,
            "encoder_outputs": encoder_outputs,
            "decoder_inputs": decoder_inputs,
            "decoder_outputs": decoder_outputs,
            "sentencepiece_piece_count": sp.get_piece_size(),
            "decoder_start_token_id": 0,
            "eos_token_id": 1,
        },
        "runtime_versions": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "onnx": onnx.__version__,
            "onnxruntime": ort.__version__,
            "sentencepiece": getattr(sentencepiece, "__version__", "unknown"),
        },
        "public_nonterminal_smoke_probes": probes,
        "minimum_semantic_checks": semantic_checks,
        "hard_nonclaims": [
            "FOUR_SYNTHETIC_FAIL_FAST_PROBES_ARE_NOT_OPUS_5_5_PARITY_PROOF",
            "PASS_ONLY_MEANS_THE_SUB100MB_CANDIDATE_SURVIVED_A_MINIMUM_SEMANTIC_SMOKE_GATE",
            "NO_OPUS_5_5_EQUIVALENCE_CLAIM",
            "DEDUP_DIAGNOSTIC_DOES_NOT_AUTHORIZE_A_DEDUPLICATED_RUNTIME_OR_REDUCED_H100_ACCOUNTING",
            "NO_LIVEBENCH_THRESHOLD_CLAIM",
            "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
        ],
    }
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    if not semantic_smoke_pass:
        raise SystemExit(2)
    return receipt


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["prepare", "offline"])
    p.add_argument("--root", required=True)
    p.add_argument("--receipt", default="flan_t5_small_int8_semantic_smoke_receipt.json")
    args = p.parse_args()
    root = pathlib.Path(args.root)
    if args.mode == "prepare":
        print(json.dumps(prepare(root), indent=2, sort_keys=True))
    else:
        offline_smoke(root, pathlib.Path(args.receipt))


if __name__ == "__main__":
    main()
