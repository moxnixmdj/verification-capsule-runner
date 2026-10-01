set -e
cd /app
sed -i '1a import sys; sys.path.insert(0, "/app")' /tmp/variant_probe.py
python3 /tmp/variant_probe.py
