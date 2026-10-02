import itertools
import unittest

from contract_native_proof_suites import CONTRACTS, generate_case, public_task, score_case


def independent_candidate(case):
    c=case["contract"]
    if c=="STRUCTURED_METHOD_COMPLETE_CALCULATION_GRAPH_001":
        return {"graph":[
            {"factor":x["id"],"coefficient":x["coefficient"]}
            for x in case["task"]["requirements"] if x["required"]
        ]}
    if c=="TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001":
        first=next(x["step"] for x in case["task"]["trajectory"] if not x["invariant_pass"])
        return {"cause_step":first,"repair_id":f"repair_{first}","evidence_steps":[first]}
    if c=="EVIDENCE_TO_AUDIENCE_SYNTHESIS_001":
        ev=case["task"]["evidence"]
        required=sorted(x["claim_id"] for x in ev if x["role"]=="required")
        optional=sorted(x["claim_id"] for x in ev if x["role"]=="optional")
        selected=required+optional
        uncertainty=sorted(x["claim_id"] for x in ev if x["support"]=="conflicted" and x["claim_id"] in selected)
        return {"selected_claims":selected,"uncertainty_claims":uncertainty}
    if c=="PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001":
        task=case["task"]; acts=task["edit_candidates"]; weights=task["rubric_weights"]; budget=task["edit_budget"]
        best=None
        for mask in range(1<<len(acts)):
            chosen=[acts[i] for i in range(len(acts)) if mask&(1<<i)]
            if any((not a["supported"]) or a["hard_violation"] for a in chosen): continue
            cost=sum(a["cost"] for a in chosen)
            if cost>budget: continue
            score=sum(sum(weights[d]*a["scores"][d] for d in weights) for a in chosen)
            ids=tuple(sorted(a["id"] for a in chosen))
            key=(-score,cost,ids)
            if best is None or key<best[0]: best=(key,ids)
        return {"selected_edits":list(best[1])}
    raise AssertionError(c)


class IndependentContractNativeSuiteTests(unittest.TestCase):
    def test_independent_reference_passes_500_seed_contract_pairs(self):
        for contract in sorted(CONTRACTS):
            for seed in range(125):
                case=generate_case(contract,10000+seed,1+(seed%5))
                self.assertNotIn("_oracle",public_task(case))
                result=score_case(case,independent_candidate(case))
                self.assertTrue(result["pass"],(contract,seed,result))

    def test_hidden_oracle_never_leaks_to_public_task(self):
        for contract in CONTRACTS:
            for seed in range(20):
                pub=public_task(generate_case(contract,seed,3))
                raw=repr(pub)
                self.assertNotIn("_oracle",raw)
                if contract=="TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001":
                    self.assertNotIn('"cause_step"',raw)

    def test_mutants_are_killed_across_all_contracts(self):
        # Structured method: delete one required factor.
        case=generate_case("STRUCTURED_METHOD_COMPLETE_CALCULATION_GRAPH_001",7001,5)
        cand=independent_candidate(case); cand["graph"]=cand["graph"][1:]
        self.assertFalse(score_case(case,cand)["pass"])

        # Trajectory: choose first downstream symptom rather than causal violation.
        case=generate_case("TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001",7002,5)
        cause=next(x["step"] for x in case["task"]["trajectory"] if not x["invariant_pass"])
        bad={"cause_step":cause+1,"repair_id":f"repair_{cause+1}","evidence_steps":[cause+1]}
        self.assertFalse(score_case(case,bad)["pass"])

        # Synthesis: inject unsupported claim.
        seed=7003
        while True:
            case=generate_case("EVIDENCE_TO_AUDIENCE_SYNTHESIS_001",seed,5)
            forbidden=[x["claim_id"] for x in case["task"]["evidence"] if x["role"]=="forbidden"]
            if forbidden: break
            seed+=1
        cand=independent_candidate(case); cand["selected_claims"].append(forbidden[0])
        self.assertFalse(score_case(case,cand)["pass"])

        # Professional planning: violate exact optimum.
        case=generate_case("PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001",7004,5)
        cand=independent_candidate(case)
        all_ids=[x["id"] for x in case["task"]["edit_candidates"]]
        replacement=[] if cand["selected_edits"] else [all_ids[0]]
        self.assertFalse(score_case(case,{"selected_edits":replacement})["pass"])

    def test_seed_and_difficulty_are_reproducible(self):
        for contract in CONTRACTS:
            for d in range(1,6):
                self.assertEqual(generate_case(contract,424242,d),generate_case(contract,424242,d))


if __name__=="__main__":
    unittest.main()
