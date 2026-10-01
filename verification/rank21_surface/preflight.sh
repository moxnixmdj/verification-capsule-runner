set -euo pipefail
CTX=/tmp/rank21ctx
mkdir -p "$CTX/data"
BASE=https://raw.githubusercontent.com/harbor-framework/terminal-bench/452bf305c6daa62fc59061d22133a7cbc7c1572e/tasks/foodstuff-beta-activity/environment
curl -LfsS "$BASE/Dockerfile" -o "$CTX/Dockerfile"
curl -LfsS "$BASE/data/measurement%20data.xls" -o "$CTX/data/measurement data.xls"
curl -LfsS "$BASE/data/sample.xls" -o "$CTX/data/sample.xls"
curl -LfsS "$BASE/data/Sr-90_tables.pdf" -o "$CTX/data/Sr-90_tables.pdf"
test "$(stat -c%s "$CTX/data/measurement data.xls")" = 22528
test "$(stat -c%s "$CTX/data/sample.xls")" = 23040
test "$(stat -c%s "$CTX/data/Sr-90_tables.pdf")" = 105291
docker build -t rank21-preflight "$CTX"
docker run --rm rank21-preflight sh -lc '
set -eu
python --version
test -r "/app/data/measurement data.xls"
test -r "/app/data/sample.xls"
test -r "/app/data/Sr-90_tables.pdf"
test -w /app
printf preflight > /app/.surface-preflight
rm /app/.surface-preflight
test ! -e /app/results.txt
command -v curl
command -v uv
'
docker image inspect rank21-preflight --format '{{json .Config}}' > rank21_surface_profile.json
