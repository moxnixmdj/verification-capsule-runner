set -e
cat >/tmp/identity-probes.ts <<'TS'
import * as fs from 'node:fs'
import { submitLead } from '/app/src/lib/submitLead.ts'
async function main(){
  const out='/app/output'
  const reset=()=>fs.rmSync(out,{recursive:true,force:true})
  reset()
  const fb=await submitLead({
    platform:'facebook_lead_ads',leadgen_id:'FB-PHONE-ONLY',campaign_id:'CMP',
    consent:true,receivedAt:'2025-01-02T10:00:00Z',
    field_data:[
      {name:'full_name',values:['Phone Only']},
      {name:'phone_number',values:['+14045550115']},
      {name:'service_needed',values:['roof_repair']},
      {name:'city',values:['Atlanta']},
      {name:'state',values:['GA']}
    ]
  })
  console.log('PHONE_ONLY_FB='+JSON.stringify(fb))
  reset()
  const google=await submitLead({
    fullName:'No Gclid',email:'nogclid@example.com',phone:'+14045550116',
    service:'consultation',city:'Denver',state:'CO',consent:true,
    source:'google_ads',campaign:'c',utmMedium:'cpc',receivedAt:'2025-01-02T10:00:00Z'
  })
  console.log('GOOGLE_NO_GCLID='+JSON.stringify(google))
  reset()
}
main().catch(e=>{console.error(e);process.exit(1)})
TS
cd /app && ./node_modules/.bin/tsx /tmp/identity-probes.ts
