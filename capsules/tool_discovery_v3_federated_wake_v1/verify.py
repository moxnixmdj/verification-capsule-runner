import hashlib, json, urllib.request
from pathlib import Path

R=Path(__file__).resolve().parent
def B(p):
 d=(R/p).read_bytes()
 return hashlib.sha1(f"blob {len(d)}\0".encode()+d).hexdigest()
def J(p): return json.loads((R/p).read_text(encoding="utf-8"))

def get(url):
 req=urllib.request.Request(url,headers={"User-Agent":"project-brain-independent-verifier/1.0"})
 with urllib.request.urlopen(req,timeout=30) as r:
  return r.read().decode("utf-8","replace")

def main():
 errors=[]
 exp=J("EXPECTED_BLOBS.json")
 for p,v in exp.items():
  if B(p)!=v["git_blob_sha"]: errors.append("BLOB:"+p)
 intent=J("candidate_intent.json"); wake=J("candidate_wake.json")
 if wake.get("bounded_deductions",{}).get("strict_tool_discovery_acceptance_closed") is not False: errors.append("ACCEPTANCE_OVERCLAIM")
 if wake.get("bounded_deductions",{}).get("state")!="UNKNOWN__DO_NOT_INFER_NONEXISTENCE": errors.append("UNKNOWN_NOT_PRESERVED")
 for token in ["NO_GLOBAL_NONEXISTENCE_CLAIM","NO_DERIVATIVE_SYSTEM_CARD_TRANSCRIPTION_PROMOTED_AS_INDEPENDENT_MATCHED_EVIDENCE","NO_FRESH_TERMINAL_CASE_EXPOSURE"]:
  if token not in (wake.get("hard_nonclaims") or []): errors.append("MISSING_HARD_NONCLAIM:"+token)
 if any(wake.get(k) not in (0,False) for k in ["new_reality_units_consumed","incremental_spend_usd","capability_credit_delta","family_credit_delta","execution_authority","promotion_authority"]): errors.append("CREDIT_OR_AUTHORITY")
 local=(R/"fixture/toolathlon_readme.md").read_text(encoding="utf-8")
 if "600+ diverse tools" not in local or "Toolathlon-Verified" not in local or "public evaluation service" not in local: errors.append("OFFICIAL_REPO_EXPECTATION")
 try:
  hf=get("https://huggingface.co/datasets/hkust-nlp/Toolathlon-Verified_Trajectories/raw/main/README.md")
 except Exception as e:
  errors.append("HF_FETCH:"+type(e).__name__); hf=""
 if hf:
  low=hf.lower()
  if "108-task" not in low and "108 task" not in low and "108 tasks" not in low: errors.append("HF_108_TASKS_NOT_FOUND")
  if "claude opus 5.5" in low or "claude-opus-5-5" in low or "opus-5.5" in low: errors.append("HF_OPUS55_NOW_PRESENT__SOURCE_EPOCH_CHANGED")
  model_markers=[
   "claude opus 4.8","gpt-5.5","gemini 3.5 flash","glm-5.2",
   "kimi k2.7 code","deepseek v4 pro","deepseek v4 flash",
   "gemini 3.1 pro preview","claude sonnet 5","muse spark 1.1",
   "muse spark 1.2","kimi k3"
  ]
  present=[x for x in model_markers if x in low]
  if len(present)!=12: errors.append("HF_CURRENT_12_MODEL_MANIFEST_MISMATCH:"+str(len(present)))
  if "36" not in hf or "eval_stats.json" not in hf: errors.append("HF_36_RUN_SUMMARY_SIGNAL_MISSING")
 print(json.dumps({"pass":not errors,"errors":errors,"hf_sha256":hashlib.sha256(hf.encode()).hexdigest() if hf else None,"toolathlon_readme_blob":B("fixture/toolathlon_readme.md"),"new_reality_units_consumed":0,"acceptance_credit_delta":0},indent=2))
 return 0 if not errors else 1
if __name__=="__main__": raise SystemExit(main())
