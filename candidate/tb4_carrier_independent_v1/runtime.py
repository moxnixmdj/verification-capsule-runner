"""Fail-closed conservative acceptance bound compiler."""
from __future__ import annotations
from decimal import Decimal, ROUND_CEILING
from typing import Any, Mapping
SCHEMA="PROJECT_BRAIN_ACCEPTANCE_BOUND_COMPILER_V1"
def _fail(*errors:str)->dict[str,Any]:
    return {"schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,"errors":sorted(set(errors)),"metric_type":None,"decision":"UNRESOLVED","proof_route_ready":False,"execution_authority":False,"capability_credit_delta":0,"family_credit_delta":0}
def _int(v): return None if isinstance(v,bool) or not isinstance(v,int) else v
def _dec(v):
    if isinstance(v,bool) or not isinstance(v,(int,float,str,Decimal)): return None
    try: d=Decimal(str(v))
    except Exception: return None
    return d if d.is_finite() else None
def evaluate(spec:Mapping[str,Any])->dict[str,Any]:
    if spec.get("metric_semantics_frozen") is not True: return _fail("METRIC_SEMANTICS_NOT_FROZEN")
    if spec.get("population_frozen") is not True: return _fail("POPULATION_NOT_FROZEN")
    if spec.get("worst_case_assignment_admissible") is not True: return _fail("WORST_CASE_ASSIGNMENT_NOT_PROVEN_ADMISSIBLE")
    if spec.get("metric_type")!="BINARY_RATE": return _fail("UNSUPPORTED_METRIC_TYPE")
    total=_int(spec.get("total_slots")); executable=_int(spec.get("executable_slots")); successes=_int(spec.get("observed_successes",0)); failures=_int(spec.get("observed_failures",0)); threshold=_dec(spec.get("threshold_percent"))
    if total is None or total<=0 or executable is None or executable<0 or successes is None or successes<0 or failures is None or failures<0 or threshold is None: return _fail("INVALID_INPUT")
    if executable>total or successes+failures>executable: return _fail("COUNT_INVARIANT_FAIL")
    required=int(((threshold*Decimal(total))/Decimal(100)).to_integral_value(rounding=ROUND_CEILING))
    remaining=executable-successes-failures; best=successes+remaining
    decision="PASS_LOCKED" if successes>=required else ("FAIL_LOCKED" if best<required else "UNRESOLVED")
    return {"schema":SCHEMA,"status":"PASS","pass":True,"errors":[],"metric_type":"BINARY_RATE","decision":decision,"proof_route_ready":executable>=required,"execution_authority":False,"total_slots":total,"executable_slots":executable,"unavailable_slots":total-executable,"observed_successes":successes,"observed_failures":failures,"remaining_executable_slots":remaining,"threshold_percent":str(threshold),"required_successes":required,"conservative_lower_bound_percent":str((Decimal(successes)*100)/Decimal(total)),"optimistic_upper_bound_percent":str((Decimal(best)*100)/Decimal(total)),"capability_credit_delta":0,"family_credit_delta":0}
