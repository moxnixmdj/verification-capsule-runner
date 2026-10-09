"""Lossless content-addressed evidence frontier for TB-Science planning.

Full observations remain Brain-owned. Planner context receives only a bounded
index plus explicitly selected content-addressed expansions. Large strings are
chunked without semantic summarization, so omission from active context never
means deletion.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Mapping

INLINE_TEXT_CHARS = 512
TEXT_CHUNK_CHARS = 1536
LATEST_RECORD_REFS = 4
MAX_EVIDENCE_REQUESTS = 4


class EvidenceFrontierError(RuntimeError):
    pass


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class EvidenceLedger:
    def __init__(self) -> None:
        self._objects: dict[str, dict[str, Any]] = {}
        self._record_refs: list[str] = []

    def _store(self, value: dict[str, Any]) -> str:
        raw = _canonical_bytes(value)
        ref = "sha256:" + hashlib.sha256(raw).hexdigest()
        existing = self._objects.get(ref)
        if existing is not None and _canonical_bytes(existing) != raw:
            raise EvidenceFrontierError("EVIDENCE_HASH_COLLISION")
        self._objects[ref] = value
        return ref

    def get(self, ref: str) -> dict[str, Any]:
        value = self._objects.get(ref)
        if value is None:
            raise EvidenceFrontierError("EVIDENCE_REF_UNKNOWN:" + str(ref))
        expected = "sha256:" + hashlib.sha256(_canonical_bytes(value)).hexdigest()
        if expected != ref:
            raise EvidenceFrontierError("EVIDENCE_OBJECT_INTEGRITY_MISMATCH:" + ref)
        return value

    def _store_text(self, text: str) -> dict[str, Any]:
        digest = _sha256_text(text)
        if len(text) <= INLINE_TEXT_CHARS:
            return {
                "$inline_text": text,
                "chars": len(text),
                "sha256": digest,
            }

        refs: list[str] = []
        for offset in range(0, len(text), TEXT_CHUNK_CHARS):
            chunk = text[offset: offset + TEXT_CHUNK_CHARS]
            refs.append(self._store({
                "type": "text_chunk",
                "offset_chars": offset,
                "chars": len(chunk),
                "text": chunk,
            }))
        manifest_ref = self._store({
            "type": "text_manifest",
            "chars": len(text),
            "sha256": digest,
            "chunk_refs": refs,
        })
        return {
            "$evidence_text_ref": manifest_ref,
            "chars": len(text),
            "sha256": digest,
        }

    def _compact(self, value: Any) -> Any:
        if isinstance(value, str):
            return self._store_text(value)
        if isinstance(value, Mapping):
            return {
                str(key): self._compact(item)
                for key, item in sorted(value.items(), key=lambda kv: str(kv[0]))
            }
        if isinstance(value, list):
            return [self._compact(item) for item in value]
        if value is None or isinstance(value, (bool, int, float)):
            return value
        raise EvidenceFrontierError(
            "EVIDENCE_VALUE_TYPE_UNSUPPORTED:" + type(value).__name__
        )

    def add_record(self, record: Mapping[str, Any]) -> str:
        if not isinstance(record, Mapping):
            raise EvidenceFrontierError("EVIDENCE_RECORD_OBJECT_REQUIRED")
        compact = self._compact(dict(record))
        ref = self._store({
            "type": "record",
            "ordinal": len(self._record_refs),
            "value": compact,
        })
        self._record_refs.append(ref)
        return ref

    @property
    def record_refs(self) -> tuple[str, ...]:
        return tuple(self._record_refs)

    def manifest_ref(self) -> str:
        return self._store({
            "type": "record_manifest",
            "record_count": len(self._record_refs),
            "record_refs": list(self._record_refs),
        })

    def prompt_index(self) -> dict[str, Any]:
        return {
            "record_count": len(self._record_refs),
            "manifest_ref": self.manifest_ref(),
            "latest_record_refs": list(
                self._record_refs[-LATEST_RECORD_REFS:]
            ),
        }

    def validate_requests(self, refs: Any) -> list[str]:
        if refs is None:
            return []
        if not isinstance(refs, list):
            raise EvidenceFrontierError("EVIDENCE_REQUESTS_NOT_LIST")
        if len(refs) > MAX_EVIDENCE_REQUESTS:
            raise EvidenceFrontierError("EVIDENCE_REQUESTS_TOO_MANY")
        out: list[str] = []
        for ref in refs:
            if (
                not isinstance(ref, str)
                or len(ref) != 71
                or not ref.startswith("sha256:")
            ):
                raise EvidenceFrontierError("EVIDENCE_REQUEST_REF_INVALID")
            try:
                int(ref[7:], 16)
            except Exception as exc:
                raise EvidenceFrontierError("EVIDENCE_REQUEST_REF_INVALID") from exc
            if ref in out:
                raise EvidenceFrontierError("EVIDENCE_REQUEST_REF_DUPLICATE")
            self.get(ref)
            out.append(ref)
        return out

    def expansion_candidates(
        self,
        requested_refs: Iterable[str] = (),
    ) -> list[str]:
        out: list[str] = []
        for ref in list(requested_refs) + list(
            self._record_refs[-LATEST_RECORD_REFS:]
        ):
            if ref not in out:
                self.get(ref)
                out.append(ref)
        return out

    def expansion_rows(self, refs: Iterable[str]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for ref in refs:
            out.append({"ref": ref, "object": self.get(ref)})
        return out

    def reconstruct_text(self, ref: str) -> str:
        manifest = self.get(ref)
        if manifest.get("type") != "text_manifest":
            raise EvidenceFrontierError("EVIDENCE_TEXT_MANIFEST_REQUIRED")
        chunks: list[str] = []
        expected_offset = 0
        for chunk_ref in manifest.get("chunk_refs") or []:
            chunk = self.get(chunk_ref)
            if chunk.get("type") != "text_chunk":
                raise EvidenceFrontierError("EVIDENCE_TEXT_CHUNK_REQUIRED")
            if chunk.get("offset_chars") != expected_offset:
                raise EvidenceFrontierError("EVIDENCE_TEXT_CHUNK_ORDER_INVALID")
            text = chunk.get("text")
            if not isinstance(text, str) or chunk.get("chars") != len(text):
                raise EvidenceFrontierError("EVIDENCE_TEXT_CHUNK_INVALID")
            chunks.append(text)
            expected_offset += len(text)
        text = "".join(chunks)
        if len(text) != manifest.get("chars"):
            raise EvidenceFrontierError("EVIDENCE_TEXT_LENGTH_MISMATCH")
        if _sha256_text(text) != manifest.get("sha256"):
            raise EvidenceFrontierError("EVIDENCE_TEXT_HASH_MISMATCH")
        return text

    def _restore(self, value: Any) -> Any:
        if isinstance(value, list):
            return [self._restore(item) for item in value]
        if not isinstance(value, dict):
            return value
        if "$inline_text" in value:
            text = value.get("$inline_text")
            if not isinstance(text, str):
                raise EvidenceFrontierError("EVIDENCE_INLINE_TEXT_INVALID")
            if len(text) != value.get("chars") or _sha256_text(text) != value.get("sha256"):
                raise EvidenceFrontierError("EVIDENCE_INLINE_TEXT_INTEGRITY_MISMATCH")
            return text
        if "$evidence_text_ref" in value:
            text = self.reconstruct_text(str(value["$evidence_text_ref"]))
            if len(text) != value.get("chars") or _sha256_text(text) != value.get("sha256"):
                raise EvidenceFrontierError("EVIDENCE_TEXT_DESCRIPTOR_MISMATCH")
            return text
        return {key: self._restore(item) for key, item in value.items()}

    def reconstruct_record(self, ref: str) -> dict[str, Any]:
        record = self.get(ref)
        if record.get("type") != "record":
            raise EvidenceFrontierError("EVIDENCE_RECORD_REF_REQUIRED")
        value = self._restore(record.get("value"))
        if not isinstance(value, dict):
            raise EvidenceFrontierError("EVIDENCE_RECONSTRUCTED_RECORD_INVALID")
        return value
