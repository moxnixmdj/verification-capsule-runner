import unittest

from canonical.runtime.sharded_finite_population_proof import (
    compile_execution_manifest, population_commitment, score_results, select_case_ids
)


class IndependentShardedProofTests(unittest.TestCase):
    def ids(self,n=120):
        return [f"opaque-{i:04d}" for i in range(n)]

    def manifest(self,seed="beacon",n=20,N=100):
        return compile_execution_manifest(
            case_ids=self.ids(N), sample_size=n, seed=seed,
            candidate_commit="cand", harness_commit="har", scorer_commit="score",
            runner_label="ubuntu-24.04", timeout_minutes=30
        )

    def test_selection_does_not_depend_on_population_input_order(self):
        ids=self.ids(80)
        self.assertEqual(
            select_case_ids(ids,17,"future-beacon"),
            select_case_ids(list(reversed(ids)),17,"future-beacon")
        )

    def test_no_replacement_and_exact_size(self):
        s=select_case_ids(self.ids(100),33,"beacon-x")
        self.assertEqual(len(s),33)
        self.assertEqual(len(set(s)),33)

    def test_seed_changes_sample(self):
        self.assertNotEqual(
            select_case_ids(self.ids(100),25,"beacon-a"),
            select_case_ids(self.ids(100),25,"beacon-b")
        )

    def test_population_commitment_is_order_invariant_and_content_sensitive(self):
        ids=self.ids(30)
        self.assertEqual(population_commitment(ids),population_commitment(list(reversed(ids))))
        changed=ids[:-1]+["different"]
        self.assertNotEqual(population_commitment(ids),population_commitment(changed))

    def test_every_sampled_id_must_return_exactly_once(self):
        m=self.manifest(n=10,N=50)
        rows=[{"case_id":x,"oracle_pass":True} for x in m["selected_case_ids"]]
        with self.assertRaises(ValueError):
            score_results(m,rows[:-1],threshold_rate=.3)
        with self.assertRaises(ValueError):
            score_results(m,rows+[rows[0]],threshold_rate=.3)

    def test_local_resource_failure_is_conservative_failure_not_resample(self):
        m=self.manifest(n=20,N=100)
        rows=[{"case_id":x,"oracle_pass":True} for x in m["selected_case_ids"]]
        victim=m["selected_case_ids"][7]
        rows[7]={"case_id":victim,"oracle_pass":False,"failure_class":"RESOURCE_LIMIT"}
        out=score_results(m,rows,threshold_rate=.1)
        self.assertEqual(out["sample_size"],20)
        self.assertEqual(out["failures"],1)
        self.assertEqual(out["case_results"][7]["case_id"],victim)

    def test_timeout_harness_and_candidate_failures_all_conservative(self):
        m=self.manifest(n=20,N=100)
        classes=["TIMEOUT","HARNESS_CASE_FAILURE","CANDIDATE_FAILURE"]
        rows=[]
        for i,cid in enumerate(m["selected_case_ids"]):
            if i < len(classes):
                rows.append({"case_id":cid,"oracle_pass":False,"failure_class":classes[i]})
            else:
                rows.append({"case_id":cid,"oracle_pass":True})
        out=score_results(m,rows,threshold_rate=.1)
        self.assertEqual(out["failures"],3)

    def test_global_scorer_invalidation_invalidates_entire_wave(self):
        m=self.manifest(n=10,N=40)
        rows=[{"case_id":x,"oracle_pass":True} for x in m["selected_case_ids"]]
        rows[0]["scorer_invalidated"]=True
        out=score_results(m,rows,threshold_rate=.1)
        self.assertEqual(out["status"],"INVALID_SCORER")
        self.assertFalse(out["pass_terminal_rate_lower_bound"])
        self.assertNotIn("finite_population_proof",out)

    def test_all_success_sample_can_clear_seventy_percent_population_bar(self):
        m=self.manifest(n=20,N=100)
        rows=[{"case_id":x,"oracle_pass":True} for x in m["selected_case_ids"]]
        out=score_results(m,rows,threshold_rate=.70,alpha=.05)
        self.assertTrue(out["pass_terminal_rate_lower_bound"],out)

    def test_manifest_binds_candidate_harness_scorer_and_no_replacement(self):
        m=self.manifest()
        self.assertEqual(m["candidate_commit"],"cand")
        self.assertEqual(m["harness_commit"],"har")
        self.assertEqual(m["scorer_commit"],"score")
        self.assertFalse(m["replacement_allowed"])
        self.assertEqual(m["job_policy"],"ONE_SELECTED_CASE_PER_FRESH_JOB")


if __name__=="__main__":
    unittest.main()
