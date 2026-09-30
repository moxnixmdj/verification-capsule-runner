set -e
cd /app
printf '===== FILES =====\n'
find . -maxdepth 4 -type f -not -path './node_modules/*' -not -path './dist/*' | sort
printf '\n===== package.json =====\n'
cat package.json
printf '\n===== visibility.json =====\n'
cat visibility.json
printf '\n===== tsconfig.json =====\n'
cat tsconfig.json
printf '\n===== scripts/src =====\n'
for f in $(find scripts src -type f | sort); do
  echo "\n--- $f ---"
  sed -n '1,260p' "$f"
done
