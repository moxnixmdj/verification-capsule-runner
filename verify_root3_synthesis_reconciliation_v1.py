#!/usr/bin/env python3
import json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parent
F={
"root":"fixtures/root3_synth_recon_terminal_root.json",
"res":"fixtures/root3_synth_recon_residual.json",
"cut":"fixtures/root3_synth_recon_mincut.json",
"ua":"fixtures/root3_synth_recon_scope_activation.json",
"sp":"fixtures/root3_synth_recon_superportfolio.json",
"zc":"fixtures/root3_synth_recon_zero_cut.json",
"fr":"fixtures/root3_synth_recon_frontier.json",
"ta":"fixtures/root3_synth_recon_terminal_authority.json",
"cert":"fixtures/root3_synth_recon_synthesis_certificate.json",
"receipt":"fixtures/root3_synth_recon_synthesis_activation_receipt.json",
}
H={
F["root"]:"c19135025f17cdb9acf65aaf7d17d660aae9189d",
F["res"]:"bad32d1e90bf0e54bb1176b67ad677336f40d71d",
F["cut"]:"6cfc9d1365e879637261e6c14d6cd09f21719d26",
F["ua"]:"28573015115365d76422bddf80520c7d313040df",
F["sp"]:"78615211c9cd40e79afc2c5e5624893b9a503ef7",
F["zc"]:"cc1981abb7e80b7d197105fdcb3955a5e54d4e44",
F["fr"]:"12e3ff86ad5f4436f1679ec5257d92f7c89f5c08",
F["ta"]:"2c759919f8ff640453fccff645bfb4681957e20e",
F["cert"]:"dea9028f92f111ee3c8be71615fa4b02e8a8bfb6",
F["receipt"]:"1528485a15c98e89c9fb4dc50d691b6682e08542",
}
e=[]
for p,h in H.items():
    got=subprocess.check_output(["git","hash-object",p],text=True).strip()
    if got!=h:e.append("BLOB:"+p)
D={k:json.loads((R/p).read_text()) for k,p in F.items()}
pid="SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR"
cert=D["cert"]
if not (cert.get("verified") is True and cert.get("independent") is True and cert.get("basis")=="LOSSLESS_DECOMPOSITION" and cert.get("scope_relation")=="PROVEN_STRONGER"):
    e.append("CERT_ADMISSIBILITY")
if not (cert.get("coverage_complete") is True and cert.get("coverage_relation")=="EXACT_UNION" and cert.get("coverage_proof_verified") is True):
    e.append("CERT_COVERAGE")
receipt=D["receipt"].get("verified") or {}
if receipt.get("before_root_class")!="ROOT2_AND_ROOT3" or receipt.get("after_root_class")!="ROOT2_ONLY":
    e.append("ACTIVATION_RECEIPT_CLASS")
if receipt.get("after_root3_involved_count")!=10 or receipt.get("root2_involved_count")!=19 or receipt.get("unresolved_total")!=26:
    e.append("ACTIVATION_RECEIPT_COUNTS")

root=D["root"]
acc=root.get("current_acceptance") or {}
if (acc.get("accepted_families"),acc.get("open_families"),acc.get("proved_atomic"),acc.get("unresolved_atomic"),acc.get("terminal"))!=(5,14,12,26,False):
    e.append("ACCEPTANCE")
part=root.get("current_residual_root_partition") or {}
r2=part.get("root2_only") or []; r3=part.get("root3_only") or []; mix=part.get("root2_and_root3") or []
if (part.get("root2_only_count"),part.get("root3_only_count"),part.get("root2_and_root3_count"),part.get("unresolved_total"))!=(16,7,3,26):
    e.append("ROOT_COUNTS")
if pid not in r2 or pid in r3 or pid in mix:e.append("SYNTH_CLASS")
if len(set(r2)|set(r3)|set(mix))!=26 or set(r2)&set(r3) or set(r2)&set(mix) or set(r3)&set(mix):
    e.append("ROOT_PARTITION")

srow=next((x for x in D["res"].get("compressed_residuals",[]) if x.get("predicate_id")==pid),None)
if not isinstance(srow,dict) or srow.get("root_class")!="ROOT2" or srow.get("scope_relation_closed") is not True:
    e.append("RESIDUAL")

