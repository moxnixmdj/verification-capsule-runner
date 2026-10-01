import unittest
from requirement_graph_kernel import compile_requirement_contract, requirement_mutation_score

def corpus():
    return [
        {"id":"REQ-INPUT","critical":True,"dependencies":[],"children":[],"open_questions":[],
         "clauses":[{"id":"C-IN","keyword":"MUST","covered_by_scenarios":["S-IN"]}],
         "scenarios":[{"id":"S-IN","given":["raw input"],"when":["normalize"],"then":["normalized input exists"]}]},
        {"id":"REQ-CALC","critical":True,"dependencies":["REQ-INPUT"],"children":[],"open_questions":[],
         "clauses":[{"id":"C-CALC","keyword":"MUST","covered_by_scenarios":["S-CALC"]}],
         "scenarios":[{"id":"S-CALC","given":["normalized input"],"when":["calculate"],"then":["intermediate and output trace exists"]}]},
        {"id":"REQ-CHECK","critical":True,"dependencies":["REQ-CALC"],"children":[],"open_questions":[],
         "clauses":[{"id":"C-CHECK","keyword":"MUST","covered_by_scenarios":["S-CHECK"]}],
         "scenarios":[{"id":"S-CHECK","given":["candidate output"],"when":["independent check"],"then":["observable acceptance consequence"]}]},
    ]

class IndependentKernelTests(unittest.TestCase):
    def test_valid_contract(self):
        self.assertTrue(compile_requirement_contract(corpus(), expected_required_ids=["REQ-INPUT","REQ-CALC","REQ-CHECK"])["pass"])

    def test_delete_each_required_node_fails(self):
        expected=["REQ-INPUT","REQ-CALC","REQ-CHECK"]
        for i in range(3):
            c=corpus(); c.pop(i)
            self.assertFalse(compile_requirement_contract(c, expected_required_ids=expected)["pass"])

    def test_ambiguity_fails(self):
        c=corpus(); c[1]["open_questions"]=["which formula applies?"]
        self.assertFalse(compile_requirement_contract(c, expected_required_ids=["REQ-INPUT","REQ-CALC","REQ-CHECK"])["pass"])

    def test_uncovered_must_fails(self):
        c=corpus(); c[1]["clauses"][0]["covered_by_scenarios"]=[]
        self.assertFalse(compile_requirement_contract(c, expected_required_ids=["REQ-INPUT","REQ-CALC","REQ-CHECK"])["pass"])

    def test_dangling_dependency_fails(self):
        c=corpus(); c[2]["dependencies"]=["REQ-NOPE"]
        self.assertFalse(compile_requirement_contract(c, expected_required_ids=["REQ-INPUT","REQ-CALC","REQ-CHECK"])["pass"])

    def test_cycle_fails(self):
        c=corpus(); c[0]["dependencies"]=["REQ-CHECK"]
        self.assertFalse(compile_requirement_contract(c, expected_required_ids=["REQ-INPUT","REQ-CALC","REQ-CHECK"])["pass"])

    def test_seeded_mutations_are_all_killed(self):
        score=requirement_mutation_score(corpus())
        self.assertTrue(score["pass"])
        self.assertEqual(score["survived"],0)
        self.assertEqual(score["kill_fraction"],1.0)
        self.assertGreaterEqual(score["total"],8)

if __name__=="__main__":
    unittest.main()
