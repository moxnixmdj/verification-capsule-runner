set -e
cd /app
echo '===== V4 AUDIT REPLAY ====='
PYTHONPATH=/app python3 /tmp/audit_dispatch.py
echo '===== FINAL OUTPUT ====='
python3 /app/dispatch.py --output /output/final-authored.json
cat /output/final-authored.json
echo '===== ARTIFACT HASHES ====='
sha256sum /app/navigation.py /app/aircraft.py /app/dispatch.py /app/requirements.txt /app/apt-packages.txt
