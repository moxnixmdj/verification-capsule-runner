set -euo pipefail
TB=/tmp/tb-rank21-verifier
rm -rf "$TB"
git clone --filter=blob:none --no-checkout https://github.com/harbor-framework/terminal-bench.git "$TB"
cd "$TB"
git sparse-checkout init --no-cone
printf 'tasks/foodstuff-beta-activity/*\n' > .git/info/sparse-checkout
git checkout --detach 452bf305c6daa62fc59061d22133a7cbc7c1572e
TASK="$TB/tasks/foodstuff-beta-activity"
cd "$GITHUB_WORKSPACE"
docker build -t rank21-hidden-verifier "$TASK/tests"
docker rm -f rank21-hidden-verifier >/dev/null 2>&1 || true
docker create --name rank21-hidden-verifier --user 0 --entrypoint /bin/sh rank21-hidden-verifier -lc 'trap : TERM INT; while :; do sleep 3600; done'
docker start rank21-hidden-verifier
docker exec rank21-hidden-verifier mkdir -p /app /logs/verifier /logs/agent
docker cp verification/rank21_verify_only/results.txt rank21-hidden-verifier:/app/results.txt
set +e
docker exec rank21-hidden-verifier /bin/sh -lc 'if [ -d /app ]; then cd /app; else cd /; fi; /bin/bash /tests/test.sh' > /tmp/verifier_stdout.txt 2> /tmp/verifier_stderr.txt
EC=$?
set -e
printf '%s' "$EC" > /tmp/verifier_exit.txt
: > /tmp/verifier_reward.txt
if docker exec rank21-hidden-verifier test -f /logs/verifier/reward.txt; then docker exec rank21-hidden-verifier cat /logs/verifier/reward.txt > /tmp/verifier_reward.txt; fi
if [ ! -s /tmp/verifier_reward.txt ] && docker exec rank21-hidden-verifier test -f /logs/verifier/reward.json; then docker exec rank21-hidden-verifier cat /logs/verifier/reward.json > /tmp/verifier_reward.txt; fi
CTRF=""
if docker exec rank21-hidden-verifier test -f /logs/verifier/ctrf.json; then docker cp rank21-hidden-verifier:/logs/verifier/ctrf.json rank21_verifier_ctrf.json; CTRF="rank21_verifier_ctrf.json"; fi
python - <<'PY'
import json
from pathlib import Path
out={
 "schema":"BRAIN_RANK21_FROZEN_OUTPUT_VERIFIER_ONLY_V1",
 "task":"foodstuff-beta-activity",
 "session_id":"foodstuff-beta-activity-20261001-stagec-v1",
 "candidate_source":"IMMUTABLE_OBSERVATION_000_FROZEN_OUTPUT__NO_RECALCULATION_NO_REPAIR",
 "verifier_invocations":1,
 "verifier_exit_code":int(Path("/tmp/verifier_exit.txt").read_text()),
 "reward":Path("/tmp/verifier_reward.txt").read_text(errors="replace").strip(),
 "stdout":Path("/tmp/verifier_stdout.txt").read_text(errors="replace")[-120000:],
 "stderr":Path("/tmp/verifier_stderr.txt").read_text(errors="replace")[-120000:],
 "ctrf_path":"rank21_verifier_ctrf.json" if Path("rank21_verifier_ctrf.json").exists() else None,
}
Path("rank21_final_verification.json").write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
PY
