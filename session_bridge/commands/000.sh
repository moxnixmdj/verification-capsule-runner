set -e
cd /app
printf '=== TREE ===\n'
find . -maxdepth 5 -type f | sort | sed -n '1,320p'
printf '\n=== SIZES ===\n'
find data/incidents/parity-2026-10 -type f -printf '%p %s bytes\n' 2>/dev/null | sort
printf '\n=== MIGRATION TICKET ===\n'
cat docs/migration_ticket.md
printf '\n=== REVIEW OPS DIGEST ===\n'
cat docs/review_ops_digest.md
printf '\n=== REBUILD SCRIPT ===\n'
cat rebuild_parity_report.sh
printf '\n=== PARITYCTL SOURCE ===\n'
find parityctl -type f -maxdepth 4 -print | sort | while read f; do echo "\n--- $f ---"; cat "$f"; done
printf '\n=== PACKET FILES (TEXT) ===\n'
find data/incidents/parity-2026-10 -type f | sort | while read f; do
  echo "\n--- $f ---"
  case "$f" in
    *.json|*.jsonl|*.csv|*.txt|*.md|*.yaml|*.yml) sed -n '1,260p' "$f" ;;
    *) file "$f" ;;
  esac
done
