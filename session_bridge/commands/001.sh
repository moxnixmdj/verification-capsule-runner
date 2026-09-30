python - <<'PY'
from pathlib import Path
files=[
"/app/package.json",
"/app/src/spec/lead_schema.json",
"/app/src/spec/lead_policy.json",
"/app/src/spec/business_calendar.json",
"/app/src/lib/payload.ts",
"/app/src/lib/submitLead.ts",
"/app/src/lib/tracking.ts",
"/app/src/lib/validation.ts",
"/app/src/components/LeadForm.tsx",
"/app/src/App.tsx",
"/app/src/scripts/submit.ts"
]
for f in files:
    print("\n===== "+f+" =====")
    print(Path(f).read_text())
PY
