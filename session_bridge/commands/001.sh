set -euo pipefail
for f in /app/src/worker/config.py /app/src/worker/worker.py /app/src/worker/requirements.txt /app/supervisor.conf /app/run-slot.sh /app/entrypoint.sh /app/src/worker/__init__.py; do
  printf '\n===== %s =====\n' "$f"
  sed -n '1,260p' "$f"
done