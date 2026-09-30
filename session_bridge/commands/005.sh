set -e
cd /app/src
python3 - <<'PY'
from worker.state import PartitionState, encode_state
import hashlib, time
for n in (50000,100000,150000,300000):
    ids={hashlib.sha256(f'txn-{i}'.encode()).hexdigest() for i in range(n)}
    balances={f'user-{i}':i%10000-5000 for i in range(2000)}
    s=PartitionState(partition=0,next_offset=n,balances=balances,processed=ids)
    t=time.perf_counter(); blob=encode_state(s); dt=time.perf_counter()-t
    print(n,'encoded_bytes',len(blob),'seconds',round(dt,3))
PY
