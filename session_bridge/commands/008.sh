for s in 'Advanced hold filter' 'priority score' 'inventory-holds-export' 'eta-route'; do echo "--- $s ---"; grep -R -l "$s" /app/.next/static/chunks 2>/dev/null || true; done
