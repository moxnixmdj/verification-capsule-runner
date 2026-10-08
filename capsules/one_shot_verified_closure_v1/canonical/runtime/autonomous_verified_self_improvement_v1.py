import json
from pathlib import Path
DEFAULT_STATE_PATH = Path(__file__).with_name("_state.json")
def load_state(path=DEFAULT_STATE_PATH):
    p=Path(path)
    if not p.exists():
        return {"observations":{},"failures":{},"episodes":{},"skills":{},"improvement_queue":{},"stats":{}}
    return json.loads(p.read_text(encoding="utf-8"))
