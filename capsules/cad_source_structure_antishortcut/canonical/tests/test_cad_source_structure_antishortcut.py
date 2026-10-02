import unittest
from canonical.runtime.cad_t0_route_specific_candidate_v1 import _texts, _parse_visible, CandidateError

class CadSourceStructureAntishortcutTests(unittest.TestCase):
    def test_same_rendered_line_split_across_svg_text_nodes_breaks_candidate(self):
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
        candidate, contract = _parse_visible(_texts(original))
        self.assertEqual(candidate["status"], "SOLID")
        self.assertIsNotNone(contract)
        with self.assertRaises(CandidateError):
            _parse_visible(_texts(split_equivalent))

    def test_equivalent_svg_dom_split_is_not_hidden_information_change(self):
        # Mutation changes only SVG source node boundaries. Visible strings and numeric values
        # remain on the same y positions; no oracle field, case identity, or dimension changes.
        split_equivalent = """<svg xmlns="http://www.w3.org/2000/svg" width="640" height="120">
        <text x="10" y="25">FRONT: rectangle 20 mm</text><text x="180" y="25"> x 10 mm</text>
        <text x="10" y="45">DEPTH: 5 mm</text>
        </svg>"""
        rows = _texts(split_equivalent)
        self.assertEqual(rows, ["FRONT: rectangle 20 mm", "x 10 mm", "DEPTH: 5 mm"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
