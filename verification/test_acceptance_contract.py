import random, unittest
from acceptance_contract import (
  canonical_payload_hash, validate_acceptance_payload,
  terminal_acceptance_errors, audit_required_graph
)

def base_payload():
    return {
      "schema":"BRAIN_FAST_BURST_ACCEPTANCE_MODEL_V1",
      "session_id":"s1",
      "frozen_before_builder":True,
      "solution_tests_verifier_exposed":False,
      "behavioral_contract":{
        "behavior_id":"B1","inputs":"i","environment_state":"e",
        "allowed_information":"a","required_output_or_action":"o",
        "success_condition":"s","failure_condition":"f",
        "terminal_consequence":"t","verification_route":"v",
        "dependency_boundary":"d","scope":"q"
      },
      "requirements":[
        {"id":"R1","statement":"preserve factor x","source_basis":"visible spec","applicable":True},
        {"id":"R2","statement":"output y","source_basis":"visible spec","applicable":True}
      ],
      "acceptance_checks":[
        {"id":"A1","kind":"LINEAGE_COVERAGE","predicted_consequence":"x reaches y",
         "evidence_basis":"independent graph audit","independence_class":"STRUCTURAL_ORACLE",
         "covers_requirements":["R1","R2"]}
      ]
    }

class TestAcceptanceContract(unittest.TestCase):
  def test_valid_and_hash_stable(self):
    p=base_payload()
    self.assertEqual(validate_acceptance_payload(p,"s1"),[])
    h1=canonical_payload_hash(p)
    q=dict(reversed(list(p.items())))
    self.assertEqual(h1,canonical_payload_hash(q))

  def test_missing_behavior_fails(self):
    p=base_payload(); del p["behavioral_contract"]["scope"]
    self.assertIn("BEHAVIOR_FIELD_MISSING:scope",validate_acceptance_payload(p,"s1"))

  def test_uncovered_requirement_fails(self):
    p=base_payload(); p["acceptance_checks"][0]["covers_requirements"]=["R1"]
    self.assertIn("REQUIREMENT_NOT_COVERED:R2",validate_acceptance_payload(p,"s1"))

  def test_builder_recompute_is_not_independent(self):
    p=base_payload(); p["acceptance_checks"][0]["independence_class"]="BUILDER_RECOMPUTE"
    self.assertIn("CHECK_NOT_INDEPENDENT:A1",validate_acceptance_payload(p,"s1"))

  def test_terminal_must_bind_frozen_hash_and_ids(self):
    p=base_payload(); h=canonical_payload_hash(p)
    terminal={"acceptance_contract_sha256":h,"acceptance_criteria":[{"id":"A1","status":"PASS","evidence":"oracle:x"}]}
    self.assertEqual(terminal_acceptance_errors(terminal,p,h),[])
    terminal["acceptance_contract_sha256"]="bad"
    self.assertIn("ACCEPTANCE_CONTRACT_HASH_MISMATCH",terminal_acceptance_errors(terminal,p,h))

  def test_random_graph_omission_detection(self):
    rng=random.Random(20261001)
    for _ in range(500):
      n=rng.randint(3,18)
      nodes=[f"N{i}" for i in range(n)]
      edges=[(nodes[i],nodes[i+1]) for i in range(n-1)]
      ok=audit_required_graph(nodes,edges,nodes,edges,inputs=[nodes[0]],outputs=[nodes[-1]])
      self.assertTrue(ok["pass"])
      k=rng.randrange(len(edges))
      bad_edges=edges[:k]+edges[k+1:]
      bad=audit_required_graph(nodes,edges,nodes,bad_edges,inputs=[nodes[0]],outputs=[nodes[-1]])
      self.assertFalse(bad["pass"])
      self.assertIn(edges[k],bad["missing_edges"])

if __name__=="__main__":
  unittest.main(verbosity=2)
