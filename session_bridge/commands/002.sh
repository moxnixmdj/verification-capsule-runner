set -e
echo '===== ENV ====='
env | sort | grep -E 'KAFKA|CUSTOMER|PYTHON|HOST' || true
echo '===== SUPERVISOR ====='
supervisorctl -c /app/supervisor.conf status || true
echo '===== WORKER LOGS ====='
for f in /tmp/worker-*.log /tmp/worker-*.err; do [ -f "$f" ] && { echo "=== $f ==="; tail -80 "$f"; }; done
echo '===== CUSTOMER PROBES ====='
python3 - <<'PY'
import httpx
for p in ['/','/health','/openapi.json','/docs']:
    try:
        r=httpx.get('http://customer:9000'+p,timeout=2)
        print(p,r.status_code,r.text[:2000])
    except Exception as e: print(p,'ERR',repr(e))
PY
echo '===== KAFKA METADATA / OFFSETS / SAMPLES ====='
cd /app/src
python3 - <<'PY'
from confluent_kafka import Consumer, TopicPartition
from worker.config import *
c=Consumer({'bootstrap.servers':KAFKA_BROKERS,'group.id':'brain-inspect','enable.auto.commit':False,'auto.offset.reset':'earliest'})
m=c.list_topics(KAFKA_TOPIC,timeout=5)
parts=sorted(m.topics[KAFKA_TOPIC].partitions)
print('partitions',parts)
for p in parts:
    tp=TopicPartition(KAFKA_TOPIC,p)
    print('wm',p,c.get_watermark_offsets(tp,timeout=5,cached=False))
print('committed',[(x.partition,x.offset) for x in c.committed([TopicPartition(KAFKA_TOPIC,p) for p in parts],timeout=5)])
for p in parts[:4]:
    lo,hi=c.get_watermark_offsets(TopicPartition(KAFKA_TOPIC,p),timeout=5,cached=False)
    for off in [lo,max(lo,hi-1)]:
        c.assign([TopicPartition(KAFKA_TOPIC,p,off)])
        msg=c.poll(3)
        if msg and not msg.error():
            print('sample',p,msg.offset(),'key=',msg.key(),'value=',msg.value()[:500])
c.close()
PY
