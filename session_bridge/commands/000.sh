set -e
cd /app
echo '===== FILES ====='
find . -maxdepth 2 -type f -printf '%p %s bytes\n' | sort
for f in navigation.py aircraft.py dispatch.py requirements.txt apt-packages.txt data/airports.json data/aircraft.json data/manifest.json data/weather.json; do
  echo "===== $f ====="
  if [ -f "$f" ]; then
    if echo "$f" | grep -q '\.json$'; then python3 -m json.tool "$f"; else sed -n '1,260p' "$f"; fi
  else
    echo MISSING
  fi
done
