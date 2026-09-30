set -e
sed -i 's/sorted(rebuilt_needed)/sorted(rebuild_needed)/' /app/src/worker/worker.py
python3 -m py_compile /app/src/worker/worker.py /app/src/worker/state.py
python3 /tmp/restart_protocol_probe.py
