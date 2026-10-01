import unittest
import numpy as np
import networkx as nx

from verification.pc_stable_cpdag_candidate import (
    pc_stable_skeleton_with_sepsets,
    cpdag_from_skeleton,
)
from verification.brain_pc_stable_skeleton_reference import pc_stable_skeleton

from causal_discovery_pc.pc import PC
from causal_discovery_pc.orient import apply_meek_rules as donor_meek


def donor_matrix(skeleton, sepsets):
    g0=nx.Graph()
    p=skeleton.shape[0]
    g0.add_nodes_from(range(p))
    for i in range(p):
        for j in range(i+1,p):
            if skeleton[i,j]:
                g0.add_edge(i,j)
    g=PC._orient_v_structures(g0,sepsets)
    donor_meek(g)
    out=np.zeros((p,p),dtype=np.int8)
    for u,v in g.edges():
        out[int(u),int(v)]=1
    return out


class CPDAGCandidateTests(unittest.TestCase):
    def test_skeleton_preserves_owned_mechanism(self):
        for seed in range(80):
            rng=np.random.default_rng(seed)
            n=240 + (seed % 5)*20
            p=5 + (seed % 3)
            x=rng.normal(size=(n,p))
            # Fresh linear-Gaussian systems with mixed direct/mediated dependence.
            for j in range(1,p):
                parent=int(rng.integers(0,j))
                x[:,j] += rng.uniform(.25,.95)*x[:,parent]
                if j>=2 and seed%2==0:
                    parent2=int(rng.integers(0,j))
                    x[:,j] += rng.uniform(.10,.45)*x[:,parent2]
            got,_=pc_stable_skeleton_with_sepsets(x,alpha=.05,max_k=2)
            expected=pc_stable_skeleton(x,alpha=.05,max_k=2)
            self.assertTrue(np.array_equal(got,expected), f"skeleton mismatch seed={seed}")

    def test_orientation_matches_pinned_donor(self):
        for seed in range(600):
            rng=np.random.default_rng(seed+10000)
            p=int(rng.integers(3,9))
            upper=rng.random((p,p)) < rng.uniform(.2,.7)
            sk=np.triu(upper,1).astype(np.int8)
            sk=sk+sk.T
            seps={}
            for x in range(p):
                for z in range(x+1,p):
                    if sk[x,z]:
                        continue
                    pool=[v for v in range(p) if v not in (x,z)]
                    k=int(rng.integers(0,min(3,len(pool))+1))
                    if k:
                        chosen=tuple(sorted(int(v) for v in rng.choice(pool,size=k,replace=False)))
                    else:
                        chosen=()
                    seps[(x,z)]=chosen
            got=cpdag_from_skeleton(sk,seps)
            expected=donor_matrix(sk,seps)
            self.assertTrue(np.array_equal(got,expected), f"orientation mismatch seed={seed}\n{got}\n{expected}")

    def test_unidentifiable_triangle_stays_undirected(self):
        sk=np.ones((3,3),dtype=np.int8)-np.eye(3,dtype=np.int8)
        got=cpdag_from_skeleton(sk,{})
        self.assertTrue(np.array_equal(got,sk))

    def test_collider_orients_only_identifiable_arrows(self):
        sk=np.array([[0,1,0],[1,0,1],[0,1,0]],dtype=np.int8)
        got=cpdag_from_skeleton(sk,{(0,2):()})
        expected=np.array([[0,1,0],[0,0,0],[0,1,0]],dtype=np.int8)
        self.assertTrue(np.array_equal(got,expected), (got,expected))


if __name__ == "__main__":
    unittest.main()
