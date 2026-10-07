#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CAP="$ROOT/verification/capsule"

declare -A EXPECTED=(
  ["verification/capsule/canonical/runtime/same_identity_supervisor_credited_v2.py"]="45d48c23ec4ae429550c264c07f530b0347430cb"
  ["verification/capsule/canonical/verification/run_long_horizon_continuity_v2.py"]="b861f1710261de5d973ce6f2c34489ac38de65c8"
  ["verification/capsule/canonical/runtime/root3_production_astra_launcher_v1.py"]="3ac42e7be5a391cfda738131ecb0d3d600fa2147"
  ["verification/capsule/canonical/runtime/root3_strict_current_bootstrap_v2.py"]="7d6e4f4e00fda4eae6ff1974f68f970ceee69c2e"
  ["verification/capsule/canonical/runtime/root3_subprocess_mediator_v2.py"]="80560cdfa91c11a4b47b9ee2161af726b2f9bccf"
  ["verification/capsule/canonical/runtime/root3_subprocess_mediator_v1.py"]="8443b61b15cb2bc597c4fa292650f2a0aae899b5"
  ["verification/capsule/canonical/runtime/root3_subprocess_callsite_classifier_v1.py"]="e654b264096dba724d82f04e5adef0dc6d6c90f7"
  ["verification/capsule/canonical/runtime/root3_subprocess_effect_class_registry_v1.py"]="24e00a3e6b70d0879cab664a8512f243973c6196"
  ["verification/capsule/canonical/runtime/root3_child_process_channel_registry_v1.py"]="fc737c1ff5d767d590a5ac52b604890f5d22b1c5"
  ["verification/capsule/canonical/runtime/root3_two_class_attempt_authorizer_v1.py"]="5aac8664433115c47d24e0fbbca15b81126753ee"
  ["verification/capsule/canonical/runtime/root3_read_only_local_file_query_executor_v1.py"]="74166a80c47ed8ddce7bae7b61a3a3610ac2ef8a"
  ["verification/capsule/canonical/runtime/root3_pdf_raster_temp_executor_v1.py"]="c07c632ac43e591bdde139f3440bdbe288ea930c"
  ["verification/capsule/canonical/runtime/zero_ambient_namespace_launcher_v1.py"]="6e687527e9c4da82fb5d974a729aaa263ee73ea8"
  ["verification/capsule/canonical/runtime/astra_runtime.py"]="3567cfd77eae06e2d384c5e0b18972b2d3a62c3b"
  ["verification/capsule/canonical/runtime/continuous_obs_runtime.py"]="e2533a0335c4f6824b9542944d4682aeefb36b2b"
  ["verification/capsule/canonical/runtime/honesty_load_bearing_result_gate_v1.py"]="6506690507854f3f28ff0c6161e34b79e9687c0b"
  ["verification/capsule/canonical/runtime/honesty_envelope_v1.py"]="1ff02d62322b76068933498e869b1ee22949b991"
  ["verification/capsule/canonical/runtime/root3_typed_durable_admin_write_v1.py"]="6c488b10b8afbaf61781703775cfd9a79710de52"
)

for path in "${!EXPECTED[@]}"; do
  got="$(git -C "$ROOT" hash-object "$ROOT/$path")"
  test "$got" = "${EXPECTED[$path]}"
done
echo "EXACT_BRAIN_BLOB_MIRROR_PASS ${#EXPECTED[@]}/18"

mkdir -p "$CAP/canonical/governance"
python - "$CAP" <<'PY'
import json, pathlib, sys
cap=pathlib.Path(sys.argv[1])
fixtures={
  "canonical/CANONICAL_POINTER.json":{"canonical_generation":"PUBLIC-CONTINUITY-CAPSULE-V1"},
  "canonical/governance/ACTIVE_GOAL_HIERARCHY_V1.json":{
    "schema":"PUBLIC_CONTINUITY_CAPSULE_FIXTURE","status":"SYNTHETIC_NONAUTHORITATIVE"
  },
  "canonical/governance/REAL_OUTPUT_SCOREBOARD_V1.json":{
    "schema":"PUBLIC_CONTINUITY_CAPSULE_FIXTURE","status":"SYNTHETIC_NONAUTHORITATIVE"
  },
}
for rel,value in fixtures.items():
    p=cap/rel
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print("SYNTHETIC_OBS_FIXTURE_READY")
PY

cd "$CAP"
export PYTHONPATH=.
python canonical/verification/run_long_horizon_continuity_v2.py "$ROOT/verification/result.json"

python - "$ROOT/verification/result.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1],encoding="utf-8"))
assert r["all_boolean_checks_pass"] is True,r
assert r["fresh_reality_units_consumed"]==0,r
assert r["incremental_spend_usd"]==0,r
assert r["acceptance_credit_delta"]==0,r
assert r["family_credit_delta"]==0,r
assert r["capability_credit_delta"]==0,r
assert r["ownership_credit_delta"]==0,r
print("CONTINUITY_CURRENT_CHILD_SEAM_PUBLIC_CAPSULE_PASS")
PY
