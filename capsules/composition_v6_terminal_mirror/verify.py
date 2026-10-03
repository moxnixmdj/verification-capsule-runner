import json,hashlib
from pathlib import Path
R=Path(__file__).parent
def J(n): return json.loads((R/n).read_text())
def H(n):
 b=(R/n).read_bytes(); return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
e=J('EXPECTED_BRAIN_BLOBS.json')['exact_brain_blobs']
assert all(H(n)==v['git_blob_sha'] for n,v in e.items())
t=J('terminal.json'); a=J('authority_v6.json'); v=J('authority_v6_verification.json')
assert t['truth']['opus55_acceptance']=='5/19_PASS__14/19_OPEN' and t['truth']['achieved'] is False
assert 'composition_component_proof_current_authority_v5' not in t['sources']
assert t['sources']['composition_component_proof_current_authority_v6']['git_blob_sha']=='5bb089582a5bc2ee4a44143c8d3a11e919fecdff'
assert t['sources']['composition_component_proof_current_authority_v6']['verification_git_blob_sha']=='28c5fe9e456cc6bd5171bb74ab291b043d7e85e4'
assert t['integrator_reconciliation_20261002_current']['composition']=='4_OF_12_CURRENTLY_ADMISSIBLE__MEMORY_RECOVERY_DELEGATION_AND_TOOL_DISCOVERY_SCOPED_PROVED__8_OPEN__PARENT_OPEN'
s=json.dumps(t)
assert 'FROZEN_COMPOSITION_COMPONENT_INTERFACES__3_OF_12_CURRENTLY_ADMISSIBLE' not in s
assert 'FROZEN_COMPOSITION_COMPONENT_INTERFACES__4_OF_12_CURRENTLY_ADMISSIBLE' in s
assert a['truth']['current_admissible_scoped_proved']==4 and a['truth']['current_open']==8
assert a['truth']['parent_composition_predicate_closed'] is False
assert v['status'].startswith('INDEPENDENT_PUBLIC_RUNNER_PASS')
print(json.dumps({'pass':True,'acceptance':'5/19','composition':'4/12','parent_open':True,'new_reality_units_consumed':0},sort_keys=True))
