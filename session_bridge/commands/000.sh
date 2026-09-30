set -e
cd /app
echo '===== FILES ====='
find . -maxdepth 3 -type f -printf '%p %s bytes\n' | sort
echo '===== PYTHON MODULES ====='
for f in ./*.py; do
  [ -f "$f" ] || continue
  echo "===== $f ====="
  sed -n '1,320p' "$f"
done
