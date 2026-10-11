from __future__ import annotations
import unittest
from canonical.runtime.bound_capabilities.chart_curve_value_query_v1 import CurveValueQueryError, query_curve_value

RED=[216,24,24]
BLUE=[24,72,216]

def base_axes():
    return {
      "x":{"scale":"LINEAR","transformed_value_from_pixel":[1.0,0.0]},
      "y":{"scale":"LINEAR","transformed_value_from_pixel":[-2.0,220.0]},
    }

def row(color, points):
    return {"color_bucket":color,"column_count":len(points),"x_range":[points[0][0],points[-1][0]],"points":points}

class IndependentCurveQueryFalsification(unittest.TestCase):
    def test_nonmatching_color_is_not_used(self):
        red=[[x,80.0] for x in range(20,101)]
        blue=[[x,30.0] for x in range(20,101)]
        scene={"plot_box":[10,10,110,110],"axes":base_axes(),"color_polylines":[row(RED,red),row(BLUE,blue)]}
        legend={"bindings":[{"label":"Target","color_bucket":RED}]}
        out=query_curve_value(scene,legend,label="Target",x_value=50)
        self.assertAlmostEqual(out["value"],60.0)

    def test_duplicate_label_binding_fails_closed(self):
        pts=[[x,80.0] for x in range(20,101)]
        scene={"plot_box":[10,10,110,110],"axes":base_axes(),"color_polylines":[row(RED,pts)]}
        legend={"bindings":[{"label":"Arm","color_bucket":RED},{"label":" arm ","color_bucket":BLUE}]}
        with self.assertRaisesRegex(CurveValueQueryError,"LEGEND_LABEL_NOT_UNIQUELY_BOUND:2"):
            query_curve_value(scene,legend,label="ARM",x_value=50)

    def test_nonbracketing_same_color_segment_does_not_create_ambiguity(self):
        p1=[[x,80.0] for x in range(20,61)]
        p2=[[x,40.0] for x in range(80,101)]
        scene={"plot_box":[10,10,110,110],"axes":base_axes(),"color_polylines":[row(RED,p1),row(RED,p2)]}
        legend={"bindings":[{"label":"Arm","color_bucket":RED}]}
        out=query_curve_value(scene,legend,label="Arm",x_value=50)
        self.assertEqual(out["query_receipt"]["polyline_index"],0)

    def test_exact_vertical_overlap_fails_closed(self):
        pts=[[20,80],[50,70],[60,20],[60,50],[70,60],[100,40]]
        scene={"plot_box":[10,10,110,110],"axes":base_axes(),"color_polylines":[row(RED,pts)]}
        legend={"bindings":[{"label":"Arm","color_bucket":RED}]}
        with self.assertRaisesRegex(CurveValueQueryError,"CURVE_NOT_UNIQUELY_QUERYABLE:0"):
            query_curve_value(scene,legend,label="Arm",x_value=60)

    def test_negative_query_on_log_x_fails_closed(self):
        axes=base_axes(); axes["x"]={"scale":"LOG10","transformed_value_from_pixel":[0.01,0.0]}
        pts=[[x,80.0] for x in range(20,101)]
        scene={"plot_box":[10,10,110,110],"axes":axes,"color_polylines":[row(RED,pts)]}
        legend={"bindings":[{"label":"Arm","color_bucket":RED}]}
        with self.assertRaisesRegex(CurveValueQueryError,"LOG_AXIS_REQUIRES_POSITIVE_QUERY"):
            query_curve_value(scene,legend,label="Arm",x_value=-1)

    def test_result_has_zero_model_and_no_domain_authority(self):
        pts=[[x,80.0] for x in range(20,101)]
        scene={"plot_box":[10,10,110,110],"axes":base_axes(),"color_polylines":[row(RED,pts)]}
        legend={"bindings":[{"label":"Arm","color_bucket":RED}]}
        out=query_curve_value(scene,legend,label="Arm",x_value=50)
        self.assertEqual(out["general_purpose_model_dependency_count"],0)
        self.assertEqual(out["external_general_purpose_model_runtime_dependency_count"],0)
        self.assertFalse(out["domain_semantic_authority"])
        self.assertFalse(out["benchmark_score_authority"])

if __name__=="__main__":
    unittest.main(verbosity=2)
