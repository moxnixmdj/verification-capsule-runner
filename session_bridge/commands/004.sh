set -euo pipefail
sha256sum src/data/lead_input.json
printf '
--- submission ---
'
cat output/submission.json
printf '
--- reconciliation ---
'
cat output/reconciliation.json
