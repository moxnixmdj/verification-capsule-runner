set -e
cd /app
rm -rf output
npm run submit
printf '\n===== OUTPUT FILES =====\n'
find output -maxdepth 1 -type f -print | sort
printf '\n===== submission.json =====\n'
cat output/submission.json
printf '\n===== crm_leads.json =====\n'
cat output/crm_leads.json
printf '\n===== lead_sources.json =====\n'
cat output/lead_sources.json
printf '\n===== reconciliation.json =====\n'
cat output/reconciliation.json
