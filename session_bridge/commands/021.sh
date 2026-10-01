set -e
cd /app
echo '=== MODEL INIT / SEED / WEIGHT CREATION ==='
grep -nE 'manual_seed|seed|reset_parameters|init|uniform_|normal_|kaiming|xavier|build_model|class ' /app/reference_model/model.py || true
echo '=== FULL REFERENCE MODEL ==='
cat /app/reference_model/model.py
echo '=== FRAMEWORK FILE LIST ==='
find /app/framework -maxdepth 1 -type f -printf '%f\n' | sort
