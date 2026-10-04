from __future__ import annotations
import hashlib, json, os, urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parent
RECEIPT=ROOT/'subject'/'livebench_zero_spend_carrier_20261004_sol'/'RECEIPT.json'
WORKFLOW=ROOT/'.github'/'workflows'/'verify-livebench-zero-spend-carrier-20261004-sol.yml'

def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()

r=json.loads(RECEIPT.read_text(encoding='utf-8'))
assert r['target_predicate']=='LIVEBENCH_IF_GE_65_7'
assert r['target_field']=='zero_incremental_spend_or_entitlement_verified'

event=json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text(encoding='utf-8'))
repo=event.get('repository') or {}
assert repo.get('full_name')=='moxnixmdj/verification-capsule-runner',repo
assert repo.get('private') is False,repo
visibility=repo.get('visibility')
if visibility is not None:
    assert visibility=='public',repo

assert os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted',os.environ.get('RUNNER_ENVIRONMENT')
wf=WORKFLOW.read_text(encoding='utf-8')
assert 'runs-on: ubuntu-latest' in wf

docs=r['github_docs']
base='https://raw.githubusercontent.com/'+docs['repository']+'/'+docs['commit']+'/'
def fetch(path: str) -> bytes:
    req=urllib.request.Request(base+path,headers={'User-Agent':'project-brain-zero-spend-verifier'})
    with urllib.request.urlopen(req,timeout=20) as resp:
        return resp.read()

billing=fetch(docs['billing_path'])
runner=fetch(docs['runner_path'])
assert git_blob_sha(billing)==docs['billing_git_blob_sha'],git_blob_sha(billing)
assert git_blob_sha(runner)==docs['runner_git_blob_sha'],git_blob_sha(runner)

bt=billing.decode('utf-8')
rt=runner.decode('utf-8')
assert 'usage is **free**' in bt
assert '**public repositories**' in bt
assert 'standard' in bt and 'hosted runners' in bt
assert 'free and unlimited on public repositories' in rt
assert 'ubuntu-latest' in rt

for k,v in r['accounting'].items():
    assert v==0,(k,v)
for claim in (
    'NO_LIVEBENCH_CASE_EXECUTION',
    'NO_LIVEBENCH_SCORE',
    'NO_PRIVATE_BRAIN_BYTES_PUBLISHED',
    'NO_FRESH_REALITY_AUTHORITY',
    'NO_EXECUTION_OR_PROMOTION_AUTHORITY',
    'NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT',
):
    assert claim in r['hard_nonclaims']

out={
  'status':'PASS',
  'repository':'moxnixmdj/verification-capsule-runner',
  'repository_visibility':'public',
  'runner_environment':'github-hosted',
  'runner_label':'ubuntu-latest',
  'github_docs_commit':docs['commit'],
  'billing_git_blob_sha':docs['billing_git_blob_sha'],
  'runner_git_blob_sha':docs['runner_git_blob_sha'],
  'zero_incremental_spend_or_entitlement_verified':True,
  'livebench_cases_executed':0,
  'fresh_reality_authority':False,
  'execution_authority':False,
  'promotion_authority':False,
  'acceptance_credit_delta':0
}
print(json.dumps(out,sort_keys=True))
