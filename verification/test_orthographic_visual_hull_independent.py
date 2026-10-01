import random
import unittest

from orthographic_visual_hull import (
    RepairRegion,
    VisualHullError,
    accept_candidate_orthographic_shape,
    compile_rectangular_repairs_to_body_payloads,
    hull_signature,
    infer_visual_hull_repairs,
    project_visual_hull,
    reconstruct_visual_hull,
)


def oracle_hull(top, front, right):
    y_cells, x_cells = len(top), len(top[0])
    z_cells = len(front)
    return [
        [
            [
                bool(top[y][x] and front[z][x] and right[z][y])
                for x in range(x_cells)
            ]
            for y in range(y_cells)
        ]
        for z in range(z_cells)
    ]


def count(vox):
    return sum(bool(v) for slab in vox for row in slab for v in row)


class IndependentVisualHullVerification(unittest.TestCase):
    def test_box_signature(self):
        top = [[1] * 5 for _ in range(4)]
        front = [[1] * 5 for _ in range(3)]
        right = [[1] * 4 for _ in range(3)]
        sig = hull_signature(reconstruct_visual_hull(top, front, right))
        self.assertEqual(sig.occupied_voxels, 60)
        self.assertEqual(sig.bbox_cells, (5, 4, 3))
        self.assertEqual(sig.connected_components, 1)
        self.assertEqual(sig.exposed_faces, 2 * (5 * 4 + 5 * 3 + 4 * 3))

    def test_visible_through_feature_survives_inversion(self):
        top = [[1, 1, 1], [1, 0, 1], [1, 1, 1]]
        front = [[1, 1, 1], [1, 1, 1], [1, 1, 1]]
        right = [[1, 1, 1], [1, 1, 1], [1, 1, 1]]
        vox = reconstruct_visual_hull(top, front, right)
        self.assertTrue(all(not vox[z][1][1] for z in range(3)))
        self.assertEqual(count(vox), 24)

    def test_one_view_overbuild_is_rejected(self):
        top = [[1, 1, 0], [1, 1, 0]]
        front = [[1, 1, 0], [1, 1, 0]]
        right = [[1, 1], [1, 1]]
        cand_top = [[1, 1, 1], [1, 1, 1]]
        cand_front = [[1, 1, 0], [1, 1, 0]]
        report = accept_candidate_orthographic_shape(
            top, front, right, cand_top, cand_front, right
        )
        self.assertFalse(report.passed)
        self.assertTrue(any("top_" in r for r in report.reasons))

    def test_rectangular_underbuild_compiles_to_exact_box(self):
        source_top = [[1, 1, 1], [1, 1, 1]]
        source_front = [[1, 1, 1], [1, 1, 1]]
        source_right = [[1, 1], [1, 1]]
        candidate_top = [[1, 1, 0], [1, 1, 0]]
        candidate_front = [[1, 1, 0], [1, 1, 0]]
        regions = infer_visual_hull_repairs(
            source_top, source_front, source_right,
            candidate_top, candidate_front, source_right,
        )
        bodies, unresolved = compile_rectangular_repairs_to_body_payloads(
            regions, cell_size=(2.0, 3.0, 5.0), origin=(10.0, 20.0, 30.0)
        )
        self.assertEqual(unresolved, [])
        self.assertEqual(
            bodies,
            [{
                "shape": "box",
                "operation": "add",
                "x": 14.0,
                "y": 20.0,
                "z": 30.0,
                "dx": 2.0,
                "dy": 6.0,
                "dz": 10.0,
            }],
        )

    def test_nonrectangular_repair_fails_closed(self):
        region = RepairRegion(
            operation="add",
            voxel_count=3,
            bbox_min=(0, 0, 0),
            bbox_max_exclusive=(2, 2, 1),
            bbox_volume=4,
            fill_ratio=0.75,
            rectangular=False,
        )
        bodies, unresolved = compile_rectangular_repairs_to_body_payloads(
            [region], cell_size=(1.0, 1.0, 1.0)
        )
        self.assertEqual(bodies, [])
        self.assertEqual(unresolved[0]["reason"], "NON_RECTANGULAR_REPAIR_REGION")

    def test_invalid_calibration_fails_closed(self):
        with self.assertRaises(VisualHullError):
            compile_rectangular_repairs_to_body_payloads([], cell_size=(1.0, 0.0, 1.0))

    def test_randomized_reconstruction_against_independent_oracle_3000(self):
        rng = random.Random(8675309)
        for _ in range(3000):
            x = rng.randint(1, 7)
            y = rng.randint(1, 7)
            z = rng.randint(1, 7)
            top = [[rng.random() < 0.62 for _ in range(x)] for _ in range(y)]
            front = [[rng.random() < 0.62 for _ in range(x)] for _ in range(z)]
            right = [[rng.random() < 0.62 for _ in range(y)] for _ in range(z)]
            got = reconstruct_visual_hull(top, front, right)
            self.assertEqual(got, oracle_hull(top, front, right))
            pt, pf, pr = project_visual_hull(got)
            for yy in range(y):
                for xx in range(x):
                    self.assertFalse(pt[yy][xx] and not top[yy][xx])
            for zz in range(z):
                for xx in range(x):
                    self.assertFalse(pf[zz][xx] and not front[zz][xx])
            for zz in range(z):
                for yy in range(y):
                    self.assertFalse(pr[zz][yy] and not right[zz][yy])

    def test_randomized_repair_conservation_1000(self):
        rng = random.Random(424242)
        for _ in range(1000):
            x = rng.randint(1, 6)
            y = rng.randint(1, 6)
            z = rng.randint(1, 6)
            masks = []
            for _side in range(2):
                top = [[rng.random() < 0.66 for _ in range(x)] for _ in range(y)]
                front = [[rng.random() < 0.66 for _ in range(x)] for _ in range(z)]
                right = [[rng.random() < 0.66 for _ in range(y)] for _ in range(z)]
                masks.append((top, front, right))
            (st, sf, sr), (ct, cf, cr) = masks
            source = reconstruct_visual_hull(st, sf, sr)
            candidate = reconstruct_visual_hull(ct, cf, cr)
            repairs = infer_visual_hull_repairs(st, sf, sr, ct, cf, cr)
            adds = sum(r.voxel_count for r in repairs if r.operation == "add")
            cuts = sum(r.voxel_count for r in repairs if r.operation == "cut")
            self.assertEqual(count(candidate) + adds - cuts, count(source))
            self.assertTrue(all(r.voxel_count > 0 for r in repairs))

    def test_exact_candidate_always_accepts_500_random_shapes(self):
        rng = random.Random(121212)
        for _ in range(500):
            x = rng.randint(1, 5)
            y = rng.randint(1, 5)
            z = rng.randint(1, 5)
            top = [[rng.random() < 0.7 for _ in range(x)] for _ in range(y)]
            front = [[rng.random() < 0.7 for _ in range(x)] for _ in range(z)]
            right = [[rng.random() < 0.7 for _ in range(y)] for _ in range(z)]
            report = accept_candidate_orthographic_shape(
                top, front, right, top, front, right
            )
            self.assertTrue(report.passed, report.reasons)

    def test_inconsistent_dimensions_fail_closed(self):
        with self.assertRaises(VisualHullError):
            reconstruct_visual_hull([[1, 1]], [[1, 1, 1]], [[1]])


if __name__ == "__main__":
    unittest.main()
