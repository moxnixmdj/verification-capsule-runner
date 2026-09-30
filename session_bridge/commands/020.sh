set -e
cd /app
printf '%s
' '=== MANIFEST ==='
cat manifest.json
printf '%s
' '=== MIGRATION ==='
cat docs/migration_ticket.md
printf '%s
' '=== REVIEW OPS ==='
cat docs/review_ops_digest.md
printf '%s
' '=== EVENTS ==='
cat data/incidents/parity-2026-10/sources/review_events.csv
printf '%s
' '=== THRESHOLDS ==='
cat data/incidents/parity-2026-10/sources/thresholds.json
printf '%s
' '=== CURRENT CLI ==='
cat parityctl/cli.py
