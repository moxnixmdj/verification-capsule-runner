import unittest, numpy as np
from pc_skeleton_minimal import pc_stable_skeleton, fisher_z_pvalue
from causallearn.utils.PCUtils import SkeletonDiscovery
from causallearn.utils.cit import CIT

def donor_skeleton(data,alpha=.05):
    cg=SkeletonDiscovery.skeleton_discovery(
        data,alpha,CIT(data,"fisherz"),stable=True,show_progress=False
    )
    g=np.asarray(cg.G.graph)
    a=(g!=0).astype(np.int8)
    np.fill_diagonal(a,0)
    return a

def make_dag_case(rng,p,n=700):
    order=list(range(p))
    B=np.zeros((p,p))
    for child in range(1,p):
        for parent in range(child):
            if rng.random()<0.32:
                mag=rng.uniform(.35,1.15)
                B[parent,child]=mag if rng.random()<.5 else -mag
    X=np.zeros((n,p))
    noise=rng.normal(0,1,size=(n,p))
    for j in order:
        X[:,j]=noise[:,j]+sum(B[i,j]*X[:,i] for i in range(j))
    return X

class TestPCSkeleton(unittest.TestCase):
    def test_fisher_z_unconditional_independence(self):
        rng=np.random.default_rng(1)
        x=rng.normal(size=3000); y=rng.normal(size=3000)
        data=np.column_stack([x,y]); corr=np.corrcoef(data.T)
        self.assertGreater(fisher_z_pvalue(corr,len(data),0,1,()),.01)

    def test_chain_conditional_separation(self):
        rng=np.random.default_rng(2); n=4000
        a=rng.normal(size=n); b=.9*a+rng.normal(size=n); c=.8*b+rng.normal(size=n)
        data=np.column_stack([a,b,c]); corr=np.corrcoef(data.T)
        self.assertLess(fisher_z_pvalue(corr,n,0,2,()),1e-8)
        self.assertGreater(fisher_z_pvalue(corr,n,0,2,(1,)),.01)

    def test_fresh_randomized_differential(self):
        rng=np.random.default_rng(20261001)
        mismatches=[]
        cases=0
        for p in range(4,9):
            for _ in range(12):
                data=make_dag_case(rng,p)
                got=pc_stable_skeleton(data,.05)
                ref=donor_skeleton(data,.05)
                cases+=1
                if not np.array_equal(got,ref):
                    mismatches.append((p,np.argwhere(got!=ref).tolist()))
        self.assertEqual(mismatches,[],f"{len(mismatches)}/{cases} donor mismatches")

    def test_fail_closed_bad_data(self):
        with self.assertRaises(ValueError): pc_stable_skeleton(np.array([[1.,np.nan],[2.,3.],[4.,5.],[6.,7.]]))
        with self.assertRaises(ValueError): pc_stable_skeleton(np.ones((10,2)))

if __name__=="__main__":
    unittest.main(verbosity=2)
