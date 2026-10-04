#!/usr/bin/env bash
set -euo pipefail
: "${GITHUB_API_URL:?}" "${GITHUB_REPOSITORY:?}" "${GITHUB_SHA:?}" "${GH_TOKEN:?}"
name="shadow-atomic-v2-verifier/${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}"
full="refs/heads/${name}"
api="${GITHUB_API_URL}/repos/${GITHUB_REPOSITORY}/git/refs"
body1="$(mktemp)"; body2="$(mktemp)"
cleanup(){ curl -sS -o /dev/null -X DELETE -H "Authorization: Bearer ${GH_TOKEN}" -H "Accept: application/vnd.github+json" "${GITHUB_API_URL}/repos/${GITHUB_REPOSITORY}/git/refs/heads/${name}" || true; }
trap cleanup EXIT
payload=$(printf '{"ref":"%s","sha":"%s"}' "${full}" "${GITHUB_SHA}")
s1=$(curl -sS -o "${body1}" -w "%{http_code}" -X POST -H "Authorization: Bearer ${GH_TOKEN}" -H "Accept: application/vnd.github+json" -H "Content-Type: application/json" "${api}" -d "${payload}")
[[ "${s1}" == "201" ]] || { echo "first create failed: ${s1}"; cat "${body1}"; exit 1; }
s2=$(curl -sS -o "${body2}" -w "%{http_code}" -X POST -H "Authorization: Bearer ${GH_TOKEN}" -H "Accept: application/vnd.github+json" -H "Content-Type: application/json" "${api}" -d "${payload}")
[[ "${s2}" == "422" ]] || { echo "duplicate create did not fail closed: ${s2}"; cat "${body2}"; exit 1; }
grep -q "Reference already exists" "${body2}" || { echo "wrong duplicate failure"; cat "${body2}"; exit 1; }
echo '{"status":"PASS","first_create":201,"duplicate_create":422,"terminal_cases_consumed":0}'
