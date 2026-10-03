import hashlib, importlib.util, json
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

 src=(R/"candidate_runtime.py").read_text(encoding="utf-8")
 src=src.replace('ROOT = Path(__file__).resolve().parents[2]','ROOT = Path(__file__).resolve().parent / "fixture"')
 tmp=R/"_candidate_runtime_bound.py"; tmp.write_text(src,encoding="utf-8")
 spec=importlib.util.spec_from_file_location("candidate",tmp)
 m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
 out=m.evaluate()
 if out.get("pass") is not True: errors.append("LIVE:"+repr(out))
 if out.get("live_world",{}).get("unresolved_predicates")!=27: errors.append("OPEN")
 z=out.get("zero_reality_frontier",{})
 if z.get("unique_zero_reality_requirement_count")!=17: errors.append("REQ17")
 if z.get("nondominated_certificate_count")!=14: errors.append("CERT14")
 if z.get("covered_predicate_count")!=25: errors.append("COVER25")
 if z.get("primitive_zero_reality_work_units")!=31: errors.append("WORK31")
 if z.get("matched_priority_child_facts")!=16: errors.append("MATCH16")
 tr=out.get("transition",{})
 if set(tr.get("direct_reality_blocked_predicates") or [])!={"FINANCE_UNCOVERED_SCOPE_AUDIT","UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"}: errors.append("REALITY_BLOCKED_2")
 if len(tr.get("discharged_zero_reality_requirements") or [])!=2: errors.append("DISCHARGED_2")
 if out.get("fresh_reality_authority") is not False: errors.append("FRESH_REALITY")
 if any(out.get(k) not in (0,False) for k in ["new_reality_units_consumed","acceptance_credit_delta","family_credit_delta","ownership_credit_delta","execution_authority","promotion_authority"]): errors.append("CREDIT_OR_AUTHORITY")
 proj=J("candidate_projection.json")
 ex=proj.get("expected") or {}
 if ex.get("current_zero_reality_requirements")!=17 or ex.get("current_nondominated_zero_reality_certificates")!=14 or ex.get("primitive_zero_reality_work_units")!=31: errors.append("PROJECTION")
 print(json.dumps({"pass":not errors,"errors":errors,"verified_result":out},indent=2,sort_keys=True))
 return 0 if not errors else 1
if __name__=="__main__": raise SystemExit(main())
