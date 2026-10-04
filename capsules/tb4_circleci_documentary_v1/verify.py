import hashlib,json
from pathlib import Path
p=Path(__file__).with_name("TB4_CIRCLECI_DOCUMENTARY_PREFLIGHT_REDUCTION_20261004_V1.json")
b=p.read_bytes()
sha=hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
assert sha=="a4fa8277482bfec8127b44682b5de2246e78259a",(sha,)
o=json.loads(b)
assert o["target_predicate"]=="CODING_TB4_GE_66_4"
assert o["derived"]["nominal_wall_minutes_at_xlarge_gen2"]=="416.6666666667"
assert o["incremental_spend_usd"]==0
assert o["terminal_cases_consumed"]==0
assert o["acceptance_credit_delta"]==0
assert o["fresh_reality_authority"] is False
assert o["promotion_authority"] is False
need={
"ACTUAL_ACCOUNT_XLARGE_GEN2_SELECTION",
"FREE_DISK_AT_JOB_START_GE_51200_MB",
"DOCKER_RUNTIME_PREFLIGHT",
"COMPOSE_RUNTIME_PREFLIGHT",
"8_CPU_CONTAINER_LIMIT_PREFLIGHT",
"CURRENT_FREE_CREDIT_BALANCE",
"RECOVERY_RUNTIME_WITHIN_FREE_ALLOWANCE",
"ZERO_CASE_HARBOR_PREFLIGHT"
}
assert set(o["remaining"])==need
print("PASS__EXACT_BLOB__ARITHMETIC__FAIL_CLOSED_RESIDUALS__ZERO_CREDIT")