if (D["cut"].get("derivation") or {}).get("live_root3_predicates")!=10:e.append("MINCUT")
if (D["ua"].get("current_truth") or {}).get("live_root3_predicates")!=10:e.append("UA_COUNT")
live={x.get("id") for x in D["ua"].get("exact_work_classes",[]) if isinstance(x,dict)}
closed={x.get("id") for x in D["ua"].get("closed_work_classes",[]) if isinstance(x,dict)}
if "ROOT3_SYNTHESIS_SCOPE_RELATION_V1" in live or "ROOT3_SYNTHESIS_SCOPE_RELATION_V1" not in closed:e.append("UA_CLASS")

spids={x.get("predicate_id") for x in D["sp"].get("matched_scope_targets",[]) if isinstance(x,dict)}
if pid in spids or (D["sp"].get("execution_compression") or {}).get("matched_scope_target_count")!=7:e.append("SUPERPORTFOLIO")

z=D["zc"].get("exact_state") or {}
if (z.get("root2_only_count"),z.get("root3_only_count"),z.get("root2_and_root3_count"))!=(16,7,3):e.append("ZERO_CUT")
fr=D["fr"]; fx=fr.get("exact_state") or {}
if (fx.get("root2_only_count"),fx.get("root3_only_count"),fx.get("root2_and_root3_count"),fx.get("root2_involved_count"),fx.get("root3_involved_count"))!=(16,7,3,19,10):e.append("FRONTIER_COUNTS")
if (fr.get("authority") or {}).get("root_state",{}).get("git_blob_sha")!=H[F["root"]]:e.append("FR_ROOT_PTR")
if (fr.get("authority") or {}).get("root3_residual_compression",{}).get("git_blob_sha")!=H[F["res"]]:e.append("FR_RES_PTR")
if (fr.get("authority") or {}).get("root3_minimum_action_cut",{}).get("git_blob_sha")!=H[F["cut"]]:e.append("FR_CUT_PTR")

ta=D["ta"]; truth=ta.get("truth") or {}
if truth.get("opus55_acceptance")!="5/19_PASS__14/19_OPEN" or truth.get("achieved") is not False:e.append("TA_TRUTH")
src=ta.get("sources") or {}
checks=[
("terminal_root_cause_state",F["root"]),("root2_root3_minimum_execution_frontier_v1",F["fr"]),
("root3_residual_compression_v1",F["res"]),("current_zero_reality_minimum_cut_v8",F["zc"]),
("root3_minimum_action_cut",F["cut"])]
for k,p in checks:
    if src.get(k,{}).get("git_blob_sha")!=H[p]:e.append("TA_PTR:"+k)
ss=src.get("synthesis_lossless_scope_activation") or {}
if ss.get("certificate_git_blob_sha")!=H[F["cert"]] or ss.get("verification_git_blob_sha")!=H[F["receipt"]]:
    e.append("TA_SYNTH_PTR")
for d in D.values():
    if isinstance(d,dict):
        for k in ("acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta"):
            if k in d and d.get(k)!=0:e.append("CREDIT:"+k)
        if "fresh_reality_authority" in d and d.get("fresh_reality_authority") is not False:e.append("REALITY_OVERCLAIM")
out={"schema":"PROJECT_BRAIN_ROOT3_SYNTHESIS_RECONCILIATION_INDEPENDENT_VERIFICATION_V1",
"status":"INDEPENDENT_PASS__SYNTHESIS_ROOT3_SCOPE_CLOSED__ROOT3_11_TO_10__ROOT2_19_UNCHANGED__26_UNRESOLVED__ZERO_CREDIT" if not e else "FAIL_CLOSED",
"pass":not e,"errors":sorted(set(e)),"accepted_families":5,"proved_atomic":12,"unresolved_atomic":26,
"root2_only_count":16,"root3_only_count":7,"root2_and_root3_count":3,"root2_involved_count":19,"root3_involved_count":10,
"new_reality_units_consumed":0,"incremental_spend_usd":0,"acceptance_credit_delta":0,"family_credit_delta":0,"capability_credit_delta":0,"ownership_credit_delta":0,
"execution_authority":False,"promotion_authority":False,"fresh_reality_authority":False}
print(json.dumps(out,indent=2,sort_keys=True));sys.exit(0 if not e else 1)
