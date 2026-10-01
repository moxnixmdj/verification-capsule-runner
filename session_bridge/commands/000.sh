set -e
cd /app
echo '===== API SOURCE ====='
find api -maxdepth 2 -type f -printf '%p %s bytes\n' | sort
for f in api/*.py api/requirements.txt; do
  [ -f "$f" ] || continue
  echo "===== $f ====="
  sed -n '1,520p' "$f"
done
echo '===== SERVICES FROM MAIN ====='
python3 - <<'PY'
import socket
for host,port in [('mysql-db',3306),('postgres-db',5432),('redis',6379),('customer',9000),('main',8080)]:
    s=socket.socket(); s.settimeout(2)
    try:
        s.connect((host,port)); print(host,port,'OPEN')
    except Exception as e: print(host,port,'ERR',type(e).__name__,str(e))
    finally: s.close()
PY
echo '===== BASELINE HEALTH/API ====='
python3 - <<'PY'
import urllib.request
for host in ('http://localhost:8080','http://main:8080'):
  for p in ('/healthz','/openapi.json'):
    try:
      r=urllib.request.urlopen(host+p,timeout=3); b=r.read(10000)
      print(host+p,r.status,b.decode(errors='replace')[:10000])
    except Exception as e: print(host+p,'ERR',repr(e))
PY
