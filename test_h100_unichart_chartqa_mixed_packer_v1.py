from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import torch

import h100_unichart_chartqa_mixed_packer_v1 as p


class ChartQAPackerTests(unittest.TestCase):
    def test_code_pack_roundtrips(self):
        rng=np.random.default_rng(11)
        q4=rng.integers(0,16,size=(2,p.GROUP_SIZE),dtype=np.uint8)
        q3=rng.integers(0,8,size=(2,p.GROUP_SIZE),dtype=np.uint8)
        self.assertTrue(np.array_equal(q4,p.unpack4(p._pack4(q4).tobytes(),2)))
        self.assertTrue(np.array_equal(q3,p.unpack3(p._pack3(q3).tobytes(),2)))

    def test_synthetic_state_dict_real_file(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td)
            src=td/"model.bin"
            torch.save({
                "encoder.weight":torch.linspace(-1,1,300,dtype=torch.float32),
                "decoder.weight":torch.linspace(-0.5,0.7,257,dtype=torch.float32),
                "encoder.ids":torch.tensor([1,2,3],dtype=torch.int64),
            },src)
            out=td/"packed.h100ucq"
            with (
                patch.object(p,"EXPECTED_F32",557),
                patch.object(p,"EXPECTED_I64",3),
                patch.object(p,"EXPECTED_ENCODER_F32",300),
                patch.object(p,"EXPECTED_DECODER_F32",257),
            ):
                receipt=p.pack_state_dict_file(src,out,groups_per_chunk=1)
            self.assertTrue(out.exists())
            self.assertEqual(receipt["status"],"PASS__REAL_CHARTQA_MIXED_W4_ENCODER_W3_DECODER_CHECKPOINT_CREATED")
            self.assertEqual(receipt["encoder_f32_elements"],300)
            self.assertEqual(receipt["decoder_f32_elements"],257)
            self.assertEqual(len(receipt["source_state_manifest_sha256"]),64)
            self.assertEqual(len(receipt["packed_checkpoint_sha256"]),64)

    def test_unclassified_float_fails_closed(self):
        with self.assertRaisesRegex(p.PackError,"UNCLASSIFIED_F32_TENSOR"):
            p.manifest_rows({"weird.weight":torch.ones(1,dtype=torch.float32)})


if __name__=="__main__":
    unittest.main(verbosity=2)
