import itertools
import unittest

from finite_population_proof import exact_lower_success_count, evaluate_binary_population
from proof_route_dominance import evaluate as dominance


def brute_tail(N, K, n, x):
    pop = [1] * K + [0] * (N - K)
    total = good = 0
    for idxs in itertools.combinations(range(N), n):
        total += 1
        if sum(pop[i] for i in idxs) >= x:
            good += 1
    return good / total


def brute_lower(N, n, x, alpha):
    for K in range(x, N + 1):
        if brute_tail(N, K, n, x) >= alpha:
            return K
    return N


class FinitePopulationIndependentTests(unittest.TestCase):
    def test_exhaustive_small_against_enumeration(self):
        for N in range(1, 9):
            for n in range(N + 1):
                for x in range(n + 1):
                    for alpha in (0.05, 0.10, 0.25):
                        got = exact_lower_success_count(N, n, x, alpha)
                        want = brute_lower(N, n, x, alpha)
                        self.assertEqual((N,n,x,alpha,got),(N,n,x,alpha,want))

    def test_full_census_exact(self):
        for N in range(1, 30):
            for x in range(N + 1):
                self.assertEqual(exact_lower_success_count(N,N,x,0.05), x)

    def test_population_bar_requires_lower_bound_not_sample_rate(self):
        out = evaluate_binary_population(
            population_size=100, sample_size=5, sample_successes=5,
            threshold_rate=0.95, alpha=0.05
        )
        self.assertEqual(out["status"], "INSUFFICIENT_EVIDENCE")
        self.assertFalse(out["pass_lower_bound"])


class ProofRouteDominanceIndependentTests(unittest.TestCase):
    def route(self, rid, covers, strength, **kw):
        base = dict(
            id=rid, covers=covers, oracle_strength=strength,
            zero_cost=True, executable=True, independent_oracle=True,
            scope_mapping_frozen=True, contamination_boundary_frozen=True,
        )
        base.update(kw)
        return base

    def test_union_of_admissible_routes_can_replace_blocked_route(self):
        out = dominance({
            "obligations":[
                {"id":"semantics","min_oracle_strength":2},
                {"id":"artifact","min_oracle_strength":3},
            ],
            "routes":[
                self.route("private",["semantics","artifact"],9,blocked=True),
                self.route("public_semantics",["semantics"],2),
                self.route("absolute_artifact",["artifact"],3),
            ],
        })
        verdict = out["blocked_route_verdicts"][0]
        self.assertTrue(verdict["redundant"])
        self.assertEqual(out["global_uncovered_obligations"],[])

    def test_every_admission_flag_is_fail_closed(self):
        flags = [
            "zero_cost","executable","independent_oracle",
            "scope_mapping_frozen","contamination_boundary_frozen"
        ]
        for missing in flags:
            candidate=self.route("candidate",["A"],5)
            candidate[missing]=False
            out=dominance({
                "obligations":[{"id":"A","min_oracle_strength":1}],
                "routes":[
                    self.route("private",["A"],9,blocked=True),
                    candidate,
                ],
            })
            self.assertFalse(out["blocked_route_verdicts"][0]["redundant"], missing)

    def test_strength_is_obligation_floor_not_private_brand_score(self):
        out=dominance({
            "obligations":[{"id":"A","min_oracle_strength":2}],
            "routes":[
                self.route("private",["A"],99,blocked=True),
                self.route("public_absolute",["A"],2),
            ],
        })
        self.assertTrue(out["blocked_route_verdicts"][0]["redundant"])


if __name__ == "__main__":
    unittest.main()
