set -e
cd /app
printf '%s
' '=== MANIFEST CANDIDATES ==='
find /app -type f \( -iname '*manifest*.json' -o -iname 'packet*.json' -o -iname '*config*.json' \) -print | sort
printf '%s
' '=== ALL INCIDENT FILES ==='
find /app/data/incidents -type f -print | sort
printf '%s
' '=== CONTRACT DOCS ==='
cat /app/docs/migration_ticket.md
printf '\n--- review ops ---\n'
cat /app/docs/review_ops_digest.md
printf '\n--- events ---\n'
cat /app/data/incidents/parity-2026-10/sources/review_events.csv
printf '\n--- thresholds ---\n'
cat /app/data/incidents/parity-2026-10/sources/thresholds.json
printf '\n--- cli ---\n'
cat /app/parityctl/cli.py
