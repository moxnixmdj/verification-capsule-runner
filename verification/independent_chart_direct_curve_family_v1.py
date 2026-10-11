from __future__ import annotations
import unittest

from canonical.runtime.bound_capabilities.chart_direct_curve_family_v1 import (
    DirectCurveFamilyError,
    bind_right_endpoint_curve_labels,
    query_direct_curve_family,
)

RED=[216,24,24]
BLUE=[24,72,216]
GREEN=[24,168,72]

def axes(*, log_y=False):
    return {
      "x":{"scale":"LINEAR","transformed_value_from_pixel":[1.0,0.0]},
      "y":{"scale":"LOG10" if log_y else "LINEAR",
           "transformed_value_from_pixel":[-0.01 if log_y else -1.0,2.0 if log_y else 110.0]},
    }

def line(color,y,x0=20,x1=100):
    pts=[[x,float(y)] for x in range(x0,x1+1)]
    return {"color_bucket":color,"column_count":len(pts),"x_range":[x0,x1],"points":pts}

def scene(rows, *, log_y=False):
    return {"plot_box":[10,10,110,110],"axes":axes(log_y=log_y),"color_polylines":rows}

def item(sid,text,x0,y0,x1,y1,conf=96):
    return {"source_id":sid,"text":text,"confidence_min":conf,
            "box":{"x0":x0,"y0":y0,"x1_exclusive":x1,"y1_exclusive":y1}}

class IndependentDirectCurveFamilyFalsification(unittest.TestCase):
    def test_log_y_family_rank_uses_geometry_and_returns_values(self):
        sc=scene([line(RED,30),line(BLUE,60),line(GREEN,90)],log_y=True)
        binding={"bindings":[
          {"label":"Upper","polyline_index":0},
          {"label":"Middle","polyline_index":1},
          {"label":"Lower","polyline_index":2},
        ]}
        out=query_direct_curve_family(sc,binding,x_value=50)
        self.assertEqual([r["label"] for r in out["ranked_high_to_low"]],["Upper","Middle","Lower"])
        self.assertGreater(out["ranked_high_to_low"][0]["value"],out["ranked_high_to_low"][1]["value"])
        self.assertGreater(out["ranked_high_to_low"][1]["value"],out["ranked_high_to_low"][2]["value"])

    def test_family_member_not_spanning_query_fails_closed(self):
        sc=scene([line(RED,40,20,45),line(BLUE,60,20,100)])
        binding={"bindings":[{"label":"Short","polyline_index":0},{"label":"Full","polyline_index":1}]}
        with self.assertRaisesRegex(DirectCurveFamilyError,"FAMILY_MEMBER_NOT_QUERYABLE:Short"):
            query_direct_curve_family(sc,binding,x_value=70)

    def test_left_axis_title_does_not_bind_to_right_endpoint(self):
        sc=scene([line(RED,40),line(BLUE,80)])
        ocr={"text_items":[item("axis","Height",-5,45,35,55)]}
        out=bind_right_endpoint_curve_labels(sc,ocr)
        self.assertFalse(out["pass"])

    def test_text_box_covering_endpoint_is_admissible_when_unique(self):
        sc=scene([line(RED,40),line(BLUE,80)])
        ocr={"text_items":[item("a","P90",96,35,116,45),item("b","P10",96,75,116,85)]}
        out=bind_right_endpoint_curve_labels(sc,ocr)
        self.assertEqual(out["binding_count"],2,out)

    def test_endpoint_distance_limit_fails_closed(self):
        sc=scene([line(RED,40),line(BLUE,80)])
        ocr={"text_items":[item("far","P90",122,35,140,45)]}
        out=bind_right_endpoint_curve_labels(sc,ocr,max_endpoint_distance_fraction=.03)
        self.assertFalse(out["pass"])

    def test_one_to_one_and_zero_model_nonclaims(self):
        sc=scene([line(RED,30),line(BLUE,70)])
        ocr={"text_items":[item("a","A",102,25,114,35),item("b","B",102,65,114,75)]}
        binding=bind_right_endpoint_curve_labels(sc,ocr)
        out=query_direct_curve_family(sc,binding,x_value=50,target_y=45)
        self.assertEqual(out["external_general_purpose_model_runtime_dependency_count"],0)
        self.assertEqual(out["donor_general_purpose_model_runtime_dependency_count"],0)
        self.assertFalse(out["domain_semantic_authority"])
        self.assertFalse(out["benchmark_score_authority"])

if __name__=="__main__":
    unittest.main(verbosity=2)
