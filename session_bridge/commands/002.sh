set -e
cd /app
python - <<'PY'
import json, subprocess

def probe(label, **kw):
    args=['legacy-score']
    mapping={
      'segment':'--segment','country':'--country','amount':'--amount',
      'failed':'--failed-logins','chargebacks':'--prior-chargebacks',
      'age':'--account-age-days','as_of':'--as-of'
    }
    for k,flag in mapping.items():
        args += [flag, str(kw.get(k,''))]
    p=subprocess.run(args,text=True,capture_output=True,check=True)
    print(label, p.stdout.strip())

base=dict(segment='consumer',country='US',amount='120.50',failed='0',chargebacks='0',age='400')
for ts in [
 '2026-10-01T00:00:00Z','2026-10-10T09:00:00Z',
 '2026-10-14T23:59:59Z','2026-10-15T00:00:00Z',
 '2026-10-15T11:59:59Z','2026-10-15T12:00:00Z',
 '2026-10-16T00:00:00Z','2026-11-01T00:00:00Z']:
    probe('DATE '+ts,**base,as_of=ts)

rows=[
 ('REQ1',dict(segment='consumer',country='US',amount='120.50',failed='0',chargebacks='0',age='400',as_of='2026-10-10T09:00:00Z')),
 ('REQ2',dict(segment='merchant',country='BR',amount='650',failed='7',chargebacks='1',age='80',as_of='2026-10-20T11:30:00Z')),
 ('REQ3',dict(segment='marketplace',country='NG',amount='40',failed='1',chargebacks='',age='',as_of='2026-10-16T02:00:00Z')),
 ('REQ4',dict(segment='consumer',country='CA',amount='320',failed='3',chargebacks='0',age='20',as_of='2026-10-18T15:00:00Z')),
 ('REQ5',dict(segment='merchant',country='GB',amount='240',failed='2',chargebacks='0',age='',as_of='2026-10-05T12:00:00Z')),
]
for label,kw in rows: probe(label,**kw)
PY
