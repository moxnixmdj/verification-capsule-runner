from __future__ import annotations
import ast, hashlib, json
from pathlib import Path
from typing import Any, Mapping
ROOT=Path(__file__).resolve().parent
BRAIN=ROOT/"brain"
M=json.loads((ROOT/"EXPECTED_BRAIN_BLOBS.json").read_text(encoding="utf-8"))
OWNED="VERIFIED_OWNED_EQUAL_OR_BETTER"
TARGETS={
"SUBAGENT_DELEGATION_AND_COORDINATION":{"artifact":"canonical/runtime/delegation_whole_scope_candidate_v2.py","acceptance":"canonical/verification/DELEGATION_ACCEPTANCE_REDUCTION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json","binding":"canonical/verification/DELEGATION_V4_UNIVERSAL_SCOPE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json","container":"exact_brain_inputs","key":"canonical/verification/DELEGATION_V4_UNIVERSAL_SCOPE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json","ptr":"/exact_brain_blobs/canonical~1runtime~1delegation_whole_scope_candidate_v2.py","imports":{"__future__","collections","heapq","itertools","math","typing"}},
"SELF_VERIFICATION_DEBUGGING_AND_RECOVERY":{"artifact":"canonical/runtime/trajectory_failure_typed_ir_candidate_v7.py","acceptance":"canonical/verification/RECOVERY_OPUS55_ZERO_REALITY_PUBLIC_RUNNER_VERIFICATION_20261003_V2.json","binding":"canonical/verification/P1_UNIVERSAL_GENERATOR_TRANSPORT_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json","container":"exact_brain_inputs","key":"p1_universal_theorem_blob","ptr":"exact_brain_bytes.candidate_v7_blob","scope":"canonical/verification/P1_UNIVERSAL_SCOPE_RESTORATION_V9_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json","scope_key":"p1_scope_restoration_blob","imports":{"__future__","typing"}},
"TOOL_DISCOVERY_SELECTION_AND_LEARNING":{"artifact":"canonical/runtime/tool_discovery_information_safe_candidate.py","acceptance":"canonical/verification/TOOL_DISCOVERY_ACCEPTANCE_REDUCTION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json","binding":"canonical/verification/TOOL_DISCOVERY_UNIVERSAL_SCOPE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json","container":"exact_brain_blobs","key":"canonical/verification/TOOL_DISCOVERY_UNIVERSAL_SCOPE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json","ptr":"/exact_brain_blobs/canonical~1runtime~1tool_discovery_information_safe_candidate.py","imports":{"__future__","typing"}}}
FORBIDDEN={"__import__","eval","exec","compile","open","importlib.import_module","subprocess.run","subprocess.call","subprocess.Popen","os.system","requests.get","requests.post","httpx.get","httpx.post"}
BADPREFIX=("anthropic","openai","transformers","huggingface_hub","requests","httpx","aiohttp","socket","urllib","ollama","vllm","subprocess")
def load(p):
 x=json.loads((BRAIN/p).read_text(encoding="utf-8")); assert isinstance(x,dict); return x
def blob(p):
 b=(BRAIN/p).read_bytes(); return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def ptr(d,p):
 parts=([x.replace("~1","/").replace("~0","~") for x in p.split("/")[1:]] if p.startswith("/") else p.split("."))
 x=d
 for k in parts: x=x[k]
 return x
def ip(d):
 s=d.get("status"); return isinstance(s,str) and s.startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
def cname(n):
 f=n.func; a=[]
 while isinstance(f,ast.Attribute): a.append(f.attr); f=f.value
 if isinstance(f,ast.Name): a.append(f.id)
 return ".".join(reversed(a))
def audit(rel,allowed):
 e=[]; imports=set(); t=ast.parse((BRAIN/rel).read_text(encoding="utf-8"),filename=rel)
 for n in ast.walk(t):
  if isinstance(n,ast.Import):
   for a in n.names:
    imports.add(a.name.split(".",1)[0])
    if a.name.startswith(BADPREFIX): e.append("FORBIDDEN_IMPORT:"+a.name)
  elif isinstance(n,ast.ImportFrom):
   if n.level: e.append("RELATIVE_IMPORT:"+str(n.module or ""))
   else:
    m=n.module or ""; imports.add(m.split(".",1)[0])
    if m.startswith(BADPREFIX): e.append("FORBIDDEN_IMPORT:"+m)
  elif isinstance(n,ast.Call) and cname(n) in FORBIDDEN: e.append("FORBIDDEN_CALL:"+cname(n))
 if imports!=allowed: e.append("IMPORT_SET_MISMATCH")
 return sorted(set(e))
