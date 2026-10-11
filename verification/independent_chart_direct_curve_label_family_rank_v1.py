from __future__ import annotations

import math
import unittest

from canonical.runtime.bound_capabilities.chart_direct_curve_label_family_rank_v1 import (
    DirectCurveLabelError,
    bind_direct_curve_labels,
    rank_direct_labeled_curve_family,
)

RED=[216,24,24]
BLUE=[24,72,216]
GREEN=[24,168,72]

def item(source_id,text,x0,y0,x1,y1,conf=95.0):
    return {
        "source_id":source_id,
        "text":text,
        "confidence_min":conf,
        "box":{"x0":x0,"y0":y0,"x1_exclusive":x1,"y1_exclusive":y1},
    }

def axes(*,x_scale="LINEAR",y_scale="LINEAR"):
    return {
        "x":{
            "scale":x_scale,
            "transformed_value_from_pixel":[1.0,0.0],
        },
        "y":{
            "scale":y_scale,
            "transformed_value_from_pixel":[-0.02 if y_scale=="LOG10" else -1.0,3.0 if y_scale=="LOG10" else 110.0],
        },
    }

def polyline(y,color,x0=20,x1=100):
    return {
        "color_bucket":color,
        "column_count":x1-x0+1,
        "x_range":[x0,x1],
        "points":[[x,float(y)] for x in range(x0,x1+1)],
    }

def scene(rows,ax=None):
    return {
        "plot_box":[10,10,110,110],
        "axes":ax or axes(),
        "color_polylines":rows,
    }

