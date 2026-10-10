from __future__ import annotations

import base64
import hashlib
import importlib.metadata
from pathlib import Path
import subprocess
import tempfile
import unittest

from PIL import Image

from canonical.runtime import native_artifact_render_preservation_proof_v1 as render


SOURCE_B64 = "JVBERi0xLjMKJeLjz9MKMSAwIG9iago8PAovUHJvZHVjZXIgKHB5cGRmKQo+PgplbmRvYmoKMiAwIG9iago8PAovVHlwZSAvUGFnZXMKL0NvdW50IDEKL0tpZHMgWyA0IDAgUiBdCj4+CmVuZG9iagozIDAgb2JqCjw8Ci9UeXBlIC9DYXRhbG9nCi9QYWdlcyAyIDAgUgo+PgplbmRvYmoKNCAwIG9iago8PAovVHlwZSAvUGFnZQovUmVzb3VyY2VzIDw8Ci9Gb250IDw8Ci9GMSA1IDAgUgo+Pgo+PgovTWVkaWFCb3ggWyAwLjAgMC4wIDI0MCAxODAgXQovUGFyZW50IDIgMCBSCi9Db250ZW50cyA2IDAgUgo+PgplbmRvYmoKNSAwIG9iago8PAovVHlwZSAvRm9udAovU3VidHlwZSAvVHlwZTEKL0Jhc2VGb250IC9IZWx2ZXRpY2EKPj4KZW5kb2JqCjYgMCBvYmoKPDwKL0xlbmd0aCA2NAo+PgpzdHJlYW0KQlQgL0YxIDEyIFRmIDIwIDEwMCBUZCAoT0xEMDczMTAzKSBUaiAwIC0yNSBUZCAoVU5DSEFOR0VEKSBUaiBFVAplbmRzdHJlYW0KZW5kb2JqCnhyZWYKMCA3CjAwMDAwMDAwMDAgNjU1MzUgZiAKMDAwMDAwMDAxNSAwMDAwMCBuIAowMDAwMDAwMDU0IDAwMDAwIG4gCjAwMDAwMDAxMTMgMDAwMDAgbiAKMDAwMDAwMDE2MiAwMDAwMCBuIAowMDAwMDAwMjk0IDAwMDAwIG4gCjAwMDAwMDAzNjQgMDAwMDAgbiAKdHJhaWxlcgo8PAovU2l6ZSA3Ci9Sb290IDMgMCBSCi9JbmZvIDEgMCBSCj4+CnN0YXJ0eHJlZgo0NzgKJSVFT0YK"
OUTPUT_B64 = "JVBERi0xLjMKJeLjz9MKMSAwIG9iago8PAovVHlwZSAvQ2F0YWxvZwovUGFnZXMgMiAwIFIKPj4KZW5kb2JqCjIgMCBvYmoKPDwKL1R5cGUgL1BhZ2VzCi9Db3VudCAxCi9LaWRzIFsgMyAwIFIgXQo+PgplbmRvYmoKNCAwIG9iago8PAovVHlwZSAvRm9udAovU3VidHlwZSAvVHlwZTEKL0Jhc2VGb250IC9IZWx2ZXRpY2EKPj4KZW5kb2JqCjUgMCBvYmoKPDwKL0xlbmd0aCA2NQo+PgpzdHJlYW0KQlQKL0YxIDEyIFRmCjIwIDEwMCBUZAooTkVXMDczMTAzKSBUagowIC0yNSBUZAooVU5DSEFOR0VEKSBUagpFVAoKZW5kc3RyZWFtCmVuZG9iago2IDAgb2JqCjw8Ci9Qcm9kdWNlciAocHlwZGYpCj4+CmVuZG9iagp4cmVmCjAgNwowMDAwMDAwMDAwIDY1NTM1IGYgCjAwMDAwMDAwMTUgMDAwMDAgbiAKMDAwMDAwMDA2NCAwMDAwMCBuIAowMDAwMDAwMTIzIDAwMDAwIG4gCjAwMDAwMDAyNTUgMDAwMDAgbiAKMDAwMDAwMDMyNSAwMDAwMCBuIAowMDAwMDAwNDQwIDAwMDAwIG4gCnRyYWlsZXIKPDwKL1NpemUgNwovUm9vdCAxIDAgUgovSW5mbyA2IDAgUgo+PgpzdGFydHhyZWYKNDc5CiUlRU9GCg=="

