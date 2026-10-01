import unittest
import numpy as np
from sklearn.preprocessing import RobustScaler
from verification.robust_anomaly_candidate_ranker import RobustCandidateRanker

class DifferentialTests(unittest.TestCase):
    def test_matches_sklearn_baro_core(self):
        for seed in range(1000):
            rng=np.random.default_rng(seed)
            n=int(rng.integers(16,300))
            m=int(rng.integers(3,60))
            names=[f"v{i}" for i in range(m)]
            normal={}
            abnormal={}
            expected={}
            for name in names:
                a=rng.normal(loc=rng.normal(),scale=rng.uniform(.05,20),size=n)
                b=rng.normal(loc=rng.normal(),scale=rng.uniform(.05,20),size=int(rng.integers(4,80)))
                # Exercise duplicates and near-flat variables without true constants.
                if seed%17==0:
                    a=np.round(a,2)
                normal[name]=a
                abnormal[name]=b
                sc=RobustScaler().fit(a.reshape(-1,1))
                z=sc.transform(b.reshape(-1,1))[:,0]
                expected[name]=float(max(z))
            r=RobustCandidateRanker(names).fit(normal)
            got=r.score(abnormal)
            for name in names:
                self.assertAlmostEqual(got[name],expected[name],places=11,msg=f"seed={seed} {name}")
            got_order=[x for x,_ in r.rank(abnormal)]
            exp_order=sorted(names,key=lambda name:(-expected[name],names.index(name)))
            self.assertEqual(got_order,exp_order,f"order seed={seed}")

    def test_constant_reference_matches_sklearn_zero_scale_behavior(self):
        normal={"x":np.ones(30)*5.0}
        abnormal={"x":np.array([4.,5.,7.])}
        r=RobustCandidateRanker(["x"]).fit(normal)
        sc=RobustScaler().fit(normal["x"].reshape(-1,1))
        expected=float(max(sc.transform(abnormal["x"].reshape(-1,1))[:,0]))
        self.assertAlmostEqual(r.score(abnormal)["x"],expected,places=12)

    def test_top_k_is_prefix_only(self):
        n={"a":np.arange(20.),"b":np.arange(20.),"c":np.arange(20.)}
        a={"a":np.array([100.]),"b":np.array([50.]),"c":np.array([25.])}
        r=RobustCandidateRanker(["a","b","c"]).fit(n)
        self.assertEqual(r.candidates(a,2),["a","b"])

if __name__=="__main__":
    unittest.main()
