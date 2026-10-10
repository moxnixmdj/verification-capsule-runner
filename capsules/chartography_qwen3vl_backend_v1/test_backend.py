from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend.py"


class BackendTests(unittest.TestCase):
    def _fixture(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        cli = root / "fake-cli.py"
        cli.write_text(
            "#!/usr/bin/env python3\n"
            "print('77.5 years')\n",
            encoding="utf-8",
        )
        cli.chmod(0o755)
        model = root / "model.gguf"
        mmproj = root / "mmproj.gguf"
        model.write_bytes(b"model")
        mmproj.write_bytes(b"mmproj")
        image = b"BM" + b"0" * 64
        question = "read chart"
        request = {
            "schema": "PROJECT_BRAIN_CHARTOGRAPHY_MULTIMODAL_REQUEST_V1",
            "backend_id": "test-backend",
            "question": question,
            "question_sha256": hashlib.sha256(question.encode()).hexdigest(),
            "image_sha256": hashlib.sha256(image).hexdigest(),
            "image_bytes_b64": base64.b64encode(image).decode(),
        }
        env = {
            **os.environ,
            "PROJECT_BRAIN_LLAMA_MTMD_CLI": str(cli),
            "PROJECT_BRAIN_QWEN_MODEL": str(model),
            "PROJECT_BRAIN_QWEN_MMPROJ": str(mmproj),
            "PROJECT_BRAIN_QWEN_THREADS": "1",
        }
        return td, request, env

    def test_exact_envelope_and_no_fallback(self):
        td, request, env = self._fixture()
        with td:
            p = subprocess.run(
                [sys.executable, str(BACKEND)],
                input=json.dumps(request),
                text=True,
                capture_output=True,
                env=env,
                check=True,
            )
            out = json.loads(p.stdout)
            self.assertEqual(out["backend_id"], "test-backend")
            self.assertEqual(out["answer"], "77.5 years")
            self.assertEqual(out["question_sha256"], request["question_sha256"])
            self.assertEqual(out["image_sha256"], request["image_sha256"])
            self.assertFalse(out["fallback_used"])
            self.assertFalse(out["network_required"])
            self.assertEqual(out["incremental_spend_usd"], 0)

    def test_image_hash_mismatch_fails_closed(self):
        td, request, env = self._fixture()
        with td:
            request["image_sha256"] = "0" * 64
            p = subprocess.run(
                [sys.executable, str(BACKEND)],
                input=json.dumps(request),
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )
            self.assertNotEqual(p.returncode, 0)
            self.assertIn("IMAGE_HASH_MISMATCH", p.stderr)

    def test_program_has_no_network_or_provider_imports(self):
        source = BACKEND.read_text(encoding="utf-8")
        for forbidden in (
            "requests",
            "urllib",
            "http.client",
            "socket",
            "anthropic",
            "openai",
            "google.generativeai",
        ):
            self.assertNotIn("import " + forbidden, source)


if __name__ == "__main__":
    unittest.main()
