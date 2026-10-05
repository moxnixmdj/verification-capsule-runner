import hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parent; B=R/"brain"
M=json.loads((R/"EXPECTED_BRAIN_BLOBS.json").read_text())
def blob(p):
 d=(B/p).read_bytes(); return hashlib.sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()
def load(p): return json.loads((B/p).read_text())
errors=[]
for p,h in M["exact_brain_blobs"].items():
 if blob(p)!=h: errors.append("BLOB_DRIFT:"+p)
term=load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")
root=load("canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json")
r2=load("canonical/governance/ROOT2_18_CURRENT_14_24_SCHEDULING_ACTIVATION_V1.json")
r3=load("canonical/governance/ROOT3_MINIMUM_ACTION_CUT_V5.json")
cut=load("canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V12.json")
acc=root.get("current_acceptance") or {}
if (acc.get("proved_atomic"),acc.get("unresolved_atomic"))!=(14,24): errors.append("ACCEPTANCE")
if r2.get("scheduling_authority") is not True or r2.get("execution_authority") is not False: errors.append("ROOT2_AUTH")
if r3.get("exact_state",{}).get("root3_touching_count")!=9: errors.append("ROOT3_COUNT")
if cut.get("exact_state",{}).get("root2_touching_count")!=18 or cut.get("exact_state",{}).get("root3_touching_count")!=9: errors.append("CUT_COUNTS")
groups=cut.get("minimum_zero_reality_action_groups") or []
if len(groups)!=9 or len({g["id"] for g in groups})!=9: errors.append("GROUP_COUNT")
dels={d.get("predicate") for d in cut.get("deletions_since_v11") or [] if d.get("predicate")}
if "LIVEBENCH_IF_GE_65_7" not in dels or "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT" not in dels: errors.append("CLOSED_DELETIONS")
allpred=set()
for g in groups: allpred.update(g.get("predicates") or [])
if "LIVEBENCH_IF_GE_65_7" in allpred or "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT" in allpred: errors.append("CLOSED_RESCHEDULED")
for k in ["scheduling_authority","execution_authority","promotion_authority","fresh_reality_authority"]:
 if cut.get(k) is not False: errors.append("CUT_AUTH_"+k)
if cut.get("accounting",{}).get("acceptance_credit_delta")!=0: errors.append("CUT_CREDIT")
out={"schema":"PROJECT_BRAIN_ZERO_REALITY_V12_INDEPENDENT_PUBLIC_VERIFICATION","status":"PASS__CURRENT_14_24_MINIMUM_ZERO_REALITY_CUT__ZERO_CREDIT" if not errors else "FAIL_CLOSED","pass":not errors,"errors":errors,"verified":{"proved":14,"unresolved":24,"root2_touching":18,"root3_touching":9,"action_groups":9,"fresh_reality_authority":False},"acceptance_credit_delta":0,"incremental_spend_usd":0}
print(json.dumps(out,indent=2,sort_keys=True)); raise SystemExit(0 if out["pass"] else 1)
