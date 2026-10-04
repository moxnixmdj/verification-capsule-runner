#!/usr/bin/env bash
set -euo pipefail

: "${GITHUB_API_URL:?}"
: "${GITHUB_REPOSITORY:?}"
: "${GITHUB_SHA:?}"
: "${GH_TOKEN:?}"

ref_name="shadow-claim-verifier/${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}"
full_ref="refs/heads/${ref_name}"
api="${GITHUB_API_URL}/repos/${GITHUB_REPOSITORY}/git/refs"

first_body="$(mktemp)"
second_body="$(mktemp)"
cleanup_body="$(mktemp)"

cleanup() {
  curl -sS -o "${cleanup_body}" -w "%{http_code}" \
    -X DELETE \
    -H "Authorization: Bearer ${GH_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    "${GITHUB_API_URL}/repos/${GITHUB_REPOSITORY}/git/refs/heads/${ref_name}" >/tmp/shadow_cleanup_status || true
}
trap cleanup EXIT

payload=$(printf '{"ref":"%s","sha":"%s"}' "${full_ref}" "${GITHUB_SHA}")

first_status=$(curl -sS -o "${first_body}" -w "%{http_code}" \
  -X POST \
  -H "Authorization: Bearer ${GH_TOKEN}" \
  -H "Accept: application/vnd.github+json" \
  -H "Content-Type: application/json" \
  "${api}" \
  -d "${payload}")

if [[ "${first_status}" != "201" ]]; then
  echo "first ref create failed: status=${first_status}"
  cat "${first_body}"
  exit 1
fi

second_status=$(curl -sS -o "${second_body}" -w "%{http_code}" \
  -X POST \
  -H "Authorization: Bearer ${GH_TOKEN}" \
  -H "Accept: application/vnd.github+json" \
  -H "Content-Type: application/json" \
  "${api}" \
  -d "${payload}")

if [[ "${second_status}" != "422" ]]; then
  echo "duplicate ref create did not fail closed: status=${second_status}"
  cat "${second_body}"
  exit 1
fi

if ! grep -q "Reference already exists" "${second_body}"; then
  echo "duplicate failure was not the required existing-reference condition"
  cat "${second_body}"
  exit 1
fi

echo '{"status":"PASS","first_create_status":201,"duplicate_create_status":422,"duplicate_reason":"Reference already exists","terminal_cases_consumed":0}'
