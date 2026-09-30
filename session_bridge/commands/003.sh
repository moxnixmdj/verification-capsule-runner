set -e
cd /app
python - <<'PY'
import json, math, subprocess
def probe(**kw):
    args=['legacy-score',
      '--segment',str(kw.get('segment','consumer')),
      '--country',str(kw.get('country','US')),
      '--amount',str(kw.get('amount','100')),
      '--failed-logins',str(kw.get('failed','0')),
      '--prior-chargebacks',str(kw.get('chargebacks','0')),
      '--account-age-days',str(kw.get('age','100')),
      '--as-of',str(kw.get('as_of','2026-10-10T12:00:00Z'))]
    o=json.loads(subprocess.check_output(args,text=True))
    p=float(o['score']); z=math.log(p/(1-p))
    return o['route'],p,z
def sweep(name,vals,date):
    print('\n###',date,name)
    for v in vals:
        try:
            r,p,z=probe(as_of=date,**{name:v})
            print(f'{v!r}\t{r}\t{p:.6f}\t{z:.9f}')
        except Exception as e: print(repr(v),'ERR',repr(e))
for date in ['2026-10-10T12:00:00Z','2026-10-20T12:00:00Z']:
    for name,vals in [
      ('amount',['','0','1','10','40','100','120.50','240','320','650','1000','10000']),
      ('failed',['','0','1','2','3','5','7','10','20']),
      ('chargebacks',['','0','1','2','3','5']),
      ('age',['','0','1','7','20','30','80','100','365','400','1000']),
      ('segment',['','consumer','merchant','marketplace','enterprise','other']),
      ('country',['','US','CA','GB','BR','NG','DE','FR','IN','ZZ'])
    ]: sweep(name,vals,date)
PY
