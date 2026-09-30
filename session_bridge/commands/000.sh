pwd
printf '%s\n' '--- runtime files ---'
find /app -maxdepth 3 -type f -not -path '/app/node_modules/*' | sort | sed -n '1,260p'
printf '%s\n' '--- package.json ---'
cat /app/package.json
