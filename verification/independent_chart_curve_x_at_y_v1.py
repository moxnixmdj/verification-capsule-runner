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
        pts=[[20,90],[100,50]]
        # y=50 -> pixel 70 -> halfway x pixel 60 -> x value 100.
        out=query_curve_x_at_y(scene([row(pts)]),LEG,label="dose a",y_value=50)
        self.assertAlmostEqual(out["value"],100.0,places=6)

    def test_touching_vertex_is_single_x(self):
        pts=[[20,90],[60,70],[100,90]]
        out=query_curve_x_at_y(scene([row(pts)]),LEG,label="Dose A",y_value=50)
        self.assertAlmostEqual(out["value"],100.0,places=6)

    def test_two_distinct_polylines_same_coincident_crossing_remain_ambiguous(self):
        a=[[20,90],[100,50]]
        b=[[20,90],[100,50]]
        with self.assertRaisesRegex(CurveXAtYQueryError,"CURVE_X_AT_Y_NOT_UNIQUE:2"):
            query_curve_x_at_y(scene([row(a),row(b)]),LEG,label="Dose A",y_value=50)

    def test_no_crossing_fails_closed(self):
        pts=[[20,100],[100,95]]
        with self.assertRaisesRegex(CurveXAtYQueryError,"CURVE_X_AT_Y_NOT_UNIQUE:0"):
            query_curve_x_at_y(scene([row(pts)]),LEG,label="Dose A",y_value=50)

    def test_flat_overlap_fails_closed_even_with_other_crossing(self):
        flat=[[20,70],[60,70]]
        sloped=[[60,90],[100,50]]
        with self.assertRaisesRegex(CurveXAtYQueryError,"CURVE_OVERLAPS_TARGET_Y_OVER_INTERVAL"):
            query_curve_x_at_y(scene([row(flat),row(sloped)]),LEG,label="Dose A",y_value=50)

    def test_zero_model_and_zero_score_authority(self):
        pts=[[20,90],[100,50]]
        out=query_curve_x_at_y(scene([row(pts)]),LEG,label="Dose A",y_value=50)
        self.assertEqual(out["external_general_purpose_model_runtime_dependency_count"],0)
        self.assertEqual(out["donor_general_purpose_model_runtime_dependency_count"],0)
        self.assertFalse(out["domain_semantic_authority"])
        self.assertFalse(out["benchmark_score_authority"])

if __name__=="__main__":
    unittest.main(verbosity=2)
