set -e
cd /app
python - <<'PY'
import itertools,json,subprocess,string,math

def run(country, date):
    a=['legacy-score','--segment','consumer','--country',country,'--amount','100',
       '--failed-logins','0','--prior-chargebacks','0','--account-age-days','100','--as-of',date]
    return json.loads(subprocess.check_output(a,text=True))

for date in ['2026-10-10T12:00:00Z','2026-10-20T12:00:00Z']:
    fallback=run('',date)
    print('=== COUNTRY EXCEPTIONS',date,'fallback',json.dumps(fallback,sort_keys=True),'===')
    exceptions=[]
    for a in string.ascii_uppercase:
      for b in string.ascii_uppercase:
        cc=a+b
        out=run(cc,date)
        if out != fallback:
          exceptions.append((cc,out['route'],out['score']))
    for row in exceptions: print(*row)
    print('COUNT',len(exceptions))

print('=== ROUTE OFFSET NORMALIZATION ===')
base=['legacy-score','--segment','consumer','--country','US','--amount','120.5','--failed-logins','0','--prior-chargebacks','0','--account-age-days','400']
for ts in [
  '2026-10-14T23:59:59Z',
  '2026-10-15T00:00:00Z',
  '2026-10-14T20:00:00-04:00',
  '2026-10-15T01:00:00+02:00',
  '2026-10-15T00:00:00+00:00',
  '2026-10-15T00:00:00'
]:
  p=subprocess.run(base+['--as-of',ts],text=True,capture_output=True)
  print(repr(ts),'rc',p.returncode,'out',p.stdout.strip(),'err',p.stderr.strip())
PY
