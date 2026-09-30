"""At-most-one dispatch admission for already-authorized, frozen executions."""
from __future__ import annotations
import dataclasses, hashlib, json, re, sqlite3, uuid
from contextlib import closing
from datetime import datetime, timezone
from typing import Callable, Protocol

class AdmissionDenied(RuntimeError): pass
class DispatchUncertain(RuntimeError): pass

class AtomicStore(Protocol):
    def create(self, key: str, value: dict) -> bool: ...
    def read(self, key: str) -> dict | None: ...

def _json(value: dict) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)

class SQLiteStore:
    def __init__(self, path: str):
        self.path=path
        with closing(sqlite3.connect(path, timeout=30)) as db:
            db.execute("CREATE TABLE IF NOT EXISTS immutable_records(key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            db.commit()
    def create(self,key,value):
        encoded=_json(value)
        with closing(sqlite3.connect(self.path, timeout=30)) as db:
            db.execute("PRAGMA synchronous=FULL")
            r=db.execute("INSERT OR IGNORE INTO immutable_records(key,value) VALUES (?,?)",(key,encoded))
            db.commit(); return r.rowcount==1
    def read(self,key):
        with closing(sqlite3.connect(self.path, timeout=30)) as db:
            row=db.execute("SELECT value FROM immutable_records WHERE key=?",(key,)).fetchone()
        if row is None: return None
        value=json.loads(row[0])
        if not isinstance(value,dict): raise AdmissionDenied("MALFORMED_LEDGER_RECORD")
        return value

@dataclasses.dataclass(frozen=True)
class FrozenExecution:
    gate_id:str; problem_sha256:str; task_sha256:str; runtime_sha256:str
    canonical_base:str; authorization_sha256:str
    def validate(self):
        _nonempty(self.gate_id,"gate_id")
        for f in ("problem_sha256","task_sha256","runtime_sha256","authorization_sha256"):
            _digest(getattr(self,f),f,64)
        _digest(self.canonical_base,"canonical_base",40)

def _nonempty(value,label):
    if not isinstance(value,str) or not value.strip() or len(value)>4096:
        raise ValueError("INVALID_"+label.upper())
def _digest(value,label,length):
    if not isinstance(value,str) or not re.fullmatch("[0-9a-f]{"+str(length)+"}",value):
        raise ValueError("INVALID_"+label.upper())
def _gate_key(gate_id):
    _nonempty(gate_id,"gate_id")
    return "gates/"+hashlib.sha256(gate_id.encode()).hexdigest()+".json"
def _attempt_key(kind,attempt_id):
    if not isinstance(attempt_id,str) or not re.fullmatch("[0-9a-f]{32}",attempt_id):
        raise AdmissionDenied("INVALID_ATTEMPT_ID")
    return kind+"/"+attempt_id+".json"

def _create_required(store,key,record):
    try: created=store.create(key,record)
    except Exception as exc: raise AdmissionDenied("RESERVATION_UNCONFIRMED_NO_DISPATCH") from exc
    if created is not True: raise AdmissionDenied("ALREADY_RESERVED_OR_CREATE_NOT_CONFIRMED")

def dispatch_once(store:AtomicStore,spec:FrozenExecution,owner_id:str,dispatch:Callable[[str],dict])->dict:
    spec.validate(); _nonempty(owner_id,"owner_id")
    if not callable(dispatch): raise ValueError("DISPATCH_MUST_BE_CALLABLE")
    attempt_id=uuid.uuid4().hex
    reservation={"schema":"BRAIN_DISPATCH_RESERVATION_V1","attempt_id":attempt_id,
      "owner_id":owner_id,"frozen":dataclasses.asdict(spec),
      "reserved_at":datetime.now(timezone.utc).isoformat()}
    _create_required(store,_gate_key(spec.gate_id),reservation)
    _create_required(store,"problems/"+spec.problem_sha256+".json",reservation)
    try:
        receipt=dispatch(attempt_id)
        if not isinstance(receipt,dict): raise ValueError("DISPATCH_RECEIPT_REQUIRED")
        _nonempty(receipt.get("run_ref"),"run_ref")
        ack={"schema":"BRAIN_DISPATCH_ACK_V1","attempt_id":attempt_id,
             "gate_id":spec.gate_id,"run_ref":receipt["run_ref"]}
        if store.create(_attempt_key("dispatches",attempt_id),ack) is not True:
            raise ValueError("DISPATCH_ACK_NOT_PERSISTED")
    except Exception as exc:
        raise DispatchUncertain("DISPATCH_OR_ACK_UNCERTAIN:"+attempt_id) from exc
    return {"status":"DISPATCH_ACKNOWLEDGED","attempt_id":attempt_id,
            "run_ref":receipt["run_ref"],"execution_count":None}

def _reservation(store,gate_id):
    record=store.read(_gate_key(gate_id))
    if record is None: return None
    try:
        spec=FrozenExecution(**record["frozen"]); spec.validate()
        if spec.gate_id!=gate_id or record["schema"]!="BRAIN_DISPATCH_RESERVATION_V1":
            raise ValueError("reservation mismatch")
        _attempt_key("dispatches",record["attempt_id"]); _nonempty(record["owner_id"],"owner_id")
        _nonempty(record["reserved_at"],"reserved_at")
    except (KeyError,TypeError,ValueError) as exc:
        raise AdmissionDenied("MALFORMED_RESERVATION") from exc
    return record

def _validate_receipt(receipt):
    if not isinstance(receipt,dict): raise ValueError("TERMINAL_RECEIPT_REQUIRED")
    count,outcome=receipt.get("execution_count"),receipt.get("outcome")
    if type(count) is not int or count not in (0,1): raise ValueError("EXECUTION_COUNT_MUST_BE_ZERO_OR_ONE")
    if outcome not in ("SUCCEEDED","FAILED","NOT_STARTED") or (outcome=="NOT_STARTED")!=(count==0):
        raise ValueError("OUTCOME_COUNT_MISMATCH")
    _nonempty(receipt.get("run_ref"),"run_ref"); _digest(receipt.get("evidence_sha256"),"evidence_sha256",64)

def _require_complete_reservation(store,reservation):
    p=store.read("problems/"+reservation["frozen"]["problem_sha256"]+".json")
    if p!=reservation: raise AdmissionDenied("PROBLEM_RESERVATION_MISSING_OR_CONFLICTING")

def _acknowledgement(store,gate_id,attempt_id):
    ack=store.read(_attempt_key("dispatches",attempt_id))
    if ack is None:return None
    try:
        if ack["schema"]!="BRAIN_DISPATCH_ACK_V1" or ack["gate_id"]!=gate_id or ack["attempt_id"]!=attempt_id:
            raise ValueError("ack binding mismatch")
        _nonempty(ack["run_ref"],"run_ref")
    except (KeyError,TypeError,ValueError) as exc:
        raise AdmissionDenied("MALFORMED_OR_MISMATCHED_ACK") from exc
    return ack

def _validate_terminal(terminal,gate_id,attempt_id,ack):
    try:
        if terminal["schema"]!="BRAIN_EXECUTION_TERMINAL_V1" or terminal["gate_id"]!=gate_id or terminal["attempt_id"]!=attempt_id:
            raise ValueError("terminal binding mismatch")
        receipt=terminal["receipt"]; _validate_receipt(receipt)
        if ack is not None and ack["run_ref"]!=receipt["run_ref"]: raise ValueError("terminal run mismatch")
    except (KeyError,TypeError,ValueError) as exc:
        raise AdmissionDenied("MALFORMED_OR_MISMATCHED_TERMINAL") from exc
    return receipt

def reconcile_terminal(store,gate_id,attempt_id,receipt):
    _validate_receipt(receipt); reservation=_reservation(store,gate_id)
    if reservation is None or reservation["attempt_id"]!=attempt_id:
        raise AdmissionDenied("TERMINAL_ATTEMPT_MISMATCH")
    _require_complete_reservation(store,reservation); ack=_acknowledgement(store,gate_id,attempt_id)
    terminal={"schema":"BRAIN_EXECUTION_TERMINAL_V1","gate_id":gate_id,"attempt_id":attempt_id,"receipt":dict(receipt)}
    _validate_terminal(terminal,gate_id,attempt_id,ack); key=_attempt_key("terminals",attempt_id)
    try: created=store.create(key,terminal)
    except Exception as exc: raise AdmissionDenied("TERMINAL_WRITE_UNCONFIRMED") from exc
    if created is not True:
        existing=store.read(key); _validate_terminal(existing,gate_id,attempt_id,ack)
        if _json(existing)!=_json(terminal): raise AdmissionDenied("CONFLICTING_IMMUTABLE_TERMINAL")
    return terminal

def _create_or_match(store,key,record):
    try: created=store.create(key,record)
    except Exception as exc: raise AdmissionDenied("HISTORICAL_SEED_WRITE_UNCONFIRMED") from exc
    if created is True:return
    existing=store.read(key)
    if existing is None or _json(existing)!=_json(record): raise AdmissionDenied("HISTORICAL_SEED_CONFLICT")

def seed_historical_execution(store,spec,receipt,source_ref,reviewer_id):
    spec.validate(); _validate_receipt(receipt); _nonempty(source_ref,"source_ref"); _nonempty(reviewer_id,"reviewer_id")
    if receipt["execution_count"]!=1 or receipt["outcome"]=="NOT_STARTED":
        raise ValueError("HISTORICAL_SEED_REQUIRES_CONSUMED_EXECUTION")
    material=_json({"gate_id":spec.gate_id,"problem_sha256":spec.problem_sha256,
      "run_ref":receipt["run_ref"],"evidence_sha256":receipt["evidence_sha256"],"source_ref":source_ref})
    attempt_id=hashlib.sha256(("historical:"+material).encode()).hexdigest()[:32]
    reservation={"schema":"BRAIN_DISPATCH_RESERVATION_V1","attempt_id":attempt_id,
      "owner_id":"historical-reconciliation:"+reviewer_id,"frozen":dataclasses.asdict(spec),
      "reserved_at":"HISTORICAL_BEFORE_GUARD","historical_source_ref":source_ref}
    _create_or_match(store,_gate_key(spec.gate_id),reservation)
    _create_or_match(store,"problems/"+spec.problem_sha256+".json",reservation)
    terminal={"schema":"BRAIN_EXECUTION_TERMINAL_V1","gate_id":spec.gate_id,"attempt_id":attempt_id,
              "receipt":dict(receipt),"historical_source_ref":source_ref}
    _validate_terminal(terminal,spec.gate_id,attempt_id,None)
    _create_or_match(store,_attempt_key("terminals",attempt_id),terminal)
    return terminal

def inspect_execution(store,gate_id):
    reservation=_reservation(store,gate_id)
    if reservation is None:return {"status":"NO_RESERVATION_OBSERVED","execution_count":None}
    attempt_id=reservation["attempt_id"]; state={"status":"RESERVED_OR_DISPATCH_UNKNOWN","attempt_id":attempt_id,"execution_count":None}
    ack=_acknowledgement(store,gate_id,attempt_id); terminal=store.read(_attempt_key("terminals",attempt_id))
    if ack is not None or terminal is not None:_require_complete_reservation(store,reservation)
    if terminal is not None:
        receipt=_validate_terminal(terminal,gate_id,attempt_id,ack)
        state.update(status="RECONCILED_"+receipt["outcome"],execution_count=receipt["execution_count"],
                     run_ref=receipt["run_ref"],evidence_sha256=receipt["evidence_sha256"])
    elif ack is not None: state.update(status="DISPATCH_ACKNOWLEDGED",run_ref=ack["run_ref"])
    return state
