from __future__ import annotations

import unittest

from canonical.runtime.bound_capabilities.chart_curve_inverse_query_v1 import (
    CurveInverseQueryError,
    query_curve_x_at_y,
)

RED=[216,24,24]
BLUE=[24,80,216]


def axes(*, log_x=False, log_y=False):
    return {
        "x":{
            "scale":"LOG10" if log_x else "LINEAR",
            "transformed_value_from_pixel":[0.01 if log_x else 1.0,0.0],
        },
        "y":{
            "scale":"LOG10" if log_y else "LINEAR",
            "transformed_value_from_pixel":[-0.01 if log_y else -1.0,2.0 if log_y else 110.0],
        },
    }


def legend():
    return {"bindings":[{"label":"Series A","color_bucket":RED}]}


def scene(rows, *, ax=None):
    return {"plot_box":[10,10,110,110],"axes":ax or axes(),"color_polylines":rows}


class IndependentCurveInverseV1(unittest.TestCase):
    def test_reversed_point_order_unique_crossing(self):
        pts=[[100,50],[80,60],[60,70],[40,80],[20,90]]
        rows=[{"color_bucket":RED,"column_count":5,"x_range":[20,100],"points":pts}]
        out=query_curve_x_at_y(scene(rows),legend(),label="Series A",y_value=40,max_interpolation_gap_fraction=1.0)
        self.assertAlmostEqual(out["value"],60.0,places=6)

    def test_nonmatching_color_is_ignored(self):
        red=[[20,90],[100,50]]
        blue=[[20,80],[100,40]]
        rows=[
            {"color_bucket":RED,"column_count":2,"x_range":[20,100],"points":red},
            {"color_bucket":BLUE,"column_count":2,"x_range":[20,100],"points":blue},
        ]
        out=query_curve_x_at_y(scene(rows),legend(),label="Series A",y_value=40,max_interpolation_gap_fraction=1.0)
        self.assertAlmostEqual(out["value"],60.0,places=6)

    def test_three_crossing_wave_is_rejected(self):
        pts=[[20,90],[40,60],[60,90],[80,60],[100,90]]
        rows=[{"color_bucket":RED,"column_count":5,"x_range":[20,100],"points":pts}]
        with self.assertRaisesRegex(CurveInverseQueryError,"CURVE_NOT_UNIQUELY_INVERTIBLE_AT_QUERY"):
            query_curve_x_at_y(scene(rows),legend(),label="Series A",y_value=40,max_interpolation_gap_fraction=1.0)

    def test_horizontal_nonquery_segment_is_harmless(self):
        pts=[[20,90],[40,90],[60,70],[80,60],[100,50]]
        rows=[{"color_bucket":RED,"column_count":5,"x_range":[20,100],"points":pts}]
        out=query_curve_x_at_y(scene(rows),legend(),label="Series A",y_value=40,max_interpolation_gap_fraction=1.0)
        self.assertAlmostEqual(out["value"],60.0,places=6)

    def test_nonpositive_log_y_query_is_rejected(self):
        pts=[[20,90],[100,50]]
        rows=[{"color_bucket":RED,"column_count":2,"x_range":[20,100],"points":pts}]
        with self.assertRaisesRegex(CurveInverseQueryError,"LOG_AXIS_REQUIRES_POSITIVE_QUERY"):
            query_curve_x_at_y(scene(rows,ax=axes(log_y=True)),legend(),label="Series A",y_value=0,max_interpolation_gap_fraction=1.0)

    def test_exact_vertex_deduplicates_without_hiding_second_crossing(self):
        pts=[[20,90],[60,70],[80,50],[100,70]]
        rows=[{"color_bucket":RED,"column_count":4,"x_range":[20,100],"points":pts}]
        with self.assertRaisesRegex(CurveInverseQueryError,"CURVE_NOT_UNIQUELY_INVERTIBLE_AT_QUERY:2"):
            query_curve_x_at_y(scene(rows),legend(),label="Series A",y_value=40,max_interpolation_gap_fraction=1.0)


if __name__=="__main__":
    unittest.main(verbosity=2)
