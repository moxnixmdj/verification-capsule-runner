import unittest, math
import numpy as np

from verification.saccr_credit_kernel import (
    CreditTrade, supervisory_duration, adjusted_notional, maturity_factor,
    effective_notional, supervisory_factor, supervisory_correlation,
    trace_trade, credit_addon
)
from verification.baselkit_sa_ccr_pinned import (
    SACCRTrade, AssetClass,
    supervisory_duration as d_sd,
    adjusted_notional as d_adj,
    maturity_factor as d_mf,
    _effective_notional as d_eff,
    _supervisory_factor as d_sf,
    _addon_systematic as d_addon,
    _RHO_CREDIT_SINGLE, _RHO_CREDIT_INDEX
)

def donor_trade(t):
    return SACCRTrade(
        asset_class=AssetClass.CREDIT,
        notional=t.notional,start=t.start,end=t.end,direction=t.direction,
        hedging_set=t.reference,reference=t.reference,credit_rating=t.credit_rating,
        is_index=t.is_index,margined_mpor=t.margined_mpor
    )

class SACCRCreditKernelTests(unittest.TestCase):
    def test_random_trade_intermediates_match_pinned_donor(self):
        ratings_single=["AAA","AA","A","BBB","BB","B","CCC"]
        ratings_index=["IG","SG"]
        for seed in range(2000):
            rng=np.random.default_rng(seed)
            is_index=bool(seed%4==0)
            start=float(rng.uniform(0,8))
            end=float(start+rng.uniform(0.001,15))
            t=CreditTrade(
                notional=float(rng.uniform(1e3,1e8)),start=start,end=end,
                direction=-1 if seed%3==0 else 1,
                reference=f"R{seed%7}",
                credit_rating=(ratings_index[seed%len(ratings_index)] if is_index else ratings_single[seed%len(ratings_single)]),
                is_index=is_index,
                margined_mpor=(None if seed%5 else float(rng.uniform(.001,.5)))
            )
            d=donor_trade(t)
            self.assertAlmostEqual(supervisory_duration(t.start,t.end),d_sd(d.start,d.end),places=12)
            self.assertAlmostEqual(adjusted_notional(t),d_adj(d),places=8)
            self.assertAlmostEqual(maturity_factor(t),d_mf(d),places=12)
            self.assertAlmostEqual(effective_notional(t),d_eff(d),places=8)
            self.assertAlmostEqual(supervisory_factor(t),d_sf(d),places=12)
            tr=trace_trade(t)
            self.assertAlmostEqual(tr["adjusted_notional"],tr["trade"]["notional"]*tr["supervisory_duration"],places=8)
            self.assertAlmostEqual(tr["effective_notional"],tr["adjusted_notional"]*tr["delta"]*tr["maturity_factor"],places=8)

    def test_random_portfolios_match_pinned_credit_aggregation(self):
        rs=["AAA","AA","A","BBB","BB","B","CCC"]
        for seed in range(400):
            rng=np.random.default_rng(seed+9000)
            trades=[]; donors=[]
            for i in range(int(rng.integers(1,20))):
                t=CreditTrade(
                    notional=float(rng.uniform(1e4,5e7)),start=0.0,end=float(rng.uniform(.05,12)),
                    direction=1 if rng.random()>.4 else -1,
                    reference=f"E{int(rng.integers(0,6))}",
                    credit_rating=rs[int(rng.integers(0,len(rs)))],
                    is_index=False
                )
                trades.append(t); donors.append(donor_trade(t))
            self.assertAlmostEqual(credit_addon(trades),d_addon(donors,_RHO_CREDIT_SINGLE,_RHO_CREDIT_INDEX),places=7)

    def test_regulatory_supervisory_duration_examples(self):
        # Published examples: S=0, E=3 -> about 2.79; E=6 -> about 5.18; E=5 -> about 4.42.
        self.assertAlmostEqual(supervisory_duration(0,3),2.785840,places=5)
        self.assertAlmostEqual(supervisory_duration(0,6),5.183636,places=5)
        self.assertAlmostEqual(supervisory_duration(0,5),4.423984,places=5)

    def test_rank13_missing_factor_identity_is_impossible(self):
        # 25m IG credit trade with S=0,E=5 must carry SD into adjusted/effective notional.
        t=CreditTrade(25_000_000,0,5,1,"CP_B","IG",True)
        tr=trace_trade(t)
        self.assertGreater(tr["supervisory_duration"],4.0)
        self.assertAlmostEqual(tr["adjusted_notional"],25_000_000*tr["supervisory_duration"],places=5)
        self.assertNotAlmostEqual(tr["adjusted_notional"],25_000_000,places=2)
        self.assertAlmostEqual(tr["directional_addon"],tr["effective_notional"]*0.0038,places=5)

if __name__=="__main__":
    unittest.main()
