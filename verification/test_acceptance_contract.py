import random, unittest
from acceptance_contract import (
  canonical_payload_hash, validate_acceptance_payload, validate_lease_authorization,
  validate_lease_revalidation, terminal_acceptance_errors, audit_required_graph
)
from controller_fast import runtime_authority_errors

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
  def test_lease_authorization_fail_closed(self):
    good={
      "schema":"BRAIN_FAST_BURST_LEASE_AUTHORIZATION_V1","session_id":"s1","task":"t1",
      "authorization":True,"lease_merged_to_main":True,
      "canonical_brain_commit":"a"*40,
      "canonical_lease_path":"canonical/governance/LEASE_T1.json","sample_rank":15
    }
    self.assertEqual(validate_lease_authorization(good,"s1","t1"),[])
    bad=dict(good); bad["lease_merged_to_main"]=False
    self.assertIn("LEASE_NOT_CONFIRMED_MERGED_TO_MAIN",validate_lease_authorization(bad,"s1","t1"))
    bad=dict(good); bad["canonical_brain_commit"]="not-a-commit"
    self.assertIn("CANONICAL_BRAIN_COMMIT_INVALID",validate_lease_authorization(bad,"s1","t1"))


  def test_per_action_lease_revalidation_is_single_scope_and_burst_bound(self):
    lease={
      "schema":"BRAIN_FAST_BURST_LEASE_AUTHORIZATION_V1","session_id":"s1","task":"t1",
      "authorization":True,"lease_merged_to_main":True,
      "canonical_brain_commit":"a"*40,
      "canonical_lease_path":"canonical/governance/LEASE_T1.json","sample_rank":16
    }
    burst={
      "schema":"BRAIN_FAST_BURST_LEASE_REVALIDATION_V1","session_id":"s1","task":"t1",
      "authorization":True,"scope":"BURST","burst_id":0,
      "canonical_brain_commit":"b"*40,
      "canonical_lease_path":"canonical/governance/LEASE_T1.json","sample_rank":16
    }
    self.assertEqual(validate_lease_revalidation(
      burst,"s1","t1",lease,expected_scope="BURST",expected_burst_id=0
    ),[])
    self.assertIn("LEASE_REVALIDATION_BURST_MISMATCH",validate_lease_revalidation(
      burst,"s1","t1",lease,expected_scope="BURST",expected_burst_id=1
    ))
    self.assertIn("PER_ACTION_CANONICAL_LEASE_REVALIDATION_REQUIRED",runtime_authority_errors(
      session_id="s1",task="t1",lease_authorized=True,bound_lease=lease,
      revalidation=None,scope="BURST",burst_id=0,pr_open=True
    ))
    self.assertIn("RUNNER_PR_NOT_OPEN",runtime_authority_errors(
      session_id="s1",task="t1",lease_authorized=True,bound_lease=lease,
      revalidation=burst,scope="BURST",burst_id=0,pr_open=False
    ))
    self.assertEqual(runtime_authority_errors(
      session_id="s1",task="t1",lease_authorized=True,bound_lease=lease,
      revalidation=burst,scope="BURST",burst_id=0,pr_open=True
    ),[])

  def test_terminal_requires_fresh_terminal_revalidation(self):
    lease={
      "canonical_lease_path":"canonical/governance/LEASE_T1.json","sample_rank":16
    }
    terminal={
      "schema":"BRAIN_FAST_BURST_LEASE_REVALIDATION_V1","session_id":"s1","task":"t1",
      "authorization":True,"scope":"TERMINAL",
      "canonical_brain_commit":"c"*40,
      "canonical_lease_path":"canonical/governance/LEASE_T1.json","sample_rank":16
    }
    self.assertEqual(runtime_authority_errors(
      session_id="s1",task="t1",lease_authorized=True,bound_lease=lease,
      revalidation=terminal,scope="TERMINAL",pr_open=True
    ),[])
    terminal["scope"]="BURST"; terminal["burst_id"]=0
    self.assertIn("LEASE_REVALIDATION_SCOPE_MISMATCH",runtime_authority_errors(
      session_id="s1",task="t1",lease_authorized=True,bound_lease=lease,
      revalidation=terminal,scope="TERMINAL",pr_open=True
    ))

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
