from __future__ import annotations
import hashlib, json

from automationbench.domains import get_domain_dataset

DOMAINS=["sales","marketing","operations","support","finance","hr"]
counts={}
slots=[]
for domain in DOMAINS:
    ds=get_domain_dataset(domain)
    n=len(ds)
    counts[domain]=n
    assert n==100, (domain,n)
    slots.extend(f"{domain}:{i:03d}" for i in range(n))

raw=json.dumps(sorted(slots),separators=(",",":"),ensure_ascii=False).encode("utf-8")
commitment=hashlib.sha256(raw).hexdigest()
assert len(slots)==600
assert commitment=="73fb894dd1679968f1a2c7805f2e51a65208b321579d614e47aa45756899a9b9"

verdict={
  "schema":"PROJECT_BRAIN_AUTOMATIONBENCH_PUBLIC_600_POPULATION_BINDING_V1",
  "upstream_commit":"4a8e1061254004d9dac807054eed33fad7d1ff14",
  "domain_counts":counts,
  "population_size":len(slots),
  "slot_id_rule":"DOMAIN_COLON_ZERO_PADDED_ZERO_BASED_ROW_INDEX",
  "population_commitment_sha256":commitment,
  "task_prompts_emitted":0,
  "expected_states_emitted":0,
  "terminal_results_observed":0,
  "incremental_spend_usd":0,
  "family_credit_delta":0,
}
open("AUTOMATIONBENCH_PUBLIC_600_POPULATION_BINDING_V1.json","w",encoding="utf-8").write(json.dumps(verdict,indent=2,sort_keys=True)+"\n")
print(json.dumps(verdict,sort_keys=True))
