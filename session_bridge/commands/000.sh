set -euo pipefail
find /app -maxdepth 5 -type f -not -path '*/__pycache__/*' -print | sort