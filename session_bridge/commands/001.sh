set -e
for f in /app/config.py /app/serializer.py /app/wal.py /app/wal_index.py /app/log_writer.py /app/segment_manager.py /app/checkpoint.py /app/recovery.py /app/metrics.py /app/app.py /app/_stage_a.py /app/_stage_b.py /app/_stage_c.py /app/_stage_d.py /app/_stage_e.py; do
  echo "===== $f ====="
  cat "$f"
done
