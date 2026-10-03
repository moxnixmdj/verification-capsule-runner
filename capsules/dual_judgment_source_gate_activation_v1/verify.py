import hashlib, importlib.util, json, sys
from pathlib import Path

R=Path(__file__).resolve().parent
def B(p):
 d=(R/p).read_bytes()
 return hashlib.sha1(f"blob {len(d)}\0".encode()+d).hexdigest()
def J(p): return json.loads((R/p).read_text(encoding="utf-8"))

def main():
 errors=[]
 for p,v in J("EXPECTED_BRAIN_BLOBS.json").items():
  if B(p)!=v["git_blob_sha"]: errors.append("BLOB:"+p)
 # make candidate runtime resolve its ROOT fixture by loading a transformed copy
 src=(R/"candidate_runtime.py").read_text(encoding="utf-8")
 src=src.replace('ROOT=Path(__file__).resolve().parents[2]','ROOT=Path(__file__).resolve().parent / "fixture"')
 tmp=R/"_candidate_runtime_bound.py"; tmp.write_text(src,encoding="utf-8")
 # activation itself is expected under fixture canonical path
 act_src=R/"candidate_activation.json"
 act_dst=R/"fixture/canonical/governance/DUAL_JUDGMENT_SOURCE_GATE_ACTIVATION_V1.json"
 act_dst.parent.mkdir(parents=True,exist_ok=True); act_dst.write_bytes(act_src.read_bytes())
 spec=importlib.util.spec_from_file_location("candidate",tmp)
 m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
 out=m.evaluate()
 if out.get("pass") is not True: errors.append("ACTIVATION:"+repr(out))
 if out.get("discharged_requirements") != sorted([
  "BRAIN_OWNED_OR_PERMISSIVELY_INTERNALIZED_FINANCE_JUDGMENT_SOURCE_GATE_PASS",
  "BRAIN_OWNED_OR_PERMISSIVELY_INTERNALIZED_UNKNOWN_DOMAIN_JUDGMENT_SOURCE_GATE_PASS",
 ]): errors.append("REQUIREMENTS")
 if out.get("remaining_acceptance_predicate_delta") != 0: errors.append("ACCEPTANCE_OVERCLAIM")
 if out.get("new_reality_units_consumed") != 0: errors.append("REALITY")
 if out.get("global_fresh_reality_authority") is not False: errors.append("GLOBAL_REALITY_AUTHORITY")
 print(json.dumps({"pass":not errors,"errors":errors,"new_reality_units_consumed":0,"incremental_spend_usd":0},indent=2))
 return 0 if not errors else 1
if __name__=="__main__": raise SystemExit(main())
