import re
import unittest

from canonical.runtime.cad_t0_geometry_population import generate_case, public_case
from canonical.runtime.cad_t0_route_specific_candidate_v1 import solve_with_result


class CadRenderedLineAntishortcutRepairTests(unittest.TestCase):
    def test_render_equivalent_text_node_split_preserves_semantics(self):
        hidden = generate_case(123456789, 0)
        public = public_case(hidden)
        original_answer, _ = solve_with_result(public)
        svg = public["drawing_svg"]
        m = re.search(r'<text x="10" y="25" font-size="12">(.*?)</text>', svg, re.I | re.S)
        self.assertIsNotNone(m)
        text = m.group(1)
        cut = max(1, len(text)//2)
        left, right = text[:cut], text[cut:]
        mutated = svg[:m.start()] + (
            '<text x="10" y="25" font-size="12">' + left + '</text>'
            '<text x="300" y="25" font-size="12">' + right + '</text>'
        ) + svg[m.end():]
        public2 = dict(public)
        public2["drawing_svg"] = mutated
        mutated_answer, _ = solve_with_result(public2)
        self.assertEqual(original_answer["status"], mutated_answer["status"])
        self.assertEqual(original_answer["constraint_graph"], mutated_answer["constraint_graph"])

    def test_all_eight_families_still_parse(self):
        for slot in range(8):
            hidden = generate_case(900000 + slot, slot)
            answer, _ = solve_with_result(public_case(hidden))
            self.assertIn(answer["status"], {"SOLID","NONIDENTIFIABLE"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
