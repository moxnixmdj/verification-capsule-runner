import hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parent
P=R/"brain/canonical/governance/ROOT3_SCOPE_CERTIFICATE_ADMISSIBILITY_REFINEMENT_ACTIVATION_V2.json"
d=P.read_bytes()
blob=hashlib.sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()
x=json.loads(d)
errors=[]
if blob!="d66adfe1b9ac5893e82aee1e8c4c9ae4050f5e3b": errors.append("BLOB_DRIFT")
if x.get("base_minimum_cut",{}).get("git_blob_sha")!="4d8ce78ebe312100bbfc524062199961c0c6479d": errors.append("CUT_SHA")
if x.get("base_minimum_cut",{}).get("verification_git_blob_sha")!="7a5e32351cd20c6ef15d50283e2753186e04e77d": errors.append("CUT_VERIFICATION_SHA")
if x.get("refinement",{}).get("git_blob_sha")!="25a39569f141e6699320b5fb70e6cc434eef07fa": errors.append("REFINEMENT_SHA")
if x.get("synthesis_scope_closure",{}).get("activation_git_blob_sha")!="60d845cf2370854bfd171154cf94946436be2c16": errors.append("SYNTHESIS_ACTIVATION_SHA")
if x.get("synthesis_scope_closure",{}).get("certificate_git_blob_sha")!="dea9028f92f111ee3c8be71615fa4b02e8a8bfb6": errors.append("SYNTHESIS_CERT_SHA")
if x.get("synthesis_scope_closure",{}).get("verification_git_blob_sha")!="1528485a15c98e89c9fb4dc50d691b6682e08542": errors.append("SYNTHESIS_VERIFY_SHA")
e=x.get("current_effect",{})
if e.get("root3_predicates")!=10: errors.append("ROOT3_COUNT")
if e.get("matched_scope_targets")!=7: errors.append("MATCHED_COUNT")
if e.get("minimum_event_classes")!=3: errors.append("EVENT_COUNT")
if e.get("currently_runnable_event_count")!=0: errors.append("RUNNABLE_COUNT")
if e.get("invalid_scope_shortcut_deleted") is not True: errors.append("SHORTCUT_RULE")
if e.get("synthesis_scope_relation_closed") is not True or e.get("synthesis_root3") is not False: errors.append("SYNTHESIS_STATE")
if x.get("fresh_reality_authority") is not False: errors.append("FRESH_REALITY")
if x.get("acceptance_credit_delta")!=0: errors.append("CREDIT")
out={"schema":"PROJECT_BRAIN_ROOT3_ADMISSIBILITY_V2_PUBLIC_VERIFICATION","status":"INDEPENDENT_PUBLIC_RUNNER_PASS__RULE_PRESERVED__SYNTHESIS_SCOPE_CLOSED__10_ROOT3__3_EVENTS__ZERO_CREDIT" if not errors else "FAIL_CLOSED","pass":not errors,"errors":errors}
print(json.dumps(out,indent=2,sort_keys=True))
raise SystemExit(0 if out["pass"] else 1)
