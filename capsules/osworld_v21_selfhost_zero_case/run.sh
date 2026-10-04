#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
ROOT="$PWD"
RESULT="$ROOT/osworld-selfhost-result.json"
WEB_OK=false
GITLAB_OK=false
WEB_ROUTE_COUNT=0
WEB_RUNNING=0
GITLAB_API_USER=""

cleanup() {
  set +e
  if [ -d "$ROOT/web" ]; then (cd "$ROOT/web" && docker compose down -v --remove-orphans >/dev/null 2>&1); fi
  if [ -d "$ROOT/gitlab" ]; then (cd "$ROOT/gitlab" && docker compose down -v --remove-orphans >/dev/null 2>&1); fi
}
trap cleanup EXIT

# Exact OSWorld-web v2.1 source and pinned submodules.
git clone --branch osworld-v2.1 https://github.com/Task-Web/OSWorld-web.git web
cd web
test "$(git rev-parse HEAD)" = "60c89fe6a8ed934668619d8d26132848239eb8ee"
sed -i 's#git@github.com:#https://github.com/#g' .gitmodules
git submodule sync --recursive
git submodule update --init --recursive
export HOST_SUFFIX=localhost
export CADDY_SCHEME=http://
docker compose config --format json > "$ROOT/web-compose.json"
docker compose up -d

# Give app stacks a bounded startup window.
deadline=$((SECONDS+480))
while (( SECONDS < deadline )); do
  total="$(docker compose config --services | wc -l | tr -d ' ')"
  running="$(docker compose ps --status running --services | wc -l | tr -d ' ')"
  WEB_RUNNING="$running"
  if [ "$running" -ge "$total" ]; then break; fi
  sleep 10
done

# Derive every Caddy host route from the resolved exact compose file.
python3 - "$ROOT/web-compose.json" "$ROOT/web-routes.txt" <<'PY'
import json,re,sys
d=json.load(open(sys.argv[1]))
hosts=set()
for svc in d.get("services",{}).values():
    labels=svc.get("labels") or {}
    if isinstance(labels,list):
        pairs={}
        for x in labels:
            if "=" in x:
                k,v=x.split("=",1); pairs[k]=v
        labels=pairs
    if isinstance(labels,dict):
        for k,v in labels.items():
            if k=="caddy" or str(k).startswith("caddy_"):
                for h in re.findall(r"https?://([^/\s,]+)",str(v)):
                    if "{" not in h and "}" not in h:
                        hosts.add(h)
open(sys.argv[2],"w").write("\n".join(sorted(hosts))+"\n")
PY
WEB_ROUTE_COUNT="$(grep -c . "$ROOT/web-routes.txt" || true)"
test "$WEB_ROUTE_COUNT" -gt 0

# Each configured route must return a non-5xx HTTP response through Caddy.
while IFS= read -r host; do
  [ -n "$host" ] || continue
  code="000"
  for _ in $(seq 1 24); do
    code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 10 --resolve "$host:80:127.0.0.1" "http://$host/" || true)"
    if [[ "$code" =~ ^[1-4][0-9][0-9]$ ]]; then break; fi
    sleep 5
  done
  if ! [[ "$code" =~ ^[1-4][0-9][0-9]$ ]]; then
    echo "WEB_ROUTE_FAILED:$host:$code"
    docker compose ps -a
    exit 21
  fi
done < "$ROOT/web-routes.txt"
WEB_OK=true
docker compose ps -a
docker compose down -v --remove-orphans
cd "$ROOT"

# Exact diagnostic Task-Web/gitlab state; release contract is functional, not revision-pinned.
git clone https://github.com/Task-Web/gitlab.git gitlab
cd gitlab
git checkout 8655d651722f4254e59e813de9f68a6732ea525c
test "$(git rev-parse HEAD)" = "8655d651722f4254e59e813de9f68a6732ea525c"
export GITLAB_URL=http://localhost
export GITLAB_PRIVATE_TOKEN="$(python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(36))
PY
)"
docker compose up -d

deadline=$((SECONDS+720))
while (( SECONDS < deadline )); do
  init_state="$(docker inspect -f '{{.State.Status}} {{.State.ExitCode}}' gitlab-init-token 2>/dev/null || true)"
  if [ "$init_state" = "exited 0" ]; then break; fi
  if [[ "$init_state" == exited* ]] && [ "$init_state" != "exited 0" ]; then
    docker logs --tail=200 gitlab-init-token || true
    exit 31
  fi
  sleep 15
done
test "$(docker inspect -f '{{.State.Status}} {{.State.ExitCode}}' gitlab-init-token)" = "exited 0"

curl -fsS --max-time 30 "$GITLAB_URL/users/sign_in" >/dev/null
GITLAB_API_USER="$(curl -fsS --max-time 30 --header "PRIVATE-TOKEN: $GITLAB_PRIVATE_TOKEN" "$GITLAB_URL/api/v4/user" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("username",""))')"
test "$GITLAB_API_USER" = "root"
GITLAB_OK=true
docker compose ps -a

python3 - "$RESULT" "$WEB_OK" "$WEB_ROUTE_COUNT" "$WEB_RUNNING" "$GITLAB_OK" "$GITLAB_API_USER" <<'PY'
import json,sys
out={
 "schema":"PROJECT_BRAIN_OSWORLD_V21_SELFHOST_ZERO_CASE_RESULT_V1",
 "website_exact_source_commit":"60c89fe6a8ed934668619d8d26132848239eb8ee",
 "website_stack_reachable":sys.argv[2]=="true",
 "website_route_count":int(sys.argv[3]),
 "website_running_service_count_at_probe":int(sys.argv[4]),
 "gitlab_diagnostic_source_commit":"8655d651722f4254e59e813de9f68a6732ea525c",
 "gitlab_reachable":sys.argv[5]=="true",
 "gitlab_api_token_valid":sys.argv[6]=="root",
 "gitlab_authenticated_user":sys.argv[6],
 "gated_assets_access_proved":False,
 "terminal_cases_consumed":0,
 "brain_score_proved":False,
 "end_to_end_protocol_equivalence_proved":False,
 "incremental_spend_usd":0,
}
open(sys.argv[1],"w").write(json.dumps(out,sort_keys=True)+"\n")
print(json.dumps(out,sort_keys=True))
PY
