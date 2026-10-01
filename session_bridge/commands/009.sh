set -e
for i in 1 2 3 4 5 6 7 8 9 10; do
  python3 /tmp/acceptance.py >/tmp/acceptance-$i.log
  tail -n 2 /tmp/acceptance-$i.log
done
python3 - <<'PY'
import threading,time,sys
sys.path.insert(0,"/app")
from app import make_engine,recover_engine

e=make_engine(max_entries_per_segment=2,flush_delay=0,metadata_delay=0)
orig=e._segment_manager.reserve_segment
entered=threading.Event(); release=threading.Event(); lock=threading.Lock(); n=[0]
def gate():
    with lock:
        n[0]+=1
        cur=n[0]
    if cur==1:
        entered.set()
        if not release.wait(2):
            raise RuntimeError("release timeout")
    return orig()
e._segment_manager.reserve_segment=gate
err=[]
def put(v):
    try: e.commit_update("k",v)
    except Exception as ex: err.append(repr(ex))
a=threading.Thread(target=put,args=("one",)); a.start()
assert entered.wait(1)
b=threading.Thread(target=put,args=("two",)); b.start()
deadline=time.time()+1
seen=False
while time.time()<deadline:
    snap=e.crash_snapshot()
    flat=[x for s in snap["segments"] for x in s["entries"]]
    if any(x["lsn"]==2 for x in flat):
        seen=True
        break
    time.sleep(.005)
assert seen
assert e.runtime_state()=={}
assert e.committed_entries()==[]
assert recover_engine(e.crash_snapshot())[1]==[]
release.set(); a.join(2); b.join(2)
assert not err and not a.is_alive() and not b.is_alive()
snap=e.crash_snapshot()
assert len(snap["segments"])==1
assert [x["lsn"] for x in snap["segments"][0]["entries"][:snap["segments"][0]["durable_count"]]]==[1,2]
assert e.runtime_state()=={"k":"two"}
assert recover_engine(snap)[0]=={"k":"two"}
e.close()
print("SAME_SEGMENT_OUT_OF_ORDER_PASS")
PY
