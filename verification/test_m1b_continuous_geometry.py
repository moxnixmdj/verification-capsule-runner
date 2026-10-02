import math
import unittest

from m1b_continuous_geometry_compiler import compile_contract
from cad_partspec_generator import normalize_to_mm, spec_to_code


def build(spec):
    ns={}
    exec(spec_to_code(spec),ns)
    result=ns["result"]
    solids=result.solids().vals()
    if len(solids)!=1:
        raise AssertionError(f"expected one solid, got {len(solids)}")
    return result.val()


class M1BContinuousGeometryTests(unittest.TestCase):
    def test_circle_extrude_continuous_dimensions_and_tolerance(self):
        out=compile_contract({
            "units":"mm",
            "geometry":{"kind":"circle_extrude","diameter":37.125,"depth":12.375},
            "dimensions":[
                {"name":"overall_diameter","nominal":37.125,"tol_plus":0.007,"tol_minus":0.003},
                {"name":"overall_depth","nominal":12.375,"tol_plus":0.004,"tol_minus":0.006},
            ],
        })
        self.assertEqual(out["status"],"COMPILED")
        iv=out["dimension_intervals"]
        self.assertTrue(math.isclose(iv["overall_diameter"]["lower"],37.122,abs_tol=1e-12))
        self.assertTrue(math.isclose(iv["overall_diameter"]["upper"],37.132,abs_tol=1e-12))
        self.assertTrue(math.isclose(iv["overall_depth"]["lower"],12.369,abs_tol=1e-12))
        self.assertTrue(math.isclose(iv["overall_depth"]["upper"],12.379,abs_tol=1e-12))
        shape=build(out["partspec"])
        bb=shape.BoundingBox()
        self.assertAlmostEqual(bb.xlen,37.125,places=6)
        self.assertAlmostEqual(bb.ylen,37.125,places=6)
        self.assertAlmostEqual(bb.zlen,12.375,places=6)

    def test_line_arc_profile_builds_analytic_curved_prism(self):
        out=compile_contract({
            "units":"mm",
            "geometry":{
                "kind":"profile_extrude",
                "start":[0.0,0.0],
                "segments":[
                    {"kind":"line","end":[20.0,0.0]},
                    {"kind":"arc","mid":[25.0,5.0],"end":[20.0,10.0]},
                    {"kind":"line","end":[0.0,10.0]},
                    {"kind":"line","end":[0.0,0.0]},
                ],
                "depth":7.25,
            },
        })
        self.assertEqual(out["status"],"COMPILED")
        shape=build(out["partspec"])
        bb=shape.BoundingBox()
        self.assertAlmostEqual(bb.xlen,25.0,places=5)
        self.assertAlmostEqual(bb.ylen,10.0,places=5)
        self.assertAlmostEqual(bb.zlen,7.25,places=6)
        self.assertGreater(shape.Volume(),20.0*10.0*7.25)

    def test_revolved_steps_with_bore_builds_continuous_surface(self):
        out=compile_contract({
            "units":"mm",
            "geometry":{
                "kind":"revolved_steps",
                "segments":[
                    {"z_start":0.0,"z_end":5.125,"outer_diameter":20.25,"inner_diameter":4.75},
                    {"z_start":5.125,"z_end":12.875,"outer_diameter":12.5,"inner_diameter":0.0},
                ],
            },
        })
        self.assertEqual(out["status"],"COMPILED")
        shape=build(out["partspec"])
        bb=shape.BoundingBox()
        self.assertAlmostEqual(bb.xlen,20.25,places=5)
        self.assertAlmostEqual(bb.ylen,20.25,places=5)
        self.assertAlmostEqual(bb.zlen,12.875,places=5)

    def test_inch_tolerance_normalization_preserves_sub_hundredth_interval(self):
        out=compile_contract({
            "units":"in",
            "geometry":{"kind":"circle_extrude","diameter":1.2345,"depth":0.3755},
            "dimensions":[
                {"name":"overall_diameter","nominal":1.2345,"tol_plus":0.001,"tol_minus":0.002}
            ],
        })
        self.assertEqual(out["status"],"COMPILED")
        iv=out["dimension_intervals"]["overall_diameter"]
        self.assertTrue(math.isclose(iv["lower"],1.2325,abs_tol=1e-12))
        self.assertTrue(math.isclose(iv["upper"],1.2355,abs_tol=1e-12))
        mm=normalize_to_mm(out["partspec"])
        d=mm.dimensions[0]
        self.assertTrue(math.isclose(d.nominal,1.2345*25.4,rel_tol=0,abs_tol=1e-12))
        self.assertTrue(math.isclose(d.tol_plus,0.001*25.4,rel_tol=0,abs_tol=1e-12))
        self.assertTrue(math.isclose(d.tol_minus,0.002*25.4,rel_tol=0,abs_tol=1e-12))
        shape=build(out["partspec"])
        bb=shape.BoundingBox()
        self.assertAlmostEqual(bb.xlen,1.2345*25.4,places=5)
        self.assertAlmostEqual(bb.zlen,0.3755*25.4,places=5)

    def test_unsupported_geometry_fails_closed(self):
        out=compile_contract({
            "units":"mm",
            "geometry":{"kind":"nurbs_surface","control_points":[]},
        })
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertFalse("partspec" in out)


if __name__=="__main__":
    unittest.main()
