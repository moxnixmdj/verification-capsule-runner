import random
import unittest

from semantic_operator_counterfactuals import (
    extract_semantic_operators,
    generate_counterfactual_obligations,
    validate_operator_bindings,
    validate_counterfactual_coverage,
)


def bindings(text, source):
    rows=[]
    for op in extract_semantic_operators(text, source=source):
        row={"operator_id":op.operator_id,"semantic_class":op.semantic_class}
        if op.bound_value is not None:
            row["bound_value"]=op.bound_value
        if op.semantic_class=="AMBIGUOUS_ANY":
            row["interpretations"]=["existential_or_free_choice","universal_in_negative_context"]
        rows.append(row)
    return rows


def scenarios(text, source):
    rows=[]
    for ob in generate_counterfactual_obligations(text, source=source):
        k=ob.counterfactual_kind
        disp="ACCEPT" if "ACCEPTED" in k else ("DISAMBIGUATE" if ("DISAMBIGUATED" in k or "DISTINGUISHED" in k) else "REJECT")
        rows.append({"operator_id":ob.operator_id,"counterfactual_kind":k,"expected_disposition":disp})
    return rows


class IndependentSemanticOperatorVerification(unittest.TestCase):
    def test_shared_wrong_minmax_consensus_is_killed(self):
        text="Retain at least 4 sources."
        op=extract_semantic_operators(text,source="s")[0]
        verdict=validate_operator_bindings(text,[{
            "operator_id":op.operator_id,
            "semantic_class":"MAX_INCLUSIVE",
            "bound_value":4
        }],source="s")
        self.assertFalse(verdict["pass"])

    def test_threshold_boundary_counterfactuals_are_directional(self):
        lo=generate_counterfactual_obligations("Use at least 5 sources.",source="lo")
        hi=generate_counterfactual_obligations("Use at most 5 sources.",source="hi")
        self.assertIn("BELOW_BOUND_MUST_BE_REJECTED",{x.counterfactual_kind for x in lo})
        self.assertIn("ABOVE_BOUND_MUST_BE_REJECTED",{x.counterfactual_kind for x in hi})

    def test_missing_counterfactual_fails_closed(self):
        text="Every output must not be written before approval."
        rows=scenarios(text,"m")
        rows=rows[:-1]
        self.assertFalse(validate_counterfactual_coverage(text,rows,source="m")["pass"])

    def test_any_without_disambiguation_fails(self):
        text="Do not accept any unsigned item."
        rows=bindings(text,"a")
        for r in rows:
            if r["semantic_class"]=="AMBIGUOUS_ANY":
                r.pop("interpretations")
        self.assertFalse(validate_operator_bindings(text,rows,source="a")["pass"])

    def test_random_numeric_semantics_4000(self):
        rng=random.Random(552211)
        choices=[
            ("at least","MIN_INCLUSIVE"),
            ("no less than","MIN_INCLUSIVE"),
            ("at most","MAX_INCLUSIVE"),
            ("no more than","MAX_INCLUSIVE"),
            ("exactly","EXACT_VALUE"),
        ]
        for i in range(4000):
            token,expected=rng.choice(choices)
            n=rng.randint(-10000,10000)
            text=f"Rule {i}: retain {token} {n} records."
            op=extract_semantic_operators(text,source=f"r{i}")
            self.assertEqual(len(op),1)
            self.assertEqual(op[0].semantic_class,expected)
            self.assertEqual(op[0].bound_value,float(n))
            self.assertTrue(validate_operator_bindings(text,bindings(text,f"r{i}"),source=f"r{i}")["pass"])
            self.assertTrue(validate_counterfactual_coverage(text,scenarios(text,f"r{i}"),source=f"r{i}")["pass"])

    def test_random_opposite_mapping_rejected_2000(self):
        rng=random.Random(8411)
        for i in range(2000):
            low=bool(rng.getrandbits(1))
            token="at least" if low else "at most"
            expected="MIN_INCLUSIVE" if low else "MAX_INCLUSIVE"
            wrong="MAX_INCLUSIVE" if low else "MIN_INCLUSIVE"
            n=rng.randint(0,999)
            text=f"Need {token} {n} checks."
            op=extract_semantic_operators(text,source=f"x{i}")[0]
            self.assertEqual(op.semantic_class,expected)
            verdict=validate_operator_bindings(text,[{
                "operator_id":op.operator_id,
                "semantic_class":wrong,
                "bound_value":n
            }],source=f"x{i}")
            self.assertFalse(verdict["pass"])

    def test_operator_id_changes_with_source_identity(self):
        text="Use exactly 2 outputs."
        a=extract_semantic_operators(text,source="A")[0]
        b=extract_semantic_operators(text,source="B")[0]
        self.assertNotEqual(a.operator_id,b.operator_id)


if __name__=="__main__":
    unittest.main()
