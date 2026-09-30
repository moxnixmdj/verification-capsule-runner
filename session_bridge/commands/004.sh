set -euo pipefail
cd /app/src
python3 - <<'PY'
import inspect
import confluent_kafka
from confluent_kafka import Producer, Consumer, TopicPartition
from confluent_kafka.admin import AdminClient, NewTopic
print('version', confluent_kafka.__version__)
for cls,name in [(Producer,'Producer'),(Consumer,'Consumer'),(AdminClient,'AdminClient'),(NewTopic,'NewTopic')]:
    print('\n###', name)
    for attr in ['init_transactions','begin_transaction','commit_transaction','abort_transaction','send_offsets_to_transaction','produce','flush','consumer_group_metadata','store_offsets','assign','seek','get_watermark_offsets','create_topics']:
        obj=getattr(cls,attr,None)
        if obj is not None:
            print(attr, getattr(obj,'__doc__','')[:1800])
PY
