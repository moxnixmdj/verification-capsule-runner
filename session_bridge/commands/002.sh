set -euo pipefail
date -u
supervisorctl -c /app/supervisor.conf status || true
printf '\n--- worker stdout ---\n'
tail -n 80 /tmp/worker-00.log 2>/dev/null || true
printf '\n--- worker stderr ---\n'
tail -n 80 /tmp/worker-00.err 2>/dev/null || true
printf '\n--- env ---\n'
env | grep -E '^(KAFKA|CUSTOMER)' | sort || true
printf '\n--- kafka metadata ---\n'
cd /app/src
python3 - <<'PY'
from confluent_kafka import Consumer, TopicPartition
from worker.config import KAFKA_BROKERS,KAFKA_TOPIC,KAFKA_CONSUMER_GROUP
c=Consumer({'bootstrap.servers':KAFKA_BROKERS,'group.id':KAFKA_CONSUMER_GROUP,'enable.auto.commit':False})
m=c.list_topics(timeout=10)
print('topics', sorted(m.topics))
tm=m.topics[KAFKA_TOPIC]
parts=sorted(tm.partitions)
print('parts', parts)
for p in parts:
    low,high=c.get_watermark_offsets(TopicPartition(KAFKA_TOPIC,p),timeout=10,cached=False)
    print('watermark',p,low,high)
print('committed',[(tp.partition,tp.offset) for tp in c.committed([TopicPartition(KAFKA_TOPIC,p) for p in parts],timeout=10)])
c.close()
PY