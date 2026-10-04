import json, pathlib, subprocess

P={
 "frontier":"verification_inputs/v10_overlay_frontier.json",
 "router":"verification_inputs/v10_overlay_router.json",
 "overlay":"verification_inputs/v10_overlay.json",
 "gate":"verification_inputs/v10_outreach_gate.json",
 "fanout":"verification_inputs/v10_owner_fanout.json",
}
H={
 "frontier":"2012926814d0d06405da56da64e589b06fef1756",
 "router":"4f8a547f1ade8231a705d3d028966c107e805a90",
 "overlay":"e41024fc8588ee5e4292ad38c758c202b1d31d38",
 "gate":"3868d99a7dbddb4a78f9adb5cd083d81cd90241e",
 "fanout":"9b59f951f5b7135bb167f2aaebc35e9960172fa4",
}
def blob(p): return subprocess.check_output(["git","rev-parse",f"HEAD:{p}"],text=True).strip()
for k,p in P.items():
    got=blob(p); assert got==H[k],(k,got,H[k])
load=lambda p: json.loads(pathlib.Path(p).read_text())
f,rt,ov,g,fo=[load(P[k]) for k in ("frontier","router","overlay","gate","fanout")]

waiting=f["waiting_external_facts"]
groups=[
 rt["self_service_pending_facts"],
 rt["owner_exclusive_or_owner_receipt_facts"],
 rt["owner_or_direct_platform_receipt_facts"],
 rt["dormant_conditions"],
]
flat=[x for grp in groups for x in grp]
assert len(waiting)==18
assert len(flat)==18
assert len(set(flat))==18
assert set(flat)==set(waiting)
assert [len(x) for x in groups]==[9,6,1,2]

assert rt["parent_frontier"]["git_blob_sha"]==H["frontier"]
assert ov["parent_frontier"]["git_blob_sha"]==H["frontier"]
assert ov["parent_verification"]["git_blob_sha"]=="226832c5e9d5f4121f26d93bd645ed51dce474fe"
assert ov["components"]["fact_router"]["git_blob_sha"]==H["router"]
assert ov["components"]["outreach_gate"]["git_blob_sha"]==H["gate"]
assert ov["components"]["owner_fanout"]["git_blob_sha"]==H["fanout"]
assert ov["invariant_partition_counts"]=={
 "v10_waiting_external_fact_count":18,
 "self_service":9,
 "owner_exclusive_or_owner_receipt":6,
 "owner_or_direct_platform_receipt":1,
 "dormant":2,
 "sum":18,
}

for fact in [
 "OMC_CLOUD_TRIAL_ACCOUNT_AND_EXACT_8A16GB_OR_STRONGER_SHAPE_ACCESS",
 "OMC_CLOUD_OBSERVED_NPROC_GE_8_USABLE_MEMORY_MB_GE_16384_FREE_STORAGE_MB_GE_51200",
 "OMC_CLOUD_DOCKER_DOCKER_COMPOSE_NO_PAID_OVERAGE_AND_HARBOR_PROTOCOL_PREFLIGHT",
 "BUILDKITE_RUNTIME_DISK_DOCKER_HARD_STOP_AND_PROTOCOL_PREFLIGHT",
]:
    assert fact in rt["self_service_pending_facts"]

assert "FINANCE_AGENT_V2_CUSTOM_FUNCTION_COMPARABILITY_TO_PUBLISHED_SHARED_DEFAULT_HARNESS" in rt["dormant_conditions"]
assert "VALS_OWNER_CUSTOM_HARNESS_COMPARABILITY_ACCEPTANCE_OR_PRIMARY_METHODOLOGY_CHANGE" in rt["owner_exclusive_or_owner_receipt_facts"]

rules=set(g["hard_rules"])|set(rt["hard_rules"])|set(ov["hard_rules"])
assert any("NO_EMAIL" in x and "FREE_TRIAL" in x for x in rules)
assert any("OMC" in x and "SELF_SERVICE" in x for x in rules)
assert rt["execution_authority"] is False and rt["promotion_authority"] is False and rt["fresh_reality_authority"] is False
assert ov["execution_authority"] is False and ov["promotion_authority"] is False and ov["fresh_reality_authority"] is False

owners={x["owner"] for x in fo["owner_exclusive_channels"]}
assert owners=={"Artificial Analysis","Vals AI","Cursor","Cognition","Zapier"}
assert "Buildkite support for trial/quota/runtime confirmation" in fo["channel_reclassification"]["excluded_support_or_self_service"]
assert fo["deduplication"]["self_service_support_channels_waiting"]==0

print("ROOT2_V10_OVERLAY_V2_PASS__18_OF_18_LOSSLESS_DISJOINT_PARTITION__ANTI_WISHFUL_OUTREACH__ZERO_CREDIT")
