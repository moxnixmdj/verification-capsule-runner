set -e
cd /app
python3 - <<'PY'
import copy
from recovery import recover_from_snapshot
snapshot={"segments":[
{"segment_id":5,"entries":[{"segment_id":0,"lsn":1,"key":"a","value":{"v":[99]}},{"segment_id":5,"lsn":4,"key":"d","value":"gap"}],"durable_count":2,"closed":True},
{"segment_id":2,"entries":[{"segment_id":999,"lsn":2,"key":"b","value":{"v":[2]}},{"segment_id":777,"lsn":1,"key":"a","value":{"v":[1]}},{"segment_id":2,"lsn":3,"key":"c","value":{"v":[3]}}],"durable_count":3,"closed":False},
{"segment_id":1,"entries":[{"segment_id":1,"lsn":99,"key":"ignored","value":1}],"closed":False}]}
original=copy.deepcopy(snapshot)
state,replayed,stats=recover_from_snapshot(snapshot)
print("STATE",state)
print("REPLAYED",replayed)
print("STATS",stats)
print("INPUT_UNCHANGED",snapshot==original)
print("LSNS",[e["lsn"] for e in replayed])
print("SIDS",[e["segment_id"] for e in replayed])
sh=copy.deepcopy(snapshot); sh["segments"]=[sh["segments"][1],sh["segments"][2],sh["segments"][0]]
print("SHUFFLED",recover_from_snapshot(sh))
PY