def main():
 ge=[]
 for p,h in M["exact_brain_blobs"].items():
  g=blob(p)
  if g!=h: ge.append("BLOB_DRIFT:"+p)
 closure=load("canonical/governance/TERMINAL_CLOSURE_MANIFEST_V1.json"); matrix=load("canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json")
 cr={x["id"]:x for x in closure["families"]}; mr={x["family"]:x for x in matrix["rows"]}; rows=[]
 for fam,s in TARGETS.items():
  e=[]; c=cr.get(fam,{})
  if not(c.get("opus55_acceptance_state")=="PASS" and c.get("opus55_acceptance_calibrated") is True and c.get("unresolved")==[]): e.append("STRICT_ACCEPTANCE_NOT_CLOSED")
  m=mr.get(fam,{})
  if m.get("status")!="OWNED_COMPONENT_NOT_FULL_FAMILY": e.append("PREPROMOTION_OWNERSHIP_STATE_DRIFT")
  a=load(s["acceptance"]); b=load(s["binding"])
  if not ip(a): e.append("ACCEPTANCE_RECEIPT_NOT_INDEPENDENT_PASS")
  if not ip(b): e.append("BINDING_RECEIPT_NOT_INDEPENDENT_PASS")
  if a.get(s["container"],{}).get(s["key"])!=M["exact_brain_blobs"][s["binding"]]: e.append("ACCEPTANCE_BINDING_CHAIN_BROKEN")
  try:
   if ptr(b,s["ptr"])!=M["exact_brain_blobs"][s["artifact"]]: e.append("ARTIFACT_BINDING_CHAIN_BROKEN")
  except Exception: e.append("ARTIFACT_BINDING_POINTER_UNRESOLVED")
  if "scope" in s:
   sr=load(s["scope"])
   if not ip(sr): e.append("SCOPE_RECEIPT_NOT_INDEPENDENT_PASS")
   if a.get("exact_brain_inputs",{}).get(s["scope_key"])!=M["exact_brain_blobs"][s["scope"]]: e.append("SCOPE_BINDING_CHAIN_BROKEN")
  e.extend(audit(s["artifact"],s["imports"]))
  if fam=="SUBAGENT_DELEGATION_AND_COORDINATION":
   v=a.get("verified_result",{})
   if v.get("closure_mode")!="ABSOLUTE_DOMINANCE" or v.get("scope_completeness_basis")!="UNIVERSAL_FORMAL_SCOPE_PROOF": e.append("DELEGATION_SCOPE_OR_STRENGTH_GAP")
  elif fam=="SELF_VERIFICATION_DEBUGGING_AND_RECOVERY":
   v=a.get("verified",{}); q=b.get("verified",{})
   if not(v.get("scope_complete") is True and v.get("objective_ceiling_or_floor") is True and v.get("proposed_family_acceptance_delta")==1): e.append("RECOVERY_SCOPE_OR_STRENGTH_GAP")
   if not(q.get("all_v7_intervention_scorer_pass") is True and q.get("all_source_native_rescue_scorer_pass") is True): e.append("RECOVERY_CAUSAL_BINDING_GAP")
  else:
   v=a.get("verified",{})
   if not(v.get("reduction_pass") is True and v.get("scope_complete") is True and v.get("objective_ceiling") is True): e.append("TOOL_SCOPE_OR_STRENGTH_GAP")
  rows.append({"family":fam,"pass":not e,"errors":sorted(set(e)),"artifact":s["artifact"],"artifact_sha":M["exact_brain_blobs"][s["artifact"]]})
 ok=not ge and len(rows)==3 and all(x["pass"] for x in rows)
 out={"schema":"PROJECT_BRAIN_ROOT3_OWNERSHIP_PUBLIC_INDEPENDENT_VERIFICATION_V1","status":"INDEPENDENT_PUBLIC_RUNNER_PASS__THREE_OF_THREE_ZERO_REALITY_OWNERSHIP_PROMOTION_ELIGIBLE" if ok else "FAIL_CLOSED","pass":ok,"global_errors":ge,"families":rows,"promotion_eligible_families":[x["family"] for x in rows if x["pass"]],"candidate_verified_owned_before":2,"candidate_verified_owned_after":5 if ok else 2,"new_reality_units_consumed":0,"incremental_spend_usd":0,"ownership_credit_delta":0,"promotion_authority":False,"rule":"STRICT_ACCEPTANCE + CONTENT_ADDRESSED_PROOF_CHAIN + CANONICAL_SELF_CONTAINED_OPERATIVE_ARTIFACT + NO_HIDDEN_CAPABILITY_PROVIDER"}
 print(json.dumps(out,indent=2,sort_keys=True)); return 0 if ok else 1
if __name__=="__main__": raise SystemExit(main())
