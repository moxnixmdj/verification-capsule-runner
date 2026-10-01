set -e
python3 /app/consolidate.py >/tmp/current.log
python3 - <<'PY'
exec(open('/app/consolidate.py').read().split('state={}')[0])
d=SH[(1,0,0)]
for k in ['L1.expert_down.0','L1.expert_down.1','L1.shared_gateup','L1.grouped_gateup','L1.router','L1.shared_down','L0.mlp_down','L0.mlp_gateup','L0.attn_qkv','L0.attn_out']:
 v=d[k]
 print(k,tuple(v.shape),'min',float(v.min()),'max',float(v.max()),'std',float(v.std()))
PY
