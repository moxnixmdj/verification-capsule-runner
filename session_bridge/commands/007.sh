node <<'JS'
const urls = [
'/dispatch/summary?site=RNO1',
'/dispatch/pick-batches?site=RNO1',
'/dispatch/docks?site=RNO1',
'/dispatch/forecast?site=RNO1',
'/pick-batches?site=RNO1',
'/pick-batches/labor?site=RNO1',
'/inventory/holds?site=RNO1',
'/inventory/replenishment?site=RNO1',
'/shipments/carriers?site=RNO1',
'/shipments/dock-windows?site=RNO1',
'/exceptions/list?site=RNO1'
];
(async()=>{
  for (const u of urls) {
    const t=performance.now();
    const r=await fetch('http://127.0.0.1:4100'+u);
    await r.arrayBuffer();
    console.log(u, (performance.now()-t).toFixed(1)+'ms', r.status);
  }
})().catch(e=>{console.error(e);process.exit(1)})
JS
