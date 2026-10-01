set -e
python3 /app/consolidate.py >/tmp/current.log
python3 - <<'PY'
exec(open('/app/consolidate.py').read().split('state={}')[0])
for key in ['L1.shared_gateup','L1.shared_down','L1.router','L1.expert_bias']:
 a=SH[(1,0,0)][key]; b=SH[(1,0,1)][key]
 print(key,float((a-b).abs().max()))
PY
