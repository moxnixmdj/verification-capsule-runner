from __future__ import annotations
import hashlib
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent
EXPECTED = {
    "canonical/runtime/bound_capabilities/image_ocr_tesseract_positioned.py": "19f3087489ce7f6f935fc7baaebdc8cd672f4b62",
    "canonical/runtime/bound_capabilities/image_ocr_tesseract.py": "45714d7a0160802d986042910da1c4c6462676e5",
    "canonical/tests/test_image_ocr_tesseract_positioned.py": "b427dd6c5772aee65ebe69530659b40acf0042f1",
    "canonical/governance/M1A_POSITIONED_OCR_TSV_BRIDGE_V1.json": "17591666d602b83448df6d141274fc4e67a1a0a8",
}

def blob(path: Path) -> str:
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode("ascii")+b"\0"+data).hexdigest()

class ExactBrainBlobBindingTests(unittest.TestCase):
    def test_exact_brain_blobs(self):
        for rel,expected in EXPECTED.items():
            p=ROOT/rel
            self.assertTrue(p.is_file(),rel)
            self.assertEqual(blob(p),expected,rel)

if __name__=="__main__":
    unittest.main(verbosity=2)
