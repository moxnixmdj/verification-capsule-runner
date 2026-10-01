set -e
cd /app
echo '===== API SOURCE ====='
for f in api/*.py api/requirements.txt; do
  echo "===== $f ====="
  sed -n '1,520p' "$f"
done
echo '===== NETWORK / ENV ====='
env | sort | sed -n '1,240p'
echo '===== SERVICE PROBES ====='
python3 - <<'PY'
import socket
for host,port in [('mysql-db',3306),('postgres-db',5432),('redis',6379),('customer',9000),('main',8080)]:
    s=socket.socket(); s.settimeout(2)
    try:
        s.connect((host,port)); print(host,port,'OPEN')
    except Exception as e:
        print(host,port,'ERR',type(e).__name__,str(e))
    finally:
        s.close()
PY
echo '===== BASELINE API SAMPLE ====='
python3 - <<'PY'
import urllib.request
for p in ['/','/health','/docs','/openapi.json']:
    try:
        r=urllib.request.urlopen('http://main:8080'+p, timeout=3)
        b=r.read(4000)
        print(p,r.status,b.decode(errors='replace')[:4000])
    except Exception as e:
        print(p,'ERR',repr(e))
PY
