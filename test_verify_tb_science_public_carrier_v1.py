from __future__ import annotations

import unittest

from verify_tb_science_public_carrier_v1 import Carrier, TARGET_SCORE, evaluate


def row(i: int, *, cpus=1, memory_mb=1024, storage_mb=1024, gpus=0):
    return {
        "path": f"tasks/x/task-{i}/task.toml",
        "cpus": cpus,
        "memory_mb": memory_mb,
        "storage_mb": storage_mb,
        "gpus": gpus,
    }


class TBScienceCarrierTests(unittest.TestCase):
    def test_42_of_70_is_mathematically_enough_for_58_7(self):
        carrier = Carrier(4, 16000, 20000, True, True)
        rows = [row(i) for i in range(42)] + [
            row(i + 42, storage_mb=50000) for i in range(28)
        ]
        out = evaluate(rows, carrier)
        self.assertTrue(out["pass"], out)
        self.assertGreaterEqual(
            out["attainability"]["max_full_score_if_all_incompatible_zero"],
            TARGET_SCORE,
        )

    def test_41_of_70_is_not_enough(self):
        carrier = Carrier(4, 16000, 20000, True, True)
        rows = [row(i) for i in range(41)] + [
            row(i + 41, storage_mb=50000) for i in range(29)
        ]
        out = evaluate(rows, carrier)
        self.assertFalse(out["pass"], out)

    def test_no_docker_fails_closed(self):
        carrier = Carrier(4, 16000, 100000, False, True)
        rows = [row(i) for i in range(70)]
        out = evaluate(rows, carrier)
        self.assertFalse(out["pass"], out)

    def test_gpu_task_is_incompatible_on_cpu_carrier(self):
        carrier = Carrier(4, 16000, 100000, True, True)
        rows = [row(i) for i in range(69)] + [row(69, gpus=1)]
        out = evaluate(rows, carrier)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["attainability"]["incompatible_task_count"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
