set -e
cd /app/src
python3 - <<'PY'
from confluent_kafka import TopicPartition, Consumer
tp=TopicPartition("x",0,1)
print("TopicPartition repr",tp)
print("TopicPartition attrs",[a for a in dir(tp) if not a.startswith("_")])
print("metadata attr",getattr(tp,"metadata",None))
print("Consumer.commit doc",Consumer.commit.__doc__)
print("Consumer.committed doc",Consumer.committed.__doc__)
print("Consumer.on_commit",getattr(Consumer,"on_commit",None))
PY
