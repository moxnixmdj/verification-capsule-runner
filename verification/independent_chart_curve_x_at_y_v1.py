from __future__ import annotations
import unittest
from canonical.runtime.bound_capabilities.chart_curve_x_at_y_query_v1 import CurveXAtYQueryError, query_curve_x_at_y

RED=[216,24,24]

def axes():
    return {
      "x":{"scale":"LINEAR","transformed_value_from_pixel":[2.0,-20.0]},
      "y":{"scale":"LINEAR","transformed_value_from_pixel":[-1.0,120.0]},
    }

def row(points):
    return {"color_bucket":RED,"column_count":len(points),"x_range":[points[0][0],points[-1][0]],"points":points}

def scene(rows):
    return {"plot_box":[10,10,110,110],"axes":axes(),"color_polylines":rows}

LEG={"bindings":[{"label":"Dose A","color_bucket":RED}]}

class IndependentInverseCurveFalsification(unittest.TestCase):
    def test_scaled_axis_crossing(self):
        pts=[[x,90-0.5*(x-20)] for x in range(20,101)]
        # y=50 -> pixel 70 -> x pixel 60 -> x value 100.
        out=query_curve_x_at_y(scene([row(pts)]),LEG,label="dose a",y_value=50)
        self.assertAlmostEqual(out["value"],100.0,places=6)

    def test_touching_vertex_is_single_x(self):
        pts=[]
        for x in range(20,61):
            pts.append([x,90-0.5*(x-20)])
        for x in range(61,101):
            pts.append([x,70+0.5*(x-60)])
        out=query_curve_x_at_y(scene([row(pts)]),LEG,label="Dose A",y_value=50)
        self.assertAlmostEqual(out["value"],100.0,places=6)

    def test_two_distinct_polylines_same_coincident_crossing_remain_ambiguous(self):
        a=[[x,90-0.5*(x-20)] for x in range(20,101)]
        b=[[x,90-0.5*(x-20)] for x in range(20,101)]
        with self.assertRaisesRegex(CurveXAtYQueryError,"CURVE_X_AT_Y_NOT_UNIQUE:2"):
            query_curve_x_at_y(scene([row(a),row(b)]),LEG,label="Dose A",y_value=50)

    def test_no_crossing_fails_closed(self):
        pts=[[x,100-0.05*(x-20)] for x in range(20,101)]
        with self.assertRaisesRegex(CurveXAtYQueryError,"CURVE_X_AT_Y_NOT_UNIQUE:0"):
            query_curve_x_at_y(scene([row(pts)]),LEG,label="Dose A",y_value=50)

    def test_flat_overlap_fails_closed_even_with_other_crossing(self):
        flat=[[x,70.0] for x in range(20,61)]
        sloped=[[x,90-(x-60)] for x in range(60,101)]
        with self.assertRaisesRegex(CurveXAtYQueryError,"CURVE_OVERLAPS_TARGET_Y_OVER_INTERVAL"):
            query_curve_x_at_y(scene([row(flat),row(sloped)]),LEG,label="Dose A",y_value=50)

    def test_zero_model_and_zero_score_authority(self):
        pts=[[x,90-0.5*(x-20)] for x in range(20,101)]
        out=query_curve_x_at_y(scene([row(pts)]),LEG,label="Dose A",y_value=50)
        self.assertEqual(out["external_general_purpose_model_runtime_dependency_count"],0)
        self.assertEqual(out["donor_general_purpose_model_runtime_dependency_count"],0)
        self.assertFalse(out["domain_semantic_authority"])
        self.assertFalse(out["benchmark_score_authority"])

if __name__=="__main__":
    unittest.main(verbosity=2)
