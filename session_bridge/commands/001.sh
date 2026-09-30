set -e
cd /app
bun run release
printf '\n===== DIST =====\n'
find dist -maxdepth 2 -type f -print -exec sh -c 'echo "--- $1"; sed -n "1,220p" "$1"' _ {} \;
printf '\n===== SMOKE =====\n'
bun run smoke:client
bun run smoke:server
printf '\n===== TRACE =====\n'
set +e
bun dist/client-entry.js --trace-probe 2>&1
code=$?
set -e
echo "TRACE_EXIT=$code"
