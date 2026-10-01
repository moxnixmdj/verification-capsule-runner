"""Deterministic SA-CCR credit effective-notional and add-on slice.

Scope: supervisory duration, maturity factor, credit subcategory mapping,
effective notional, and entity-level supervisory correlation aggregation.
No whole-SA-CCR, collateral, IR/FX/EQ/CO, risk-weight, or regulatory-interpretation claim.
"""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Iterable

BUSINESS_DAYS_YEAR=250.0

@dataclass(frozen=True)
class CreditComponent:
    effective_notional: float
    supervisory_factor: float
    rho: float

def supervisory_duration(S: float, E: float) -> float:
    S=float(S); E=float(E)
    if not (math.isfinite(S) and math.isfinite(E)) or S < 0 or E < S:
        raise ValueError("require finite 0 <= S <= E")
    return (math.exp(-0.05*S)-math.exp(-0.05*E))/0.05

def maturity_factor_margined(mpor_days: float) -> float:
    d=float(mpor_days)
    if not math.isfinite(d) or d <= 0:
        raise ValueError("MPOR days must be positive finite")
    return 1.5*math.sqrt(d/BUSINESS_DAYS_YEAR)

def maturity_factor_unmargined(M_years: float) -> float:
    M=float(M_years)
    if not math.isfinite(M) or M < 0:
        raise ValueError("maturity must be non-negative finite")
    return math.sqrt(min(max(M,10.0/BUSINESS_DAYS_YEAR),1.0))

def credit_subcategory(instrument_type: str, index_name: str="", reference_entity: str="") -> str:
    name=(index_name or reference_entity or "").upper()
    is_index=(instrument_type=="CDSIndex" or "CDX" in name or "ITRAXX" in name)
    if is_index:
        return "Index_IG" if "IG" in name else "Index_HY"
    return "SingleName_HY" if "HY" in name else "SingleName_IG"

def credit_effective_notional(
    notional_usd: float,
    S: float,
    E: float,
    *,
    direction: str,
    is_margined: bool,
    mpor_days: float=10.0,
) -> float:
    n=float(notional_usd)
    if not math.isfinite(n) or n < 0:
        raise ValueError("notional must be non-negative finite")
    sd=supervisory_duration(S,E)
    mf=maturity_factor_margined(mpor_days) if is_margined else maturity_factor_unmargined(E)
    if direction=="SoldProtection":
        delta=1.0
    elif direction=="BoughtProtection":
        delta=-1.0
    else:
        raise ValueError("credit direction must be SoldProtection or BoughtProtection")
    return n*sd*delta*mf

def aggregate_credit_addon(components: Iterable[CreditComponent]) -> float:
    items=list(components)
    if not items:
        return 0.0
    sum_rho_a=0.0
    sum_resid=0.0
    for c in items:
        en=float(c.effective_notional); sf=float(c.supervisory_factor); rho=float(c.rho)
        if not all(math.isfinite(x) for x in (en,sf,rho)) or sf < 0 or not 0 <= rho <= 1:
            raise ValueError("invalid component")
        a=sf*en
        sum_rho_a += rho*a
        sum_resid += (1-rho*rho)*a*a
    return math.sqrt(sum_rho_a*sum_rho_a+sum_resid)