class IndependentChartDirectCurveFamilyRankV1(unittest.TestCase):
    def test_mixed_left_and_right_endpoint_labels_rank(self):
        s=scene([polyline(30,RED),polyline(80,BLUE)])
        ocr={"text_items":[
            item("left","Upper",2,25,18,35),
            item("right","Lower",102,75,126,85),
        ]}
        b=bind_direct_curve_labels(s,ocr)
        self.assertTrue(b["pass"],b)
        sides={r["label"]:r["endpoint_side"] for r in b["bindings"]}
        self.assertEqual(sides,{"Lower":"END","Upper":"START"})
        out=rank_direct_labeled_curve_family(s,b,x_value=60)
        self.assertEqual([r["label"] for r in out["ranked_curves"]],["Upper","Lower"])

    def test_duplicate_normalized_label_across_distinct_curves_rejected(self):
        s=scene([polyline(30,RED),polyline(80,BLUE)])
        ocr={"text_items":[
            item("a","Series A",102,25,130,35),
            item("b","  series   a  ",102,75,132,85),
        ]}
        b=bind_direct_curve_labels(s,ocr)
        self.assertEqual(b["binding_count"],1,b)
        self.assertIn("DUPLICATE_NORMALIZED_LABEL",{r["reason"] for r in b["rejected"]})

    def test_alpha_numeric_direct_label_is_eligible(self):
        s=scene([polyline(45,RED)])
        b=bind_direct_curve_labels(
            s,{"text_items":[item("p","P90",102,40,126,50)]}
        )
        self.assertTrue(b["pass"],b)
        self.assertEqual(b["bindings"][0]["label"],"P90")

    def test_low_confidence_direct_label_fails_closed(self):
        s=scene([polyline(45,RED)])
        b=bind_direct_curve_labels(
            s,{"text_items":[item("x","Treatment",102,40,132,50,conf=12)]}
        )
        self.assertFalse(b["pass"])
        self.assertEqual(b["rejected"][0]["reason"],"LOW_OCR_CONFIDENCE")

    def test_malformed_box_is_rejected_not_guessed(self):
        s=scene([polyline(45,RED)])
        bad={"source_id":"x","text":"Treatment","confidence_min":95,
             "box":{"x0":102,"y0":50,"x1_exclusive":101,"y1_exclusive":60}}
        b=bind_direct_curve_labels(s,{"text_items":[bad]})
        self.assertFalse(b["pass"])
        self.assertEqual(b["rejected"][0]["reason"],"OCR_BOX_GEOMETRY_INVALID")

    def test_vertical_overlap_at_exact_query_fails_closed(self):
        row={
            "color_bucket":RED,
            "column_count":4,
            "x_range":[40,60],
            "points":[[40,30.0],[50,20.0],[50,70.0],[60,40.0]],
        }
        s=scene([row])
        b={"bindings":[{"label":"A","polyline_index":0}]}
        with self.assertRaisesRegex(DirectCurveLabelError,"VERTICAL_OR_OVERLAPPING_CURVE_AT_QUERY"):
            rank_direct_labeled_curve_family(s,b,x_value=50)

    def test_duplicate_manual_polyline_binding_fails_closed(self):
        s=scene([polyline(40,RED)])
        b={"bindings":[
            {"label":"A","polyline_index":0},
            {"label":"B","polyline_index":0},
        ]}
        with self.assertRaisesRegex(DirectCurveLabelError,"DIRECT_LABEL_POLYLINE_BINDING_INVALID"):
            rank_direct_labeled_curve_family(s,b,x_value=60)

    def test_unsupported_axis_scale_fails_closed(self):
        s=scene([polyline(40,RED)],ax=axes(x_scale="LN"))
        b={"bindings":[{"label":"A","polyline_index":0}]}
        with self.assertRaisesRegex(DirectCurveLabelError,"AXIS_SCALE_UNSUPPORTED"):
            rank_direct_labeled_curve_family(s,b,x_value=60)

    def test_nonfinite_nearest_query_fails_closed(self):
        s=scene([polyline(40,RED),polyline(70,BLUE)])
        b={"bindings":[
            {"label":"A","polyline_index":0},
            {"label":"B","polyline_index":1},
        ]}
        with self.assertRaisesRegex(DirectCurveLabelError,"NEAREST_Y_QUERY_INVALID"):
            rank_direct_labeled_curve_family(s,b,x_value=60,nearest_y_value=float("nan"))

    def test_log_axis_rank_uses_semantic_value_not_pixel_order_assumption(self):
        s=scene(
            [polyline(20,RED),polyline(80,BLUE)],
            ax=axes(y_scale="LOG10"),
        )
        b={"bindings":[
            {"label":"Top","polyline_index":0},
            {"label":"Bottom","polyline_index":1},
        ]}
        out=rank_direct_labeled_curve_family(s,b,x_value=60)
        self.assertEqual([r["label"] for r in out["ranked_curves"]],["Top","Bottom"])
        self.assertGreater(out["ranked_curves"][0]["value"],out["ranked_curves"][1]["value"])
        self.assertAlmostEqual(out["ranked_curves"][0]["value"],10**2.6,places=7)
        self.assertAlmostEqual(out["ranked_curves"][1]["value"],10**1.4,places=7)

    def test_query_inside_plot_but_outside_curve_support_fails_closed(self):
        s=scene([polyline(40,RED,x0=30,x1=70)])
        b={"bindings":[{"label":"A","polyline_index":0}]}
        with self.assertRaisesRegex(DirectCurveLabelError,"QUERY_NOT_BRACKETED_BY_CURVE"):
            rank_direct_labeled_curve_family(s,b,x_value=20)

    def test_query_outside_plot_fails_closed_before_curve_interpolation(self):
        s=scene([polyline(40,RED)])
        b={"bindings":[{"label":"A","polyline_index":0}]}
        with self.assertRaisesRegex(DirectCurveLabelError,"QUERY_X_OUTSIDE_PLOT"):
            rank_direct_labeled_curve_family(s,b,x_value=200)

    def test_empty_binding_set_has_no_rank_authority(self):
        s=scene([polyline(40,RED)])
        with self.assertRaisesRegex(DirectCurveLabelError,"DIRECT_LABEL_BINDINGS_REQUIRED"):
            rank_direct_labeled_curve_family(s,{"bindings":[]},x_value=60)

    def test_no_benchmark_or_external_model_authority(self):
        s=scene([polyline(35,RED),polyline(75,GREEN)])
        ocr={"text_items":[
            item("a","Alpha",102,30,128,40),
            item("b","Beta",102,70,128,80),
        ]}
        b=bind_direct_curve_labels(s,ocr)
        out=rank_direct_labeled_curve_family(s,b,x_value=60)
        for obj in (b,out):
            self.assertFalse(obj["benchmark_score_authority"])
            self.assertFalse(obj["domain_semantic_authority"])
            self.assertEqual(obj["external_general_purpose_model_runtime_dependency_count"],0)
            self.assertEqual(obj["donor_general_purpose_model_runtime_dependency_count"],0)
            self.assertEqual(obj["incremental_spend_usd"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
