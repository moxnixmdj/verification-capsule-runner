set -e
for f in /app/entrypoint.sh /app/run-slot.sh /app/supervisor.conf /app/src/worker/__init__.py /app/src/worker/config.py /app/src/worker/requirements.txt /app/src/worker/worker.py; do
  echo
  echo "===== $f ====="
  cat "$f"
done
