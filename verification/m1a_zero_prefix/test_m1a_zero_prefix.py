import unittest
from compound_visual_feature_resolver import resolve
from engineering_feature_notation import parse_feature_notation
from declarative_spatial_notation import match, validate_grammar

class M1AZeroPrefix(unittest.TestCase):
    # Frozen DEV cases only. The prior heldout scenes are deliberately absent.
    def test_dev_2x_equal_holes(self):
        fs=[
          {"kind":"circle","center":[180,160],"radius":28,"id":"H1"},
          {"kind":"circle","center":[330,160],"radius":28,"id":"H2"},
        ]
        r=resolve(fs,parse_feature_notation("2X DIA 10 THRU"),[180,132])
        self.assertEqual(r["status"],"RESOLVED")
        self.assertEqual(r["feature_ids"],["H1","H2"])

    def test_dev_3x_with_distractor(self):
        fs=[
          {"kind":"circle","center":[140,190],"radius":25,"id":"H1"},
          {"kind":"circle","center":[285,190],"radius":25,"id":"H2"},
          {"kind":"circle","center":[430,190],"radius":25,"id":"H3"},
          {"kind":"circle","center":[515,80],"radius":12,"id":"H4"},
        ]
        r=resolve(fs,parse_feature_notation("3X DIA 8 THRU"),[140,165])
        self.assertEqual(r["status"],"RESOLVED")
        self.assertEqual(r["feature_ids"],["H1","H2","H3"])

    def test_dev_slot_target(self):
        fs=[
          {"kind":"slot","center":[300,160],"length":150,"width":42,"id":"S1"},
          {"kind":"circle","center":[100,160],"radius":24,"id":"H1"},
        ]
        ann={"status":"PARSED","kind":"slot_feature","feature_kind":"slot","quantity":1,"width":42}
        r=resolve(fs,ann,[225,160])
        self.assertEqual((r["status"],r["feature_id"],r["feature_kind"]),("RESOLVED","S1","slot"))

    def test_dev_ambiguous_quantity_does_not_guess(self):
        fs=[
          {"kind":"circle","center":[150,180],"radius":24,"id":"H1"},
          {"kind":"circle","center":[300,180],"radius":24,"id":"H2"},
          {"kind":"circle","center":[450,180],"radius":24,"id":"H3"},
        ]
        r=resolve(fs,parse_feature_notation("2X DIA 8 THRU"),[300,156])
        self.assertEqual(r["status"],"AMBIGUOUS")
        self.assertEqual(r["reason"],"QUANTITY_SUBSET_NONUNIQUE")

    def test_unseen_spatial_grammar_datum_left_of_frame(self):
        rules=[{
          "id":"datum_then_frame","kind":"datum_frame_pair",
          "roles":{"datum":{"class":"DATUM"},"frame":{"class":"FCF"}},
          "relations":[{"from":"datum","type":"LEFT_OF","to":"frame"}]
        }]
        nodes=[
          {"id":"n1","class":"DATUM","token":"A"},
          {"id":"n2","class":"FCF","token":"POSITION"},
          {"id":"n3","class":"TEXT","token":"NOTE"},
        ]
        rel=[{"from":"n1","type":"LEFT_OF","to":"n2"}]
        r=match(nodes,rel,rules)
        self.assertEqual(r["status"],"PARSED")
        self.assertEqual(r["match"]["roles"],{"DATUM":"N1","FRAME":"N2"})

    def test_second_unseen_grammar_transfers(self):
        rules=[{
          "id":"inspection_marker","kind":"inspection_marker",
          "roles":{"mark":{"class":"TRIANGLE"},"note":{"class":"NOTE"}},
          "relations":[{"from":"mark","type":"ABOVE","to":"note"}]
        }]
        nodes=[{"id":"m","class":"TRIANGLE"},{"id":"t","class":"NOTE"}]
        r=match(nodes,[{"from":"m","type":"ABOVE","to":"t"}],rules)
        self.assertEqual(r["status"],"PARSED")

    def test_multiple_spatial_assignments_are_ambiguous(self):
        rules=[{
          "id":"pair","kind":"pair",
          "roles":{"datum":{"class":"DATUM"},"frame":{"class":"FCF"}},
          "relations":[{"from":"datum","type":"LEFT_OF","to":"frame"}]
        }]
        nodes=[{"id":"d1","class":"DATUM"},{"id":"d2","class":"DATUM"},{"id":"f","class":"FCF"}]
        rel=[
          {"from":"d1","type":"LEFT_OF","to":"f"},
          {"from":"d2","type":"LEFT_OF","to":"f"},
        ]
        self.assertEqual(match(nodes,rel,rules)["status"],"AMBIGUOUS")

    def test_missing_relation_fails_closed(self):
        rules=[{
          "id":"pair","kind":"pair",
          "roles":{"a":{"class":"A"},"b":{"class":"B"}},
          "relations":[{"from":"a","type":"CONNECTED_TO","to":"b"}]
        }]
        nodes=[{"id":"a","class":"A"},{"id":"b","class":"B"}]
        self.assertEqual(match(nodes,[],rules)["status"],"FAIL_CLOSED")

    def test_unsupported_relation_rejected(self):
        rules=[{
          "id":"bad","kind":"bad",
          "roles":{"a":{"class":"A"},"b":{"class":"B"}},
          "relations":[{"from":"a","type":"MAGIC_OVERLAP","to":"b"}]
        }]
        self.assertFalse(validate_grammar(rules)["valid"])

    def test_duplicate_observed_node_id_fails_closed(self):
        rules=[{"id":"one","kind":"one","roles":{"a":{"class":"A"}},"relations":[]}]
        nodes=[{"id":"x","class":"A"},{"id":"x","class":"A"}]
        self.assertEqual(match(nodes,[],rules)["status"],"FAIL_CLOSED")

if __name__=="__main__":
    unittest.main()
