import unittest
import numpy as np
from scipy import stats

from verification.pc_stable_cpdag_singular_safe import fisher_z_pvalue, pc_stable_cpdag

def donor_p(data,x,y,cond=()):
    cols=[x,y,*cond]
    sub=np.asarray(data[:,cols],dtype=float)
    n=sub.shape[0]; k=len(cond)
    if n-k-3<=0:
        return 1.0
    if np.any(np.nanstd(sub,axis=0)==0):
        return 1.0
    cov=np.cov(sub,rowvar=False)
    try:
        precision=np.linalg.pinv(cov)
    except np.linalg.LinAlgError:
        return 1.0
    denom=np.sqrt(precision[0,0]*precision[1,1])
    if denom==0 or not np.isfinite(denom):
        return 1.0
    rho=-precision[0,1]/denom
    rho=np.clip(rho,-0.999999,0.999999)
    z=.5*np.log((1+rho)/(1-rho))*np.sqrt(n-k-3)
    return float(2*(1-stats.norm.cdf(abs(z))))

class SingularSafeTests(unittest.TestCase):
    def test_nonsingular_matches_donor(self):
        for seed in range(1000):
            rng=np.random.default_rng(seed)
            n=int(rng.integers(30,300)); p=int(rng.integers(3,9))
            x=rng.normal(size=(n,p))
            for j in range(1,p):
                x[:,j]+=rng.uniform(-.8,.8)*x[:,int(rng.integers(0,j))]
            corr=np.corrcoef(x.T)
            a,b=0,1
            pool=list(range(2,p))
            k=min(len(pool),seed%3)
            cond=tuple(pool[:k])
            got=fisher_z_pvalue(corr,n,a,b,cond)
            exp=donor_p(x,a,b,cond)
            self.assertAlmostEqual(got,exp,places=10,msg=f"seed={seed}")

    def test_exact_collinearity_no_crash(self):
        rng=np.random.default_rng(42)
        a=rng.normal(size=200)
        x=np.column_stack([a,2*a,a+rng.normal(scale=.1,size=200),rng.normal(size=200)])
        cpdag,sk,seps=pc_stable_cpdag(x,alpha=.05,max_k=1)
        self.assertEqual(cpdag.shape,(4,4))
        self.assertTrue(np.isfinite(cpdag).all())

    def test_near_singular_no_crash(self):
        rng=np.random.default_rng(7)
        a=rng.normal(size=160)
        x=np.column_stack([a,a+1e-14*rng.normal(size=160),rng.normal(size=160),rng.normal(size=160)])
        cpdag,sk,seps=pc_stable_cpdag(x,alpha=.05,max_k=1)
        self.assertEqual(cpdag.shape,(4,4))

    def test_thin_conditioning_fails_closed_independent(self):
        corr=np.eye(4)
        self.assertEqual(fisher_z_pvalue(corr,4,0,1,(2,)),1.0)

if __name__=="__main__":
    unittest.main()