SOURCE_SHA256 = "1a1583c1a9f9500a7ad2f1b4359ae8740e3df4e8e1c84e64f34a26f4d79eb5dd"
OUTPUT_SHA256 = "d06c3b1e24f0a966017ffe745b8603bbdb4eed7f9ac0d1275a81f3942b70add4"
SOURCE_PIXELS_SHA256 = "18ccd810ea490dadd70db8aaabcd519190a0d67905c0dfd66957be763a4592e5"
OUTPUT_PIXELS_SHA256 = "057082016774a40322fc9d20d7a3b1d807c02543b3af721f18adf12cf263b8e0"
EXPECTED_SIZE = (320, 240)

EXPECTED_LIBREOFFICE_CORE = "4:24.2.7-0ubuntu0.24.04.7"
EXPECTED_POPPLER_UTILS = "24.02.0-1ubuntu9.10"
EXPECTED_PILLOW = "12.3.0"


def dpkg_version(package: str) -> str:
    return subprocess.check_output(
        ["dpkg-query", "-W", "-f=${Version}", package],
        text=True,
    ).strip()


def raster_pixels(pdf_bytes: bytes, stem: str):
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        pdf = root / (stem + ".pdf")
        pdf.write_bytes(pdf_bytes)
        pages = render._rasterize(pdf, root, stem + "_page")
        if len(pages) != 1:
            raise AssertionError(f"expected one page, got {len(pages)}")
        with Image.open(pages[0]) as im:
            rgb = im.convert("RGB")
            return rgb.size, hashlib.sha256(rgb.tobytes()).hexdigest()


class TestProfessionalR3V7CurrentRenderReplay(unittest.TestCase):
    def test_exact_input_bytes(self):
        source = base64.b64decode(SOURCE_B64, validate=True)
        output = base64.b64decode(OUTPUT_B64, validate=True)
        self.assertEqual(hashlib.sha256(source).hexdigest(), SOURCE_SHA256)
        self.assertEqual(hashlib.sha256(output).hexdigest(), OUTPUT_SHA256)

    def test_exact_current_render_stack(self):
        self.assertEqual(dpkg_version("libreoffice-core"), EXPECTED_LIBREOFFICE_CORE)
        self.assertEqual(dpkg_version("poppler-utils"), EXPECTED_POPPLER_UTILS)
        self.assertEqual(importlib.metadata.version("Pillow"), EXPECTED_PILLOW)

    def test_exact_raster_pixels_and_localized_change(self):
        source = base64.b64decode(SOURCE_B64, validate=True)
        output = base64.b64decode(OUTPUT_B64, validate=True)

        source_size, source_pixels = raster_pixels(source, "source")
        output_size, output_pixels = raster_pixels(output, "output")
        self.assertEqual(source_size, EXPECTED_SIZE)
        self.assertEqual(output_size, EXPECTED_SIZE)
        self.assertEqual(source_pixels, SOURCE_PIXELS_SHA256)
        self.assertEqual(output_pixels, OUTPUT_PIXELS_SHA256)

        verdict = render.compare_renders(source, output, "pdf")
        self.assertTrue(verdict["pass"], verdict)
        self.assertEqual(verdict["reason"], "PASS")
        self.assertEqual(verdict["page_count"], 1)
        self.assertEqual(verdict["changed_page_count"], 1)
        self.assertLessEqual(verdict["max_pixel_fraction"], 0.025)
        self.assertLessEqual(verdict["max_bbox_fraction"], 0.10)
        page = verdict["pages"][0]
        self.assertEqual(page["bbox"], [27, 94, 117, 107])
        self.assertAlmostEqual(page["pixel_fraction"], 0.009908854166666667)
        self.assertAlmostEqual(page["bbox_fraction"], 0.015234375)


if __name__ == "__main__":
    unittest.main()
