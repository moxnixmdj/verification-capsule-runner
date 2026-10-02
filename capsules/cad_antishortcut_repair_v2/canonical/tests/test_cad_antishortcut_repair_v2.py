import re
import unittest

from canonical.runtime.cad_t0_geometry_population import generate_case, public_case, FAMILIES
from canonical.runtime.cad_t0_route_specific_candidate_v1 import _texts, _parse_visible


def split_first_drawing_line(svg: str) -> str:
    matches = list(re.finditer(r'(<text\\b[^>]*\\by="25"[^>]*>)(.*?)(</text>)', svg, flags=re.I | re.S))
    if len(matches) != 1:
        raise AssertionError(f"expected exactly one first drawing line, got {len(matches)}")
    m = matches[0]
    inner = m.group(2)
    cut = inner.find(" ", max(1, len(inner) // 3))
    if cut < 0:
        cut = inner.find(" ")
    if cut < 0:
        raise AssertionError("drawing line has no split point")
    left, right = inner[:cut], inner[cut:]
    attrs = m.group(1)
    second_attrs = re.sub(r'\\bx="[^"]*"', 'x="300"', attrs, count=1)
    replacement = attrs + left + "</text>" + second_attrs + right + "</text>"
    return svg[:m.start()] + replacement + svg[m.end():]


class CadAntishortcutRepairV2Tests(unittest.TestCase):
    def test_original_falsifier_now_preserves_semantics(self):
        original = """<svg xmlns="http://www.w3.org/2000/svg" width="640" height="120">
        <text x="10" y="25">FRONT: rectangle 20 mm x 10 mm</text>
        <text x="10" y="45">DEPTH: 5 mm</text>
        <text x="10" y="65">Three orthographic views; all dimensions nominal.</text>
        </svg>"""
        split_equivalent = """<svg xmlns="http://www.w3.org/2000/svg" width="640" height="120">
        <text x="10" y="25">FRONT: rectangle 20 mm</text><text x="180" y="25"> x 10 mm</text>
        <text x="10" y="45">DEPTH: 5 mm</text>
        <text x="10" y="65">Three orthographic views; all dimensions nominal.</text>
        </svg>"""
        self.assertEqual(_texts(original), _texts(split_equivalent))
        self.assertEqual(_parse_visible(_texts(original)), _parse_visible(_texts(split_equivalent)))

    def test_all_eight_frozen_geometry_families_are_dom_split_invariant(self):
        seen = set()
        for slot, family in enumerate(FAMILIES):
            hidden = generate_case(314159265 + slot * 271, slot)
            self.assertEqual(hidden["_oracle"]["family"], family)
            visible = public_case(hidden)
            original_svg = visible["drawing_svg"]
            mutated_svg = split_first_drawing_line(original_svg)
            self.assertEqual(_texts(original_svg), _texts(mutated_svg), family)
            self.assertEqual(
                _parse_visible(_texts(original_svg)),
                _parse_visible(_texts(mutated_svg)),
                family,
            )
            seen.add(family)
        self.assertEqual(seen, set(FAMILIES))


if __name__ == "__main__":
    unittest.main(verbosity=2)
