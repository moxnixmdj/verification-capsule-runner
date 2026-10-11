from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from canonical.runtime.bound_capabilities import chart_axis_title_unit_binding_v1 as c


def cand(text, conf=95, source="independent"):
    return {
        "text": text,
        "confidence": conf,
        "source": source,
        "evidence_kind": "INDEPENDENT_SUPPLIED_CANDIDATE",
    }


class IndependentChartAxisTitleUnitBindingV1(unittest.TestCase):
    def test_word_substrings_do_not_create_meter_or_gram_units(self):
        for text in ("Program Count", "Amplitude", "Sample Group"):
            with self.assertRaises(c.AxisTitleUnitBindingError):
                c.parse_axis_label(text)

    def test_angular_frequency_is_not_plain_frequency(self):
        out=c.parse_axis_label("Angular Frequency (rad/s)")
        self.assertEqual(out["semantic_role"],"ANGULAR_FREQUENCY")
        self.assertEqual(out["canonical_unit"],"RAD_PER_SECOND")
        self.assertEqual(out["unit_dimension"],"ANGULAR_FREQUENCY")

    def test_temperature_kelvin_parenthetical(self):
        out=c.parse_axis_label("Temperature (K)")
        self.assertEqual(out["semantic_role"],"TEMPERATURE")
        self.assertEqual(out["canonical_unit"],"KELVIN")

    def test_pressure_mpa(self):
        out=c.parse_axis_label("Pressure [MPa]")
        self.assertEqual(out["semantic_role"],"PRESSURE")
        self.assertEqual(out["canonical_unit"],"MEGAPASCAL")

    def test_mass_role_and_unit(self):
        out=c.parse_axis_label("Mass (kg)")
        self.assertEqual(out["semantic_role"],"WEIGHT")
        self.assertEqual(out["canonical_unit"],"KILOGRAM")

    def test_length_unit_conflict_fails_closed(self):
        with self.assertRaisesRegex(c.AxisTitleUnitBindingError,"AXIS_UNIT_CONFLICT"):
            c.parse_axis_label("Height (cm / mm)")

    def test_time_unit_conflict_fails_closed(self):
        with self.assertRaisesRegex(c.AxisTitleUnitBindingError,"AXIS_UNIT_CONFLICT"):
            c.parse_axis_label("Time (days / weeks)")

    def test_unit_only_title_can_bind_without_inventing_role(self):
        out=c.parse_axis_label("(dB)")
        self.assertIsNone(out["semantic_role"])
        self.assertEqual(out["canonical_unit"],"DECIBEL")

    def test_role_only_title_can_bind_without_inventing_unit(self):
        out=c.parse_axis_label("Temperature")
        self.assertEqual(out["semantic_role"],"TEMPERATURE")
        self.assertIsNone(out["canonical_unit"])

    def test_two_different_high_quality_axis_titles_fail_closed(self):
        out=c.select_axis_binding([
            cand("Age (years)",96,"one"),
            cand("Time (months)",96,"two"),
        ],ambiguity_margin=1.0)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"AMBIGUOUS_AXIS_TITLE_UNIT_CANDIDATES")

    def test_low_confidence_semantic_noise_is_not_selected(self):
        ocr={"text_items":[
            {"text":"Frequency (Hz)","confidence_min":12},
            {"text":"100","confidence_min":99},
        ]}
        rows=c._candidate_rows(ocr,"noise")
        self.assertEqual(rows,[])

    def test_combined_split_axis_title_retains_explicit_unit(self):
        ocr={"text_items":[
            {"text":"Survival Probability","confidence_min":93},
            {"text":"(%)","confidence_min":91},
            {"text":"0","confidence_min":99},
            {"text":"100","confidence_min":99},
        ]}
        rows=c._candidate_rows(ocr,"split")
        matches=[
            r for r in rows
            if r.get("semantic_role")=="SURVIVAL_PROBABILITY"
            and r.get("canonical_unit")=="PERCENT"
        ]
        self.assertTrue(matches,rows)

    def test_partial_binding_does_not_fabricate_missing_axis(self):
        out=c.bind_axis_candidates([cand("Frequency (Hz)")],[])
        self.assertTrue(out["pass"])
        self.assertEqual(out["bound_axis_count"],1)
        self.assertFalse(out["y_axis"]["pass"])

    def test_real_rotated_y_axis_and_horizontal_x_axis_ocr(self):
        font_path=Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
        self.assertTrue(font_path.is_file(),font_path)
        font=ImageFont.truetype(str(font_path),30)
        small=ImageFont.truetype(str(font_path),22)

        w,h=1000,700
        im=Image.new("RGB",(w,h),"white")
        d=ImageDraw.Draw(im)
        left,top,right,bottom=220,100,900,520

        d.line((left,bottom,right,bottom),fill="black",width=4)
        d.line((left,top,left,bottom),fill="black",width=4)

        # Numeric ticks are intentionally present so the semantic binder must
        # reject them rather than confuse them with titles.
        for x,text in ((left,"0"),((left+right)//2,"12"),(right,"24")):
            d.line((x,bottom-5,x,bottom+5),fill="black",width=2)
            d.text((x-10,bottom+12),text,fill="black",font=small)
        for y,text in ((bottom,"0"),((top+bottom)//2,"50"),(top,"100")):
            d.line((left-5,y,left+5,y),fill="black",width=2)
            d.text((left-55,y-12),text,fill="black",font=small)

        x_title="Time (months)"
        bx=d.textbbox((0,0),x_title,font=font)
        tw=bx[2]-bx[0]
        d.text(((left+right-tw)//2,620),x_title,fill="black",font=font)

        y_title="Survival Probability (%)"
        probe=Image.new("RGB",(520,70),"white")
        pd=ImageDraw.Draw(probe)
        pd.text((10,15),y_title,fill="black",font=font)
        rotated=probe.rotate(90,expand=True)
        py=max(0,(h-rotated.height)//2)
        im.paste(rotated,(25,py))

        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"chart.png"
            im.save(p)
            out=c.bind_axis_titles_and_units(p)

        self.assertTrue(out["pass"],out)
        self.assertEqual(out["bound_axis_count"],2,out)
        xb=out["x_axis"]["binding"]
        yb=out["y_axis"]["binding"]
        self.assertEqual(xb["semantic_role"],"TIME")
        self.assertEqual(xb["canonical_unit"],"MONTH")
        self.assertEqual(yb["semantic_role"],"SURVIVAL_PROBABILITY")
        self.assertEqual(yb["canonical_unit"],"PERCENT")
        self.assertEqual(out["external_general_purpose_model_runtime_dependency_count"],0)
        self.assertFalse(out["domain_semantic_authority"])
        self.assertFalse(out["benchmark_score_authority"])


if __name__=="__main__":
    unittest.main(verbosity=2)
