import math, unittest
import cadquery as cq
from m1b_continuous_geometry_compiler import compile_contract
from cadquery_partspec_generator import spec_to_code
from cadquery_partspec_validator import validate

def build(contract):
    compiled=compile_contract(contract)
    if compiled["status"]!="COMPILED":
        raise AssertionError(compiled)
    ns={}
    exec(spec_to_code(compiled["partspec"]),ns)
    assert "result" in ns
    return compiled,ns["result"]

class M1BEndToEnd(unittest.TestCase):
    def test_circle_extrude_real_brep_and_tolerance(self):
        c={
          "units":"mm",
          "geometry":{"kind":"circle_extrude","diameter":10.0,"depth":5.0},
          "dimensions":[
            {"name":"overall_width","nominal":10.0,"tol_plus":0.1,"tol_minus":0.2},
            {"name":"overall_depth","nominal":5.0,"tol_plus":0.05,"tol_minus":0.05}
          ]
        }
        comp,result=build(c)
        self.assertEqual(len(result.solids().vals()),1)
        bb=result.val().BoundingBox()
        self.assertAlmostEqual(bb.xlen,10.0,places=6)
        self.assertAlmostEqual(bb.ylen,10.0,places=6)
        self.assertAlmostEqual(bb.zlen,5.0,places=6)
        self.assertAlmostEqual(result.val().Volume(),math.pi*25.0*5.0,places=4)
        self.assertEqual(comp["dimension_intervals"]["overall_width"],
                         {"nominal":10.0,"lower":9.8,"upper":10.1,"tol_minus":0.2,"tol_plus":0.1})
        report=validate(comp["partspec"],result,tol=1e-6)
        self.assertTrue(report.ok(),report.feedback())

    def test_profile_line_prism_real_brep(self):
        c={
          "units":"mm",
          "geometry":{
            "kind":"profile_extrude","start":[0.0,0.0],"depth":2.0,
            "segments":[
              {"kind":"line","end":[10.0,0.0]},
              {"kind":"line","end":[10.0,5.0]},
              {"kind":"line","end":[0.0,5.0]},
              {"kind":"line","end":[0.0,0.0]}
            ]
          }
        }
        _,result=build(c)
        bb=result.val().BoundingBox()
        self.assertEqual(len(result.solids().vals()),1)
        self.assertAlmostEqual(bb.xlen,10.0,places=6)
        self.assertAlmostEqual(bb.ylen,5.0,places=6)
        self.assertAlmostEqual(bb.zlen,2.0,places=6)
        self.assertAlmostEqual(result.val().Volume(),100.0,places=4)

    def test_profile_arc_is_continuous_not_voxelized(self):
        c={
          "units":"mm",
          "geometry":{
            "kind":"profile_extrude","start":[0.0,0.0],"depth":3.0,
            "segments":[
              {"kind":"line","end":[10.0,0.0]},
              {"kind":"arc","mid":[12.0,5.0],"end":[10.0,10.0]},
              {"kind":"line","end":[0.0,10.0]},
              {"kind":"line","end":[0.0,0.0]}
            ]
          }
        }
        _,result=build(c)
        self.assertEqual(len(result.solids().vals()),1)
        # Arc must create at least one circular/curved edge in the B-rep.
        kinds={e.geomType() for e in result.edges().vals()}
        self.assertTrue(any(k in kinds for k in ("CIRCLE","ELLIPSE","BSPLINE")),kinds)
        self.assertGreater(result.val().Volume(),300.0)

    def test_revolved_steps_with_bore(self):
        c={
          "units":"mm",
          "geometry":{"kind":"revolved_steps","segments":[
            {"z_start":0.0,"z_end":4.0,"outer_diameter":12.0,"inner_diameter":4.0},
            {"z_start":4.0,"z_end":7.5,"outer_diameter":8.0,"inner_diameter":2.0}
          ]}
        }
        _,result=build(c)
        self.assertEqual(len(result.solids().vals()),1)
        bb=result.val().BoundingBox()
        self.assertAlmostEqual(bb.xlen,12.0,places=5)
        self.assertAlmostEqual(bb.ylen,12.0,places=5)
        self.assertAlmostEqual(bb.zlen,7.5,places=5)
        expected=math.pi*((12**2-4**2)/4)*4 + math.pi*((8**2-2**2)/4)*3.5
        self.assertAlmostEqual(result.val().Volume(),expected,places=3)

    def test_multibody_csg_cut(self):
        c={
          "units":"mm",
          "geometry":{"kind":"multibody","bodies":[
            {"shape":"box","operation":"add","x":0,"y":0,"z":0,"dx":20,"dy":10,"dz":5},
            {"shape":"cylinder","operation":"cut","x":10,"y":5,"z":0,"diameter":4,"length":5,"axis":"z"}
          ]}
        }
        _,result=build(c)
        self.assertEqual(len(result.solids().vals()),1)
        expected=20*10*5-math.pi*2**2*5
        self.assertAlmostEqual(result.val().Volume(),expected,places=3)

    def test_unsupported_geometry_fails_closed(self):
        r=compile_contract({"units":"mm","geometry":{"kind":"magic_spline_cloud"}})
        self.assertEqual(r["status"],"FAIL_CLOSED")
        self.assertTrue(any("unsupported geometry kind" in x for x in r["errors"]))

    def test_invalid_tolerance_fails_closed(self):
        r=compile_contract({
          "units":"mm","geometry":{"kind":"circle_extrude","diameter":10,"depth":5},
          "dimensions":[{"name":"d","nominal":10,"tol_plus":-1,"tol_minus":0}]
        })
        self.assertEqual(r["status"],"FAIL_CLOSED")

if __name__=="__main__":
    unittest.main()
