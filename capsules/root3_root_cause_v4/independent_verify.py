import hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parent
B=R/"brain"
M=json.loads((R/"EXPECTED_BRAIN_BLOBS.json").read_text())
def blob(p):
 d=(B/p).read_bytes()
 return hashlib.sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()
def load(p): return json.loads((B/p).read_text())
errors=[]
for p,h in M["exact_brain_blobs"].items():
 if blob(p)!=h: errors.append("BLOB_DRIFT:"+p)
term=load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")
root=load("canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json")
cut=load("canonical/governance/ROOT3_MINIMUM_ACTION_CUT_V4.json")
truth=term.get("truth") or {}
part=term.get("current_root_partition_override") or {}
acc=root.get("current_acceptance") or {}
if truth.get("opus55_atomic_acceptance")!="14/38_PROVED__24/38_OPEN__LIVEBENCH_IF_AND_UNKNOWN_DOMAIN_TRANSFER_AUDIT_CLEANLY_PROVED": errors.append("TERMINAL_TRUTH")
if acc.get("proved_atomic")!=14 or acc.get("unresolved_atomic")!=24: errors.append("ROOT_ACCEPTANCE")
want={"root1_positive_gap_count":0,"root2_only":15,"root3_only":6,"root2_and_root3":3,"root2_touching":18}
for k,v in want.items():
 if part.get(k)!=v: errors.append("PARTITION_"+k)
if cut.get("exact_state",{}).get("root3_touching_count")!=9: errors.append("CUT_ROOT3_COUNT")
live=cut.get("live_root3_predicates") or []
matched=cut.get("shared_matched_scope_targets") or []
if len(live)!=9 or len(set(live))!=9: errors.append("LIVE_ROOT3_SET")
if len(matched)!=7 or len(set(matched))!=7: errors.append("MATCHED_SET")
if not set(matched).issubset(set(live)): errors.append("MATCHED_NOT_SUBSET")
d=cut.get("exact_decomposition") or {}
if d.get("arithmetic_identity")!="9 = 7 + 1 + 1": errors.append("DECOMPOSITION")
if d.get("finance_direct_oracle_predicate")!="FINANCE_UNCOVERED_SCOPE_AUDIT": errors.append("FINANCE_DIRECT")
if "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT" not in (d.get("deleted_closed_root3_work") or [""])[0]: errors.append("UNKNOWN_DOMAIN_DELETE")
if len(cut.get("minimum_event_classes") or [])!=3: errors.append("EVENT_CLASSES")
for k in ["scheduling_authority","execution_authority","promotion_authority","fresh_reality_authority"]:
 if cut.get(k) is not False: errors.append("AUTH_"+k)
if cut.get("accounting",{}).get("acceptance_credit_delta")!=0: errors.append("CREDIT")
out={"schema":"PROJECT_BRAIN_ROOT3_V4_INDEPENDENT_PUBLIC_VERIFICATION","status":"PASS__CURRENT_14_24_ROOT3_9_EVENT_CUT__ZERO_CREDIT" if not errors else "FAIL_CLOSED","pass":not errors,"errors":errors,"verified":{"proved":14,"unresolved":24,"root3_touching":9,"shared_matched_scope":7,"event_classes":3,"fresh_reality_authority":False},"acceptance_credit_delta":0,"incremental_spend_usd":0}
print(json.dumps(out,indent=2,sort_keys=True))
raise SystemExit(0 if out["pass"] else 1)
