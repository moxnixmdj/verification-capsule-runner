from __future__ import annotations
import hashlib, importlib.util, json, os, re, sys, types, urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SUB=ROOT/"subject"/"livebench_public_zero_spend_carrier_20261004_sol"
EXPECTED={
 "GOVERNANCE.json":"093ec45bd3889fc3a8edd4f50f41c93a9de2cd10",
 "RUNTIME.py":"ef658254e1cf285ff882a239e4f57026cf267a6f",
 "TEST.py":"c918454915ad908dcfefad6798edfd4b461edbd0",
 "THIN_ADAPTER.py":"f0d30b287027e62970849305cac867e891b3af85",
 "GENERIC_RUNTIME.py":"58f2ae9c3f0ef0ac55da2e58d0ed81ae88560296",
}
def git_blob_sha(p:Path)->str:
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
for n,s in EXPECTED.items():
    got=git_blob_sha(SUB/n)
    assert got==s,(n,got,s)

gov=json.loads((SUB/"GOVERNANCE.json").read_text())
assert gov["target_predicate"]=="LIVEBENCH_IF_GE_65_7"
assert gov["execution_binding"]["repository"]=="moxnixmdj/verification-capsule-runner"
assert gov["execution_binding"]["runner_label"]=="ubuntu-24.04"
assert gov["execution_binding"]["runner_class"]=="STANDARD_GITHUB_HOSTED"
assert gov["execution_binding"]["larger_or_paid_runner_allowed"] is False
assert gov["execution_binding"]["paid_external_model_or_api_allowed"] is False
assert gov["semantic_effect_if_independently_verified"]["resource_fit_or_terminal_completion_proved"] is False
assert gov["fresh_reality_authority"] is False
assert all(v==0 for v in gov["accounting"].values())

# Current first-party repository visibility.
req=urllib.request.Request(
    "https://api.github.com/repos/moxnixmdj/verification-capsule-runner",
    headers={"Accept":"application/vnd.github+json","User-Agent":"Project-Brain-independent-verifier"}
)
with urllib.request.urlopen(req,timeout=30) as r:
    repo=json.loads(r.read(2_000_000).decode("utf-8"))
assert repo["full_name"]=="moxnixmdj/verification-capsule-runner"
assert repo["private"] is False
assert repo["visibility"]=="public"

# Current first-party billing/runner documentation. This is deliberately live:
# if GitHub changes the rule, the binding fails instead of silently inheriting
# an obsolete zero-cost assumption.
docs_url="https://docs.github.com/en/actions/reference/runners/github-hosted-runners"
req=urllib.request.Request(docs_url,headers={"User-Agent":"Project-Brain-independent-verifier"})
with urllib.request.urlopen(req,timeout=30) as r:
    html=r.read(8_000_000).decode("utf-8","replace")
normalized=re.sub(r"\s+"," ",html).lower()
assert "free and unlimited on public repositories" in normalized
assert "ubuntu-24.04" in normalized

# This workflow itself is pinned to the declared standard Linux image.
assert os.environ.get("RUNNER_OS")=="Linux"

# Load candidate cost checker.
spec=importlib.util.spec_from_file_location("carrier",SUB/"RUNTIME.py")
carrier=importlib.util.module_from_spec(spec); assert spec and spec.loader
spec.loader.exec_module(carrier)
binding={
  "repository":"moxnixmdj/verification-capsule-runner",
  "repository_is_public":True,
  "runner_label":"ubuntu-24.04",
  "standard_public_runner_zero_incremental_spend_verified":True,
  "larger_or_paid_runner_allowed":False,
  "paid_external_model_or_api_allowed":False,
}
out=carrier.verify_binding(binding)
assert out["cost_binding_pass"] is True
assert out["zero_incremental_spend_or_entitlement_verified"] is True
assert out["resource_fit_proved"] is False
assert out["execution_success_proved"] is False
assert out["fresh_reality_authority"] is False
assert out["acceptance_credit_authorized"] is False

# Mutation teeth.
for key,value in {
 "repository_is_public":False,
 "standard_public_runner_zero_incremental_spend_verified":False,
 "larger_or_paid_runner_allowed":True,
 "paid_external_model_or_api_allowed":True,
}.items():
    bad=dict(binding); bad[key]=value
    assert carrier.verify_binding(bad)["cost_binding_pass"] is False,key
bad=dict(binding); bad["runner_label"]="ubuntu-latest-16-cores"
assert carrier.verify_binding(bad)["cost_binding_pass"] is False

# Prove the consequence against the exact previously-verified generic checker:
# this cost receipt is precisely the eighth field, no more.
canonical=types.ModuleType("canonical")
runtime_pkg=types.ModuleType("canonical.runtime")
canonical.runtime=runtime_pkg
sys.modules["canonical"]=canonical
sys.modules["canonical.runtime"]=runtime_pkg
gspec=importlib.util.spec_from_file_location(
 "canonical.runtime.generic_precommit_isolation_theorem_v1",
 SUB/"GENERIC_RUNTIME.py"
)
generic=importlib.util.module_from_spec(gspec); assert gspec and gspec.loader
sys.modules[gspec.name]=generic
gspec.loader.exec_module(generic)
tspec=importlib.util.spec_from_file_location("thin",SUB/"THIN_ADAPTER.py")
thin=importlib.util.module_from_spec(tspec); assert tspec and tspec.loader
tspec.loader.exec_module(thin)
before=thin.evaluate()
after=thin.with_zero_spend_receipt_proved()
assert before["proved_field_count"]==7 and before["thin_adapter_pass"] is False
assert before["unproved_fields"]==["zero_incremental_spend_or_entitlement_verified"]
assert after["proved_field_count"]==8 and after["thin_adapter_pass"] is True
assert after["unproved_fields"]==[]
assert after["execution_authority"] is False
assert after["fresh_reality_authority"] is False
assert after["acceptance_credit_authorized"] is False

print(json.dumps({
 "status":"PASS",
 "exact_candidate_blobs":EXPECTED,
 "repository_visibility":"public",
 "runner_label":"ubuntu-24.04",
 "github_public_standard_runner_zero_spend_rule_live":True,
 "zero_incremental_spend_or_entitlement_verified":True,
 "livebench_thin_adapter_after_binding":"8_OF_8_PASS",
 "resource_fit_proved":False,
 "execution_success_proved":False,
 "fresh_reality_authority":False,
 "acceptance_credit_delta":0,
},sort_keys=True))
