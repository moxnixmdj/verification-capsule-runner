set -e
cd /app/src
echo '===== FINAL FILES ====='
find worker -maxdepth 1 -type f -print -exec sha256sum {} \;
echo '===== COMPILE ====='
python3 -m py_compile worker/__init__.py worker/config.py worker/state.py worker/worker.py
echo 'PY_COMPILE_PASS'
echo '===== RESTART PROTOCOL ====='
python3 /tmp/restart_protocol_probe.py
echo '===== STATE CORE ====='
python3 - <<'PY'
from worker.state import PartitionState, apply_transaction, preview_transaction, encode_state, decode_state
s=PartitionState(3)
assert preview_transaction(s,{'user_id':'u','transaction_id':'a','type':'credit','amount':10})==(10,True)
s,b,a=apply_transaction(s,{'user_id':'u','transaction_id':'a','type':'credit','amount':10},1)
assert a and b==10
s2=decode_state(encode_state(s),3)
assert s2.balances=={'u':10} and s2.processed=={'a'} and s2.next_offset==1
assert preview_transaction(s2,{'user_id':'u','transaction_id':'a','type':'debit','amount':99})==(10,False)
print('STATE_CORE_FINAL_PASS')
PY
echo '===== FINAL GUARD GREP ====='
grep -RInE 'TODO|FIXME|COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT|solution/|tests/' worker || true
echo 'FINAL_COMPLETION_GATE_PASS'
