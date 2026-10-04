#!/usr/bin/env python3
import hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parent
def blob(p):
 b=p.read_bytes(); return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
m=json.loads((R/'EXPECTED.json').read_text())
for rel,exp in m['exact_blobs'].items(): assert blob(R/rel)==exp
inv=json.loads((R/'canonical/governance/ROOT2_FIXED_BAR_ROUTE_INVENTORY_V1.json').read_text())
cut=json.loads((R/'canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V9.json').read_text())
assert cut['exact_state']['root2_only_count']==15
assert cut['exact_state']['root2_unique_benchmark_surfaces']==14
assert cut['new_reality_units_consumed']==0 and cut['terminal_cases_consumed']==0
assert cut['incremental_spend_usd']==0 and cut['acceptance_credit_delta']==0
assert cut['execution_authority'] is False and cut['promotion_authority'] is False and cut['fresh_reality_authority'] is False
active=' '.join(x['work'] for x in cut['active_zero_reality_work'])
assert 'GITLAB_EXACT_REVISION' not in active
assert 'BIND_HARD_ZERO_SPEND_GUARD' not in active
assert 'LIVEBENCH_IF_GE_65_7__ROUTE_COMPLETE_TO_BRAIN_SCORE_ONLY' in cut['preserved_for_minimum_reality_execution']
assert 'TB_SCIENCE_GE_58_7__ROUTE_COMPLETE_TO_BRAIN_SCORE_ONLY' in cut['preserved_for_minimum_reality_execution']
events={x['event_class'] for x in cut['external_event_dependencies']}
assert 'CHARTOGRAPHY_PROJECT_ACCOUNT_CAPACITY' in events
assert 'HUGGINGFACE_GATED_ACCOUNT_ACCESS' in events
chart=next(x for x in inv['routes'] if x['surface']=='Chartography with tools')
assert len(chart['zero_spend_guard']['remaining'])==3
osw=next(x for x in inv['routes'] if x['surface']=='OSWorld 2.1 partial')
assert osw['gitlab_protocol_reconciliation']['replacement']=='GITLAB_FUNCTIONAL_PROTOCOL_PREFLIGHT'
print(json.dumps({'pass':True,'schema':'PROJECT_BRAIN_ROOT2_MINIMUM_CUT_V9_PUBLIC_RUNNER_RESULT_V1','status':'PASS__EXACT_BLOBS__STALE_BLOCKERS_DELETED__EVENTS_SEPARATED__ZERO_CREDIT'},sort_keys=True))
