#!/usr/bin/env python3
import hashlib, importlib.util, json, pathlib, sys

ROOT=pathlib.Path(__file__).resolve().parent

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec)
    sys.modules[name]=mod
    spec.loader.exec_module(mod)
    return mod

producer=load("grounding_producer",ROOT/"plain_goal_bound_grounding.py")
verifier=load("grounding_verifier",ROOT/"plain_goal_bound_grounding_verify.py")
registry_raw=json.loads((ROOT/"BOUND_CAPABILITY_REGISTRY_V1.json").read_text())
registry=registry_raw["capabilities"]

cases=[
  {
    "id":"REAL_SOFTWARE_TEST_AUDIT",
    "goal":"Audit the Python tests with unittest and report passed failed and skipped counts.",
    "must_include":"python.tests.audit.unittest",
  },
  {
    "id":"FRESH_REUSE_RENDERED_BROWSER_CAPTURE",
    "goal":"Open the rendered browser page at https://example.com and capture a screenshot.",
    "must_include":"web.browser.rendered.capture.chromedriver",
  },
]
results=[]
for case in cases:
    out=producer.ground(case["goal"],registry)
    ok,reason=verifier.verify(case["goal"],out,registry)
    ids=set(out.get("candidate_capability_ids") or [])
    results.append({
      "id":case["id"],
      "goal":case["goal"],
      "producer_verified":bool(ok),
      "verifier_reason":reason,
      "must_include":case["must_include"],
      "must_include_present":case["must_include"] in ids,
      "candidate_capability_ids":sorted(ids),
      "grounded_clause_count":out.get("grounded_clause_count"),
      "unresolved_clause_indexes":out.get("unresolved_clause_indexes"),
      "model_dependency_count":out.get("model_dependency_count"),
      "goal_sha256":out.get("goal_sha256"),
      "result":out,
    })

negative_goal="Calibrate the neutrino interferometer phase drift."
negative=producer.ground(negative_goal,registry)
negative_ok,negative_reason=verifier.verify(negative_goal,negative,registry)

manifest={
  "schema":"PROJECT_BRAIN_PLAIN_GOAL_GROUNDING_PUBLIC_VALIDATION_V1",
  "source_pr_head":"1812e890b195b7bbeae6c078b7673c3c13f232c5",
  "source_main_base":"f4abfcdd5e44f83e2c591b22817f39ec0e0800b3",
  "producer_expected_git_blob":"00f5d0c1c742f444ad876103f251bb4476017dc1",
  "verifier_expected_git_blob":"d4aa64dc995845fcf8045f14f476f84b7f1d9cb8",
  "registry_expected_git_blob":"1b4a05c1b24070a7d2125713af11231214021a97",
  "model_dependency_count":0,
  "cases":results,
  "negative_case":{
    "goal":negative_goal,
    "verified":bool(negative_ok),
    "verifier_reason":negative_reason,
    "grounded_clause_count":negative.get("grounded_clause_count"),
    "candidate_capability_ids":negative.get("candidate_capability_ids"),
    "correctly_unresolved":negative.get("grounded_clause_count")==0 and not negative.get("candidate_capability_ids"),
  }
}
hard=[
  all(x["producer_verified"] for x in results),
  all(x["must_include_present"] for x in results),
  all(x["model_dependency_count"]==0 for x in results),
  manifest["negative_case"]["verified"],
  manifest["negative_case"]["correctly_unresolved"],
]
manifest["verdict"]="PASS" if all(hard) else "FAIL"
path=ROOT/"PLAIN_GOAL_GROUNDING_PUBLIC_VALIDATION.json"
path.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
print(json.dumps({
  "verdict":manifest["verdict"],
  "cases":[{k:v for k,v in x.items() if k!="result"} for x in results],
  "negative_case":manifest["negative_case"],
},indent=2,sort_keys=True))
raise SystemExit(0 if manifest["verdict"]=="PASS" else 2)
