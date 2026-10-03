#!/usr/bin/env python3
from __future__ import annotations
import hashlib
import importlib.util
import json
import pathlib
import urllib.parse

ROOT=pathlib.Path(__file__).resolve().parent
PROVIDER=ROOT/"subjects/github_public_retrieval_provider_v1.py"
ROUTER=ROOT/"subjects/residual_witness_backend_router_v1.py.txt"
EXPECTED_PROVIDER="29b808935559382ab7ddc81aaa08fe0611a05df8"
EXPECTED_ROUTER="578c5f87901a458b12d7df984e0a6a525d367456"

def blob_sha(path):
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

assert blob_sha(PROVIDER)==EXPECTED_PROVIDER,(blob_sha(PROVIDER),EXPECTED_PROVIDER)
assert blob_sha(ROUTER)==EXPECTED_ROUTER,(blob_sha(ROUTER),EXPECTED_ROUTER)

spec=importlib.util.spec_from_file_location("subject_provider",PROVIDER)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class Resp:
    def __init__(self,payload):
        self.raw=json.dumps(payload,ensure_ascii=False).encode()
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def read(self,*args): return self.raw

class Opener:
    def __init__(self): self.urls=[]
    def __call__(self,req,timeout=0):
        self.urls.append(req.full_url)
        path=urllib.parse.urlsplit(req.full_url).path
        if path=="/search/repositories":
            return Resp({"items":[{"full_name":"例子/仓库","html_url":"https://github.com/e/r","description":None,"language":"Python","default_branch":"main","archived":False,"fork":False}]})
        if path=="/search/code":
            return Resp({"items":[{"name":"codec.py","path":"src/codec.py","sha":"a"*40,"html_url":"https://github.com/e/r/blob/main/src/codec.py","repository":{"full_name":"e/r"}}]})
        if path=="/search/issues":
            return Resp({"items":[{"html_url":"https://github.com/e/r/issues/1","repository_url":"https://api.github.com/repos/e/r","title":"编解码器","state":"open"}]})
        if path=="/search/commits":
            return Resp({"items":[{"sha":"b"*40,"html_url":"https://github.com/e/r/commit/"+"b"*40,"repository":{"full_name":"e/r"},"commit":{"message":"修复 UBJSON 编码"}}]})
        raise AssertionError(req.full_url)

def action(surface,q="中文 UBJSON 编解码器"):
    return {"action":"QUERY","query_id":"Q000","query":q,"surface":surface}

# Unicode transport + code-content independence from metadata/popularity.
o=Opener()
out=m.search(action("CODE_CONTENT"),opener=o)
assert out["candidate_count"]==1,out
assert "中文 UBJSON 编解码器" in urllib.parse.unquote(o.urls[0]),o.urls
assert out["complete"] is False and out["independently_complete"] is False,out
c=out["candidates"][0]
assert c["repository"]=="e/r" and c["path"]=="src/codec.py",c
assert "stars" not in c and "description" not in c,c

# Descriptionless repo survives candidate discovery.
o=Opener()
repo=m.search(action("REPOSITORY_METADATA"),opener=o)
assert repo["candidate_count"]==1,repo
assert repo["candidates"][0]["description"] is None,repo

# Manifest/test searches really hit code search with structural qualifiers.
for surface,needle in (("MANIFESTS","filename:"),("TESTS_EXAMPLES","path:")):
    o=Opener()
    got=m.search(action(surface,"ubjson"),limit=2,opener=o)
    assert got["candidate_count"]>=1,got
    decoded="\n".join(urllib.parse.unquote(x) for x in o.urls)
    assert needle in decoded,(surface,decoded)

# Issues/history are candidate discovery; history explicitly remains partial.
o=Opener()
issue=m.search(action("ISSUES_PRS"),opener=o)
history=m.search(action("COMMITS_RELEASES_BRANCHES_TAGS"),opener=o)
assert issue["candidates"][0]["repository"]=="e/r",issue
assert "COMMIT_SEARCH_ONLY" in history["coverage_detail"],history
assert history["complete"] is False,history

# Router exact bytes bind the seven surfaces to the one provider.
router_text=ROUTER.read_text()
for surface in (
    "REPOSITORY_METADATA","CODE_CONTENT","SYMBOLS","MANIFESTS",
    "TESTS_EXAMPLES","ISSUES_PRS","COMMITS_RELEASES_BRANCHES_TAGS",
):
    assert f'"{surface}"' in router_text,surface
assert "github_public_retrieval_provider_v1.search(action,limit=20)" in router_text
assert '"SOCIAL_TECHNICAL_DISCUSSION"' not in router_text.split("def default_providers",1)[1].split("def _candidate_id",1)[0]

# Authority boundary remains hard: subject never emits verified sufficiency.
for surface in m.SUPPORTED_SURFACES:
    o=Opener()
    got=m.search(action(surface,"ubjson"),limit=1,opener=o)
    assert got.get("acceptance_credit")==0,got
    assert got.get("sufficiency_status")=="UNVERIFIED",got
    assert got.get("complete") is False,got
    assert "verified_sufficient" not in got,got

print("GITHUB_RESIDUAL_RETRIEVAL_SURFACES_V1_VERIFIED")
print(json.dumps({
    "provider_blob":EXPECTED_PROVIDER,
    "router_blob":EXPECTED_ROUTER,
    "supported_surface_count":len(m.SUPPORTED_SURFACES),
    "unicode_transport":True,
    "descriptionless_repository_retained":True,
    "content_search_metadata_independent":True,
    "candidate_only_authority":True,
    "history_scope_partial_and_explicit":True,
},sort_keys=True))
