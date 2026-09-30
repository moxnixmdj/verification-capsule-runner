set -e
cd /app
PYTHONPATH=/app python3 - <<'PY'
import itertools, json
import dispatch
A=json.load(open('/app/data/airports.json'))
AC=json.load(open('/app/data/aircraft.json'))
M=json.load(open('/app/data/manifest.json'))
W=json.load(open('/app/data/weather.json'))
D=dispatch._destinations(M)
for perm in itertools.permutations(D):
    route=['NAN',*perm,'NAN']
    try:
        p=dispatch._build_flight_plan(route,A,AC,M,W)
    except Exception as e:
        print('EXC',route,repr(e)); continue
    bad=[]
    for i,l in enumerate(p['legs']):
        fails=[k for k in ('takeoff_weight_ok','landing_weight_ok','fuel_capacity_ok','fuel_remaining_ok','crosswind_ok') if not l[k]]
        if fails: bad.append((i,l['from']+'-'+l['to'],fails,l['takeoff_weight_lbs'],l['landing_weight_lbs'],l['fuel_on_board_gal'],l['fuel_remaining_gal'],l['crosswind_component_kts']))
    print('ROUTE',route,'FEAS',p['summary']['route_feasible'],'TIME',p['summary']['total_time_min'],'BAD',bad)
PY
