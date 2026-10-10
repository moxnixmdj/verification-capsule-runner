#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

from execution_guard.content_addressed_runtime_binding_v1 import (
    BoundRuntimeError,
    git_blob_sha,
    resolve_runtime_binding,
)

ROOT = Path(__file__).resolve().parents[2]
SURFACE = "execution_guard/CURRENT_TERMINAL_EXECUTION_SURFACE_V1.json"
RUNNER = ROOT / "capsules/tb_science_rank20_20261010_v1/rank20_v8_status_journal_runner.py"


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, str):
        path.write_text(value, encoding="utf-8")
    else:
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _blob(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def main() -> int:
    resolved = resolve_runtime_binding(
        root=ROOT,
        surface_rel=SURFACE,
        runtime_key="start_cas",
    )
    assert resolved.relative_to(ROOT).as_posix() == (
        "capsules/tb_science_rank20_20261010_v1/rank20_start_cas_v8.py"
    )
    assert git_blob_sha(resolved) == "99d81c7d1316d1767c688e12c2c05790c69662f3"

    source = RUNNER.read_text(encoding="utf-8")
    assert "rank20_start_cas_v7.py" not in source
    assert 'runtime_key="start_cas"' in source
    assert "resolve_runtime_binding" in source

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        runtime = root / "runtime.py"
        _write(runtime, "print('ok')\n")
        behavior = root / "behavior.json"
        _write(
            behavior,
            {
                "runtime_bindings": {
                    "start_cas": {
                        "path": "runtime.py",
                        "git_blob_sha": _blob(runtime),
                    }
                }
            },
        )
        surface = root / "surface.json"
        _write(
            surface,
            {
                "behavior": {
                    "path": "behavior.json",
                    "git_blob_sha": _blob(behavior),
                }
            },
        )
        assert resolve_runtime_binding(
            root=root,
            surface_rel="surface.json",
            runtime_key="start_cas",
        ) == runtime.resolve()

        bad = json.loads(behavior.read_text(encoding="utf-8"))
        bad["runtime_bindings"]["start_cas"]["git_blob_sha"] = "0" * 40
        _write(behavior, bad)
        _write(
            surface,
            {
                "behavior": {
                    "path": "behavior.json",
                    "git_blob_sha": _blob(behavior),
                }
            },
        )
        try:
            resolve_runtime_binding(
                root=root,
                surface_rel="surface.json",
                runtime_key="start_cas",
            )
        except BoundRuntimeError as exc:
            assert str(exc) == "RUNTIME_START_CAS_BLOB_MISMATCH"
        else:
            raise AssertionError("forged runtime blob was accepted")

        outside = root.parent / "outside-runtime.py"
        _write(outside, "print('outside')\n")
        _write(
            behavior,
            {
                "runtime_bindings": {
                    "start_cas": {
                        "path": "../outside-runtime.py",
                        "git_blob_sha": _blob(outside),
                    }
                }
            },
        )
        _write(
            surface,
            {
                "behavior": {
                    "path": "behavior.json",
                    "git_blob_sha": _blob(behavior),
                }
            },
        )
        try:
            resolve_runtime_binding(
                root=root,
                surface_rel="surface.json",
                runtime_key="start_cas",
            )
        except BoundRuntimeError as exc:
            assert str(exc) == "BOUND_PATH_ESCAPES_REPOSITORY"
        else:
            raise AssertionError("path escape was accepted")
        outside.unlink(missing_ok=True)

    print("PASS__CONTENT_ADDRESSED_START_CAS_CALLER__NO_VERSION_SKEW")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
