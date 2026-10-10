#!/usr/bin/env python3
import hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SURFACE="execution_guard/CURRENT_TERMINAL_EXECUTION_SURFACE_V1.json"
SLOT="terminal-bench-science/hysteretic-aquifer-control::trial-0"
DIGEST="sha256:681df0c3b2ada03a933ac4d2e11f07983676f87a9f26b61e416987904b880289"
ATTEMPT="aeadf4a998d2392b4aa277f1fdd6d31f057a81305dd98f9038f3a8b8bb14be68"
CLAIM_DIGEST="sha256:bc4522cfc367a3fd250ce53d0812b8a856f575dcf7eb00e8104781cfe0d29a15"
AUTH="696bf1cc8a5bcb38648288b6c6561a8b397c1912"
LEDGER="919d93263713eeabe70e7220df9df3e88363ec32"
EPOCH="1ae81185657fbdc8c07605dd2d79dce4a167c1fc"
EXEC_CLAIM="2a7e018daf466779be7d86d389a6fbf1231b17c9"
BRAIN_AUTH="c9346c09a963c080a90ed54eb26847b65d208f15"
BRAIN_LEDGER="8e24f2352ab34da06b486922c55985894f6a5f29"

def load(rel):
    return json.loads((ROOT/rel).read_text(encoding="utf-8"))

def blob(rel):
    raw=(ROOT/rel).read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def bind(row):
    assert blob(row["path"])==row["git_blob_sha"], row

def main():
    s=load(SURFACE)
    assert s["slot_id"]==SLOT and s["task_digest"]==DIGEST
    assert s["logical_attempt_id"]==ATTEMPT
    assert s["execution_claim_binding_digest"]==CLAIM_DIGEST
    assert s["execution_authority"] is True and s["task_read_authority"] is True
    assert s["task_read_history"] is False and s["task_started"] is False
    assert s["benchmark_trials_consumed"]==0
    assert not (ROOT/s["activation_path"]).exists()
    for key in ("authority","ledger","epoch","execution_claim"):
        bind(s[key])
    assert s["authority"]["git_blob_sha"]==AUTH
    assert s["ledger"]["git_blob_sha"]==LEDGER
    assert s["epoch"]["git_blob_sha"]==EPOCH
    assert s["execution_claim"]["git_blob_sha"]==EXEC_CLAIM

    a=load(s["authority"]["path"])
    assert a["brain_authority"]["git_blob_sha"]==BRAIN_AUTH
    assert a["brain_ledger"]["git_blob_sha"]==BRAIN_LEDGER
    assert a["ledger"]["git_blob_sha"]==LEDGER
    assert a["execution_authority"] is True and a["task_read_authority"] is True
    assert a["activation_authority"] is False
    assert a["task_read_history"] is False and a["task_started"] is False
    assert a["benchmark_trials_consumed"]==0

    l=load(s["ledger"]["path"])
    assert l["brain_authority"]["git_blob_sha"]==BRAIN_AUTH
    assert l["brain_ledger"]["git_blob_sha"]==BRAIN_LEDGER
    assert l["logical_attempt_id"]==ATTEMPT
    assert l["execution_claim_binding_digest"]==CLAIM_DIGEST
    assert l["rank20_task_read_history"] is False
    assert l["rank20_task_started"] is False
    assert l["rank20_start_cas_acquired"] is False
    assert l["rank20_benchmark_trials_consumed"]==0
    assert l["activation_present"] is False

    e=load(s["epoch"]["path"])
    c=load(s["execution_claim"]["path"])
    for doc in (e,c):
        assert doc["logical_attempt_id"]==ATTEMPT
        assert doc["execution_claim_binding_digest"]==CLAIM_DIGEST
        assert doc["brain_authority_blob"]==BRAIN_AUTH
        assert doc["brain_ledger_blob"]==BRAIN_LEDGER
        assert doc["execution_authority"] is True
        assert doc["execution_authority_effective"] is True
        assert doc["task_read_authority"] is True
        assert doc["activation_present"] is False
    assert e["public_authority_binding_blob"]==AUTH
    assert e["public_ledger_binding_blob"]==LEDGER
    assert c["public_authority_binding_blob"]==AUTH
    assert c["public_ledger_binding_blob"]==LEDGER
    assert c["epoch_git_blob_sha"]==EPOCH
    print("PASS__RANK20_V12_PROMOTED_EFFECTIVE_AUTHORITY__PREACTIVATION__ZERO_EXPOSURE")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
