import unittest

from canonical.runtime.cad_t0_route_specific_candidate_v1 import _parse_visible, _texts


class CadSourceStructureAntishortcutRepairTests(unittest.TestCase):
    ORIGINAL = """<svg xmlns="http://www.w3.org/2000/svg" width="640" height="120">
    <text x="10" y="25">FRONT: rectangle 20 mm x 10 mm</text>
    <text x="10" y="45">DEPTH: 5 mm</text>
    <text x="10" y="65">Three orthographic views; all dimensions nominal.</text>
    </svg>"""
    SPLIT_EQUIVALENT = """<svg xmlns="http://www.w3.org/2000/svg" width="640" height="120">
    <text x="10" y="25">FRONT: rectangle 20 mm</text><text x="180" y="25"> x 10 mm</text>
    <text x="10" y="45">DEPTH: 5 mm</text>
    <text x="10" y="65">Three orthographic views; all dimensions nominal.</text>
    </svg>"""
    SPLIT_REVERSED_DOM = """<svg xmlns="http://www.w3.org/2000/svg" width="640" height="120">
    <text x="180" y="25"> x 10 mm</text><text x="10" y="25">FRONT: rectangle 20 mm</text>
    <text x="10" y="45">DEPTH: 5 mm</text>
    <text x="10" y="65">Three orthographic views; all dimensions nominal.</text>
    </svg>"""
    LINE_DOM_REORDER = """<svg xmlns="http://www.w3.org/2000/svg" width="640" height="120">
    <text x="10" y="45">DEPTH: 5 mm</text>
    <text x="10" y="65">Three orthographic views; all dimensions nominal.</text>
    <text x="10" y="25">FRONT: rectangle 20 mm x 10 mm</text>
    </svg>"""
    ENTITY_EQUIVALENT = """<svg xmlns="http://www.w3.org/2000/svg" width="640" height="120">
    <text x="10" y="25">FRONT: rectangle 20 mm &#120; 10 mm</text>
    <text x="10" y="45">DEPTH: 5 mm</text>
    <text x="10" y="65">Three orthographic views; all dimensions nominal.</text>
    </svg>"""
    INVISIBLE_INJECTION = """<svg xmlns="http://www.w3.org/2000/svg" width="640" height="120">
    <text x="10" y="25">FRONT: rectangle 20 mm x 10 mm</text>
    <text x="10" y="45" style="display:none">DEPTH: 999 mm</text>
    <text x="10" y="45">DEPTH: 5 mm</text>
    <text x="10" y="65">Three orthographic views; all dimensions nominal.</text>
    </svg>"""

    def parsed(self, svg):
        return _parse_visible(_texts(svg))

    def test_node_split_reconstructs_same_rows(self):
        self.assertEqual(_texts(self.ORIGINAL), _texts(self.SPLIT_EQUIVALENT))

    def test_node_split_preserves_parse(self):
        self.assertEqual(self.parsed(self.ORIGINAL), self.parsed(self.SPLIT_EQUIVALENT))

    def test_same_line_dom_order_does_not_change_parse(self):
        self.assertEqual(self.parsed(self.ORIGINAL), self.parsed(self.SPLIT_REVERSED_DOM))

    def test_cross_line_dom_order_does_not_change_parse(self):
        self.assertEqual(self.parsed(self.ORIGINAL), self.parsed(self.LINE_DOM_REORDER))

    def test_character_entity_encoding_does_not_change_parse(self):
        self.assertEqual(self.parsed(self.ORIGINAL), self.parsed(self.ENTITY_EQUIVALENT))

    def test_invisible_text_cannot_change_visible_geometry_inference(self):
        self.assertEqual(self.parsed(self.ORIGINAL), self.parsed(self.INVISIBLE_INJECTION))


if __name__ == "__main__":
    unittest.main(verbosity=2)
