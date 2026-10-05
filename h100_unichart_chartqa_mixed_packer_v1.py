"""Real mixed-precision packer for UniChart ChartQA.

Loads the pinned Hugging Face PyTorch state_dict on CPU using torch.load with
weights_only=True, verifies the expected architecture partition, and emits a
deterministic H100UCQ2 packed file:
- encoder.* F32 tensors -> affine W4, group size 256
- decoder.* F32 tensors -> affine W3, group size 256
- I64 tensors -> lossless raw bytes

Each quantized group stores FP16 scale + FP16 offset plus fixed-width packed
codes. Last-group metadata is computed only from real values; code padding is
added afterwards.

This is a storage/transform experiment only. It does not prove capability
preservation.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
import struct
from pathlib import Path
from typing import Any

import numpy as np
import torch

MAGIC = b"H100UCQ2"
SCHEMA = "PROJECT_BRAIN_H100_UNICHART_CHARTQA_MIXED_PACK_V1"
GROUP_SIZE = 256
EXPECTED_F32 = 201_858_168
EXPECTED_I64 = 200_000
EXPECTED_ENCODER_F32 = 74_180_728
EXPECTED_DECODER_F32 = 127_677_440
H100_BUDGET_BYTES = 100_000_000


class PackError(RuntimeError):
    pass


def sha256_file(path: Path, chunk: int = 8 * 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _normalize_state_dict(obj: Any) -> dict[str, torch.Tensor]:
    if isinstance(obj, dict) and obj and all(torch.is_tensor(v) for v in obj.values()):
        return dict(obj)
    if isinstance(obj, dict) and isinstance(obj.get("state_dict"), dict):
        sd = obj["state_dict"]
        if sd and all(torch.is_tensor(v) for v in sd.values()):
            return dict(sd)
    raise PackError("PYTORCH_OBJECT_NOT_PLAIN_STATE_DICT")


def load_state_dict(path: Path) -> dict[str, torch.Tensor]:
    obj = torch.load(path, map_location="cpu", weights_only=True)
    return _normalize_state_dict(obj)


def manifest_rows(sd: dict[str, torch.Tensor]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    f32 = i64 = enc = dec = 0
    for name in sorted(sd):
        t = sd[name]
        dtype = str(t.dtype)
        numel = int(t.numel())
        if t.dtype == torch.float32:
            f32 += numel
            if name.startswith("encoder."):
                enc += numel
                bits = 4
            elif name.startswith("decoder."):
                dec += numel
                bits = 3
            else:
                raise PackError(f"UNCLASSIFIED_F32_TENSOR:{name}")
        elif t.dtype == torch.int64:
            i64 += numel
            bits = None
        else:
            raise PackError(f"UNSUPPORTED_TENSOR_DTYPE:{name}:{dtype}")
        rows.append(
            {
                "name": name,
                "dtype": dtype,
                "shape": list(t.shape),
                "numel": numel,
                "bits": bits,
            }
        )
    if f32 != EXPECTED_F32:
        raise PackError(f"F32_COUNT_MISMATCH:{f32}!={EXPECTED_F32}")
    if i64 != EXPECTED_I64:
        raise PackError(f"I64_COUNT_MISMATCH:{i64}!={EXPECTED_I64}")
    if enc != EXPECTED_ENCODER_F32:
        raise PackError(f"ENCODER_COUNT_MISMATCH:{enc}!={EXPECTED_ENCODER_F32}")
    if dec != EXPECTED_DECODER_F32:
        raise PackError(f"DECODER_COUNT_MISMATCH:{dec}!={EXPECTED_DECODER_F32}")
    return rows


def manifest_sha256(rows: list[dict[str, Any]]) -> str:
    b = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(b).hexdigest()


def _code_bytes(bits: int) -> int:
    if bits == 4:
        return 128
    if bits == 3:
        return 96
    raise PackError(f"BITS_INVALID:{bits}")


def _pack4(q: np.ndarray) -> np.ndarray:
    q = np.asarray(q, dtype=np.uint8).reshape(-1, GROUP_SIZE)
    return (q[:, 0::2] | (q[:, 1::2] << 4)).astype(np.uint8, copy=False)


def _pack3(q: np.ndarray) -> np.ndarray:
    q = np.asarray(q, dtype=np.uint8).reshape(-1, GROUP_SIZE)
    x = q.reshape(q.shape[0], 32, 8).astype(np.uint32)
    w = (
        x[:, :, 0]
        | (x[:, :, 1] << 3)
        | (x[:, :, 2] << 6)
        | (x[:, :, 3] << 9)
        | (x[:, :, 4] << 12)
        | (x[:, :, 5] << 15)
        | (x[:, :, 6] << 18)
        | (x[:, :, 7] << 21)
    )
    out = np.empty((q.shape[0], 96), dtype=np.uint8)
    out[:, 0::3] = (w & 0xFF).astype(np.uint8)
    out[:, 1::3] = ((w >> 8) & 0xFF).astype(np.uint8)
    out[:, 2::3] = ((w >> 16) & 0xFF).astype(np.uint8)
    return out


def unpack4(blob: bytes, groups: int) -> np.ndarray:
    b = np.frombuffer(blob, dtype=np.uint8).reshape(groups, 128)
    q = np.empty((groups, GROUP_SIZE), dtype=np.uint8)
    q[:, 0::2] = b & 0x0F
    q[:, 1::2] = (b >> 4) & 0x0F
    return q


def unpack3(blob: bytes, groups: int) -> np.ndarray:
    b = np.frombuffer(blob, dtype=np.uint8).reshape(groups, 96)
    lo = b[:, 0::3].astype(np.uint32)
    mi = b[:, 1::3].astype(np.uint32)
    hi = b[:, 2::3].astype(np.uint32)
    w = lo | (mi << 8) | (hi << 16)
    q = np.empty((groups, 32, 8), dtype=np.uint8)
    for i in range(8):
        q[:, :, i] = ((w >> (3 * i)) & 7).astype(np.uint8)
    return q.reshape(groups, GROUP_SIZE)


def _stats_init() -> dict[str, float]:
    return {
        "sse": 0.0,
        "sae": 0.0,
        "source_ss": 0.0,
        "max_abs_error": 0.0,
        "values": 0.0,
    }


def _stats_add(dst: dict[str, float], src: dict[str, float]) -> None:
    dst["sse"] += src["sse"]
    dst["sae"] += src["sae"]
    dst["source_ss"] += src["source_ss"]
    dst["values"] += src["values"]
    dst["max_abs_error"] = max(dst["max_abs_error"], src["max_abs_error"])


def _quantize_matrix(block: np.ndarray, bits: int) -> tuple[np.ndarray, np.ndarray, dict[str, float]]:
    if block.ndim != 2 or block.shape[1] != GROUP_SIZE:
        raise PackError("QUANT_BLOCK_SHAPE_INVALID")
    if not np.isfinite(block).all():
        raise PackError("NONFINITE_WEIGHT")
    levels = (1 << bits) - 1
    mins = block.min(axis=1).astype(np.float32)
    maxs = block.max(axis=1).astype(np.float32)
    raw_scale = (maxs - mins) / np.float32(levels)
    scale16 = raw_scale.astype(np.float16)
    offset16 = mins.astype(np.float16)
    varying = maxs != mins
    if np.any(varying & (scale16 == 0)):
        raise PackError("QUANT_SCALE_UNDERFLOW")
    if not np.isfinite(scale16).all() or not np.isfinite(offset16).all():
        raise PackError("QUANT_METADATA_NONFINITE")
    s = scale16.astype(np.float32)
    o = offset16.astype(np.float32)
    q = np.zeros(block.shape, dtype=np.uint8)
    if np.any(varying):
        qv = np.rint((block[varying] - o[varying, None]) / s[varying, None])
        q[varying] = np.clip(qv, 0, levels).astype(np.uint8)
    recon = o[:, None] + s[:, None] * q.astype(np.float32)
    err = block - recon
    stats = {
        "sse": float(np.sum(err * err, dtype=np.float64)),
        "sae": float(np.sum(np.abs(err), dtype=np.float64)),
        "source_ss": float(np.sum(block * block, dtype=np.float64)),
        "max_abs_error": float(np.max(np.abs(err))) if err.size else 0.0,
        "values": float(block.size),
    }
    meta = np.empty((block.shape[0], 2), dtype="<f2")
    meta[:, 0] = scale16
    meta[:, 1] = offset16
    codes = _pack4(q) if bits == 4 else _pack3(q)
    return meta.view(np.uint8).reshape(block.shape[0], 4), codes, stats


def _quantize_partial(values: np.ndarray, bits: int) -> tuple[bytes, dict[str, float]]:
    values = np.asarray(values, dtype=np.float32).reshape(-1)
    if not (0 < values.size < GROUP_SIZE):
        raise PackError("PARTIAL_GROUP_INVALID")
    if not np.isfinite(values).all():
        raise PackError("NONFINITE_WEIGHT")
    levels = (1 << bits) - 1
    mn = np.float32(values.min())
    mx = np.float32(values.max())
    raw_scale = np.float32(0.0 if mx == mn else (mx - mn) / np.float32(levels))
    scale16 = np.float16(raw_scale)
    offset16 = np.float16(mn)
    if mx != mn and scale16 == 0:
        raise PackError("QUANT_SCALE_UNDERFLOW")
    s = np.float32(scale16)
    o = np.float32(offset16)
    q_real = np.zeros(values.size, dtype=np.uint8)
    if mx != mn:
        q_real = np.clip(np.rint((values - o) / s), 0, levels).astype(np.uint8)
    recon = o + s * q_real.astype(np.float32)
    err = values - recon
    q = np.zeros((1, GROUP_SIZE), dtype=np.uint8)
    q[0, : values.size] = q_real
    codes = _pack4(q) if bits == 4 else _pack3(q)
    meta = np.asarray([scale16, offset16], dtype="<f2").view(np.uint8).tobytes()
    return meta + codes.tobytes(), {
        "sse": float(np.sum(err * err, dtype=np.float64)),
        "sae": float(np.sum(np.abs(err), dtype=np.float64)),
        "source_ss": float(np.sum(values * values, dtype=np.float64)),
        "max_abs_error": float(np.max(np.abs(err))) if err.size else 0.0,
        "values": float(values.size),
    }


def _output_header(rows: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    cursor = 0
    out_rows = []
    for row in rows:
        numel = int(row["numel"])
        bits = row["bits"]
        if bits is None:
            storage = "I64_RAW"
            groups = 0
            record_bytes = 0
            length = numel * 8
        else:
            groups = math.ceil(numel / GROUP_SIZE) if numel else 0
            record_bytes = 4 + _code_bytes(int(bits))
            length = groups * record_bytes
            storage = f"QAFFINE_W{bits}_G{GROUP_SIZE}_F16_SCALE_OFFSET"
        out_rows.append({
            **row,
            "storage": storage,
            "group_size": GROUP_SIZE if bits else None,
            "group_count": groups,
            "record_bytes": record_bytes,
            "packed_data_start": cursor,
            "packed_data_end": cursor + length,
        })
        cursor += length
    header = {
        "schema": SCHEMA,
        "source_manifest_sha256": manifest_sha256(rows),
        "quantization": {
            "encoder_f32_bits": 4,
            "decoder_f32_bits": 3,
            "group_size": GROUP_SIZE,
            "metadata": "FP16_SCALE_PLUS_FP16_OFFSET",
            "rounding": "NUMPY_RINT_TIES_TO_EVEN",
            "group_boundary": "RESET_PER_TENSOR",
            "last_group_rule": "METADATA_FROM_REAL_VALUES_THEN_ZERO_PAD_CODES",
        },
        "tensor_count": len(rows),
        "payload_bytes": cursor,
        "tensors": out_rows,
    }
    return header, out_rows


def pack_state_dict_file(
    source_bin: Path,
    output: Path,
    *,
    groups_per_chunk: int = 4096,
) -> dict[str, Any]:
    sd = load_state_dict(source_bin)
    rows = manifest_rows(sd)
    src_manifest = manifest_sha256(rows)
    header, out_rows = _output_header(rows)
    header_bytes = json.dumps(header, sort_keys=True, separators=(",", ":")).encode("utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    stats = {"encoder": _stats_init(), "decoder": _stats_init()}

    with output.open("wb") as out:
        out.write(MAGIC)
        out.write(struct.pack("<Q", len(header_bytes)))
        out.write(header_bytes)
        for row in out_rows:
            name = row["name"]
            t = sd.pop(name)
            numel = int(row["numel"])
            bits = row["bits"]
            if bits is None:
                arr = t.detach().cpu().contiguous().view(-1).numpy().astype("<i8", copy=False)
                out.write(arr.tobytes(order="C"))
                del arr, t
                gc.collect()
                continue

            arr = t.detach().cpu().contiguous().view(-1).numpy()
            if arr.dtype != np.float32:
                raise PackError(f"NUMPY_DTYPE_MISMATCH:{name}:{arr.dtype}")
            part = "encoder" if int(bits) == 4 else "decoder"
            full_groups = numel // GROUP_SIZE
            rem = numel % GROUP_SIZE
            done = 0
            while done < full_groups:
                g = min(groups_per_chunk, full_groups - done)
                start = done * GROUP_SIZE
                block = np.array(
                    arr[start : start + g * GROUP_SIZE],
                    dtype=np.float32,
                    copy=True,
                ).reshape(g, GROUP_SIZE)
                meta, codes, st = _quantize_matrix(block, int(bits))
                records = np.empty((g, 4 + _code_bytes(int(bits))), dtype=np.uint8)
                records[:, :4] = meta
                records[:, 4:] = codes
                out.write(records.tobytes(order="C"))
                _stats_add(stats[part], st)
                done += g
            if rem:
                record, st = _quantize_partial(arr[full_groups * GROUP_SIZE :], int(bits))
                out.write(record)
                _stats_add(stats[part], st)
            del arr, t
            gc.collect()

    if sd:
        raise PackError(f"UNCONSUMED_STATE_DICT_KEYS:{len(sd)}")
    expected = len(MAGIC) + 8 + len(header_bytes) + int(header["payload_bytes"])
    actual = output.stat().st_size
    if actual != expected:
        raise PackError(f"OUTPUT_SIZE_MISMATCH:{actual}!={expected}")

    for part in ("encoder", "decoder"):
        s = stats[part]
        n = int(s["values"])
        s["values"] = n
        s["rmse"] = math.sqrt(s["sse"] / n) if n else 0.0
        s["mae"] = s["sae"] / n if n else 0.0
        s["relative_mse"] = s["sse"] / s["source_ss"] if s["source_ss"] else 0.0

    return {
        "schema": "PROJECT_BRAIN_H100_UNICHART_CHARTQA_REAL_PACK_RECEIPT_V1",
        "status": "PASS__REAL_CHARTQA_MIXED_W4_ENCODER_W3_DECODER_CHECKPOINT_CREATED"
        if actual <= H100_BUDGET_BYTES else "FAIL__CHECKPOINT_EXCEEDS_H100",
        "source_state_manifest_sha256": src_manifest,
        "tensor_count": len(rows),
        "f32_elements": EXPECTED_F32,
        "i64_elements": EXPECTED_I64,
        "encoder_f32_elements": EXPECTED_ENCODER_F32,
        "decoder_f32_elements": EXPECTED_DECODER_F32,
        "packed_checkpoint_bytes": actual,
        "packed_checkpoint_sha256": sha256_file(output),
        "h100_budget_bytes": H100_BUDGET_BYTES,
        "packed_checkpoint_margin_bytes": H100_BUDGET_BYTES - actual,
        "quantization_error": stats,
        "hard_nonclaims": [
            "REAL_PACKED_FILE_DOES_NOT_PROVE_CHARTQA_CAPABILITY_PRESERVATION",
            "NO_CHARTOGRAPHY_THRESHOLD_CREDIT",
            "NO_H100_TERMINAL_CREDIT",
        ],
        "h100_credit_delta": 0,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-bin", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--receipt", required=True)
    ap.add_argument("--groups-per-chunk", type=int, default=4096)
    args = ap.parse_args()
    receipt = pack_state_dict_file(
        Path(args.source_bin),
        Path(args.output),
        groups_per_chunk=args.groups_per_chunk,
    )
    Path(args.receipt).write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
