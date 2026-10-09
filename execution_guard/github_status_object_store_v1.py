#!/usr/bin/env python3
"""Durable GitHub commit-status object store for serialized terminal execution.

This store intentionally does NOT claim multi-writer compare-and-swap. The
terminal execution workflow must provide single-writer serialization (currently
via one fixed GitHub Actions concurrency group). Under that premise, this module
provides durable create/read semantics using only the commit-status permission
that is live on pull_request Actions tokens.

Objects are canonical JSON, zlib-compressed, base64url-encoded, split across
status descriptions, and committed by publishing the manifest status LAST.
Without a valid manifest the object is absent. After a manifest exists, missing
or conflicting chunks are corruption and fail closed.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import zlib
from typing import Any, Callable

SCHEMA = "PROJECT_BRAIN_GITHUB_STATUS_OBJECT_STORE_V1"
CHUNK_CHARS = 100
MAX_OBJECT_BYTES = 16384
MAX_PAGES = 100
PAGE_SIZE = 100
STATUS_STATE = "success"

Request = Callable[
    [str, str, dict[str, Any] | None],
    tuple[int, Any, dict[str, Any]],
]


class StatusObjectStoreError(RuntimeError):
    pass


def _canon(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except Exception as exc:
        raise StatusObjectStoreError("OBJECT_NOT_CANONICAL_JSON") from exc


def _hex(value: Any, n: int) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{%d}" % n, value) is not None


def _nonempty(value: Any, label: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise StatusObjectStoreError("INVALID_" + label.upper())
    return value.strip()


def _same(left: Any, right: Any) -> bool:
    return _canon(left) == _canon(right)


class SerializedStatusObjectStore:
    """Commit-status-backed store requiring an externally serialized writer."""

    def __init__(
        self,
        request: Request,
        repo: str,
        commit_sha: str,
        namespace: str,
    ) -> None:
        if not callable(request):
            raise StatusObjectStoreError("REQUEST_CALLABLE_REQUIRED")
        self.request = request
        self.repo = _nonempty(repo, "repo", 256)
        if not _hex(commit_sha, 40):
            raise StatusObjectStoreError("COMMIT_SHA_INVALID")
        self.commit_sha = commit_sha
        self.namespace = _nonempty(namespace, "namespace", 128)
        self.namespace_hash = hashlib.sha256(self.namespace.encode()).hexdigest()[:12]

    def _key_hash(self, key: str) -> str:
        key = _nonempty(key, "key", 4096)
        return hashlib.sha256(key.encode()).hexdigest()

    def _prefix(self, key: str) -> str:
        # 6 + 12 + 1 + 64 = 83 chars before suffix, below GitHub's context limit.
        return "pb/s1/" + self.namespace_hash + "/" + self._key_hash(key)

    def _manifest_context(self, key: str) -> str:
        return self._prefix(key) + "/m"

    def _chunk_context(self, key: str, index: int) -> str:
        if not isinstance(index, int) or isinstance(index, bool) or index < 0 or index > 999:
            raise StatusObjectStoreError("CHUNK_INDEX_INVALID")
        return self._prefix(key) + "/c" + f"{index:03d}"

    def _post_status(self, context: str, description: str) -> None:
        if len(context) > 100:
            raise StatusObjectStoreError("STATUS_CONTEXT_TOO_LONG")
        if len(description) > 140:
            raise StatusObjectStoreError("STATUS_DESCRIPTION_TOO_LONG")
        status, body, _headers = self.request(
            "POST",
            f"/repos/{self.repo}/statuses/{self.commit_sha}",
            {
                "state": STATUS_STATE,
                "context": context,
                "description": description,
            },
        )
        if status != 201:
            message = body.get("message") if isinstance(body, dict) else "NON_OBJECT"
            raise StatusObjectStoreError(
                "STATUS_WRITE_FAILED:" + str(status) + ":" + str(message)
            )

    def _all_statuses(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for page in range(1, MAX_PAGES + 1):
            status, body, _headers = self.request(
                "GET",
                f"/repos/{self.repo}/commits/{self.commit_sha}/statuses"
                f"?per_page={PAGE_SIZE}&page={page}",
                None,
            )
            if status != 200 or not isinstance(body, list):
                raise StatusObjectStoreError("STATUS_READ_FAILED:" + str(status))
            rows = [row for row in body if isinstance(row, dict)]
            out.extend(rows)
            if len(body) < PAGE_SIZE:
                return out
        raise StatusObjectStoreError("STATUS_PAGINATION_LIMIT_EXCEEDED")

    @staticmethod
    def _unique_description(rows: list[dict[str, Any]], *, label: str) -> str:
        descriptions = {
            row.get("description")
            for row in rows
            if row.get("state") == STATUS_STATE and isinstance(row.get("description"), str)
        }
        if not descriptions:
            raise StatusObjectStoreError(label + "_MISSING")
        if len(descriptions) != 1:
            raise StatusObjectStoreError(label + "_CONFLICT")
        return next(iter(descriptions))

    def read(self, key: str) -> dict[str, Any] | None:
        prefix = self._prefix(key)
        rows = [
            row
            for row in self._all_statuses()
            if isinstance(row.get("context"), str)
            and row["context"].startswith(prefix + "/")
        ]
        manifest_rows = [
            row for row in rows if row.get("context") == self._manifest_context(key)
        ]
        if not manifest_rows:
            # Chunks without a manifest are an uncommitted partial write.
            return None
        manifest = self._unique_description(manifest_rows, label="MANIFEST")
        parts = manifest.split(":")
        if (
            len(parts) != 5
            or parts[0] != "M1"
            or not _hex(parts[1], 64)
        ):
            raise StatusObjectStoreError("MANIFEST_INVALID")
        object_sha = parts[1]
        try:
            chunk_count = int(parts[2])
            raw_len = int(parts[3])
            compressed_len = int(parts[4])
        except Exception as exc:
            raise StatusObjectStoreError("MANIFEST_NUMERIC_INVALID") from exc
        if not 1 <= chunk_count <= 1000:
            raise StatusObjectStoreError("MANIFEST_CHUNK_COUNT_INVALID")
        if not 2 <= raw_len <= MAX_OBJECT_BYTES:
            raise StatusObjectStoreError("MANIFEST_RAW_LENGTH_INVALID")
        if not 1 <= compressed_len <= MAX_OBJECT_BYTES * 2:
            raise StatusObjectStoreError("MANIFEST_COMPRESSED_LENGTH_INVALID")

        encoded_parts: list[str] = []
        for index in range(chunk_count):
            context = self._chunk_context(key, index)
            chunk_rows = [row for row in rows if row.get("context") == context]
            desc = self._unique_description(
                chunk_rows, label="CHUNK_" + str(index)
            )
            if not desc.startswith("C1:"):
                raise StatusObjectStoreError("CHUNK_FORMAT_INVALID:" + str(index))
            encoded_parts.append(desc[3:])

        try:
            compressed = base64.urlsafe_b64decode("".join(encoded_parts).encode("ascii"))
        except Exception as exc:
            raise StatusObjectStoreError("OBJECT_BASE64_INVALID") from exc
        if len(compressed) != compressed_len:
            raise StatusObjectStoreError("OBJECT_COMPRESSED_LENGTH_MISMATCH")
        try:
            raw = zlib.decompress(compressed)
        except Exception as exc:
            raise StatusObjectStoreError("OBJECT_ZLIB_INVALID") from exc
        if len(raw) != raw_len:
            raise StatusObjectStoreError("OBJECT_RAW_LENGTH_MISMATCH")
        if hashlib.sha256(raw).hexdigest() != object_sha:
            raise StatusObjectStoreError("OBJECT_SHA256_MISMATCH")
        try:
            value = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            raise StatusObjectStoreError("OBJECT_JSON_INVALID") from exc
        if not isinstance(value, dict):
            raise StatusObjectStoreError("OBJECT_DICT_REQUIRED")
        if _canon(value) != raw:
            raise StatusObjectStoreError("OBJECT_NONCANONICAL_BYTES")
        return value

    def create(self, key: str, value: dict[str, Any]) -> bool:
        if not isinstance(value, dict):
            raise StatusObjectStoreError("OBJECT_DICT_REQUIRED")
        existing = self.read(key)
        if existing is not None:
            return False

        raw = _canon(value)
        if len(raw) > MAX_OBJECT_BYTES:
            raise StatusObjectStoreError("OBJECT_TOO_LARGE")
        object_sha = hashlib.sha256(raw).hexdigest()
        compressed = zlib.compress(raw, level=9)
        encoded = base64.urlsafe_b64encode(compressed).decode("ascii")
        chunks = [
            encoded[i : i + CHUNK_CHARS]
            for i in range(0, len(encoded), CHUNK_CHARS)
        ]
        if not chunks:
            raise StatusObjectStoreError("OBJECT_CHUNKS_EMPTY")
        if len(chunks) > 1000:
            raise StatusObjectStoreError("OBJECT_TOO_MANY_CHUNKS")

        # Transaction rule: publish every payload chunk first, then manifest last.
        # A crash before the manifest leaves read(key)==None.
        for index, chunk in enumerate(chunks):
            self._post_status(self._chunk_context(key, index), "C1:" + chunk)
        manifest = (
            "M1:"
            + object_sha
            + ":"
            + str(len(chunks))
            + ":"
            + str(len(raw))
            + ":"
            + str(len(compressed))
        )
        self._post_status(self._manifest_context(key), manifest)

        persisted = self.read(key)
        if persisted is None:
            raise StatusObjectStoreError("POSTWRITE_OBJECT_MISSING")
        if not _same(persisted, value):
            raise StatusObjectStoreError("POSTWRITE_OBJECT_MISMATCH")
        return True


__all__ = [
    "SCHEMA",
    "SerializedStatusObjectStore",
    "StatusObjectStoreError",
]
