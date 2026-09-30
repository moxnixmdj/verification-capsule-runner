node -e "const n=require('next/server'); console.log('NEXT_AFTER_TYPE='+typeof n.after)"
for u in '/dispatch/summary?site=RNO1' '/dispatch/pick-batches?site=RNO1' '/dispatch/docks?site=RNO1' '/dispatch/forecast?site=RNO1' '/pick-batches?site=RNO1' '/pick-batches/labor?site=RNO1' '/inventory/holds?site=RNO1' '/inventory/replenishment?site=RNO1' '/shipments/carriers?site=RNO1' '/shipments/dock-windows?site=RNO1' '/exceptions/list?site=RNO1'; do
  printf '%s ' "$u"
  curl -sS -o /dev/null -w '%{time_total}\n' "http://127.0.0.1:4100$u"
done
