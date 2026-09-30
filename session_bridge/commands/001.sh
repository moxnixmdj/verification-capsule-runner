set -e
cd /app
printf '=== PROBE EXAMPLES ===\n'
cat docs/probe_examples.md
printf '\n=== STALE MODEL CARD ===\n'
cat docs/stale_model_card.md
printf '\n=== LEGACY SCORE HELP ===\n'
(legacy-score --help || true) 2>&1
printf '\n=== LEGACY SCORE LOCATION/TYPE ===\n'
command -v legacy-score
file "$(command -v legacy-score)"
