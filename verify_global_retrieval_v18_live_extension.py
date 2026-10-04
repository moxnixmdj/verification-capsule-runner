#!/usr/bin/env python3
import hashlib,json,pathlib
R=pathlib.Path(__file__).resolve().parent/"subjects"
F={
"a":("GLOBAL_RETRIEVAL_V18_LIVE_EXTENSION_ACTIVATION_V1.json","fec22b8806212c59e3d2b9266ff533c79c2334e8"),
"v11":("RETRIEVAL_V11_STRATIFIED_LIVE_PROVIDER_ARENA_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json","59d1ff4676039c07ad5bdf2daf3e4f976265f7ba"),
"v12":("RETRIEVAL_V12_MULTI_QUERY_RECOVERY_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json","2bf84eccb2119b5ae66dac65e4efe3747ad73121"),
"v13":("RETRIEVAL_V13_RESIDUAL_ROOT_FIX_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json","8a436f7ba1593cb3d660f63450ec144b9fc69c27"),
"v14":("RETRIEVAL_V14_MAVEN_RESIDUAL_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json","3d92eca537007e38e497304d1886a4bdfcde7b88"),
"v16":("RETRIEVAL_V16_GRAPH_SNOWBALL_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json","13c402ded359447f32c89b4433e3c63fbe01074e"),
"v18":("RETRIEVAL_V18_VERSIONED_IDENTITY_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json","d991a068c50ccac3afa0f5d648ba047c222b3782"),
"v17":("RETRIEVAL_V17_VERSION_HISTORY_MISS_PUBLIC_RUNNER_EVIDENCE_20261004_V1.json","0732272970e00ee0bc3d0889f58eddde310bc22f"),
}
def blob(p):
 x=p.read_bytes();return hashlib.sha1(b"blob "+str(len(x)).encode()+b"\0"+x).hexdigest()
def load(k):
 n,s=F[k];p=R/n;assert blob(p)==s,(k,blob(p),s);return json.loads(p.read_text())
a=load("a");vs={k:load(k) for k in ("v11","v12","v13","v14","v16","v18","v17")}
for k in ("v11","v12","v13","v14","v16","v18"):
 assert vs[k]["independent_runner"]["conclusion"]=="success",k
assert "LIVE_MISS" in vs["v17"]["status"]
chain=a["live_evidence_chain"]
assert [x["union_hits"] for x in chain]==[12,22,27,28,29,30]
assert all(x["total"]==30 for x in chain)
assert chain[-1]["verification_git_blob_sha"]==F["v18"][1]
assert a["rejected_hypothesis_evidence"]["receipt_git_blob_sha"]==F["v17"][1]
m=a["measured_live_truth"]
assert m["finite_labeled_case_count"]==30
assert m["best_known_union_hit_count"]==30
assert m["best_known_union_miss_count"]==0
assert m["best_known_union_recall"]==1.0
assert m["open_world_completeness_claim"] is False
assert "BEHAVIOR_CONTEXT_CANDIDATE_GRAPH_SNOWBALL" in m["verified_routes_added"]
assert "PAGINATED_VERSION_HISTORY_POM_IDENTITY_BRIDGE" in m["verified_routes_added"]
assert a["incremental_spend_usd"]==0
for k in ("acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta"):
 assert a[k]==0
assert a["execution_authority"] is False and a["promotion_authority"] is False
print("GLOBAL_RETRIEVAL_V18_LIVE_EXTENSION_VERIFIED")
