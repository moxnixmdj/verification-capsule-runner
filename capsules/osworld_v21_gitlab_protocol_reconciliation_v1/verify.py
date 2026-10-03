#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, urllib.parse, urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parent
m=json.loads((ROOT/'EXPECTED.json').read_text())

def git_blob(raw:bytes)->str:
    return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()

def fetch(repo,ref,path):
    url=f'https://raw.githubusercontent.com/{repo}/{urllib.parse.quote(ref,safe="")}/{path}'
    with urllib.request.urlopen(url,timeout=30) as r:
        return r.read()

docs={}
for s in m['upstream_sources']:
    raw=fetch(s['repo'],s['ref'],s['path'])
    got=git_blob(raw)
    assert got==s['blob'],(s['path'],got,s['blob'])
    docs[s['path']]=raw.decode('utf-8')

manifest=json.loads(docs['benchmark_releases/osworld-v2.1.json'])
assert 'gitlab' not in manifest
for key in ('osworld_code','website_code','tasks','assets','task_hash_manifest','provider_images'):
    assert key in manifest,key

contract=docs['benchmark_releases/README.md']
for token in ('osworld_code','website_code','tasks','assets','task_hash_manifest','provider_images'):
    assert token in contract,token

skill=docs['.codex/skills/setup-osworld/SKILL.md']
assert 'These service procedures are shared' in skill
assert 'references/gitlab.md' in skill
assert 'website tag `osworld-v2.1`' in skill

gitlab=docs['.codex/skills/setup-osworld/references/gitlab.md']
assert 'reachable GitLab URL and valid private token' in gitlab
assert 'docker compose up -d' in gitlab
assert '/api/v4/user' in gitlab

guide=docs['docs/PUBLIC_EVALUATION_GUIDELINE_v2.1.md']
assert 'export GITLAB_URL="<your-gitlab-url>"' in guide
assert 'export GITLAB_PRIVATE_TOKEN="<your-private-token>"' in guide
assert 'Task-Web/gitlab@' not in guide

print(json.dumps({
  'schema':'OSWORLD_V21_GITLAB_PROTOCOL_THEOREM_PUBLIC_RUNNER_RESULT_V1',
  'pass':True,
  'status':'PASS__EXACT_UPSTREAM_BLOBS__GITLAB_NOT_RELEASE_PINNED__SHARED_SERVICE_FUNCTIONAL_CONTRACT',
  'verified':{
    'release_manifest_exact':True,
    'manifest_component_contract_exact':True,
    'gitlab_absent_from_release_components':True,
    'setup_skill_calls_gitlab_shared_service':True,
    'gitlab_success_contract_is_reachability_plus_valid_token':True,
    'public_eval_guide_requires_url_and_token_without_revision':True
  },
  'acceptance_credit_delta':0,
  'fresh_reality_authority':False
},sort_keys=True))
