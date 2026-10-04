#!/usr/bin/env python3
import livebench_generic_control_ir_v1 as m

cases=[
  ("if the value is valid, save the result, otherwise report failure","IF_ELSE",["save the result","report failure"]),
  ("for each item in the runtime collection, if the item is valid, process the item, otherwise skip the item","FOR_EACH",["process the item","skip the item"]),
  ("for every user, create one verified record","FOR_EACH",["create one verified record"]),
  ("repeat fetch the source no more than 4 times","BOUNDED_REPEAT",["fetch the source"]),
  ("up to 3 times, verify the artifact","BOUNDED_REPEAT",["verify the artifact"]),
]
for text,kind,leaves in cases:
    x=m.parse(text)
    assert x["kind"]==kind,(text,x)
    assert m.collect_leaves(x)==leaves,(text,m.collect_leaves(x))
    assert m.validate_fail_closed(x) is True
    stack=[x]
    while stack:
        n=stack.pop()
        assert n["execution_authority"] is False
        if n["kind"] in ("FOR_EACH","BOUNDED_REPEAT"):
            stack.append(n["body"])
        elif n["kind"]=="IF_ELSE":
            stack.extend([n["then"],n["else"]])

for bad in ("repeat forever","if condition then maybe"):
    try:
        m.parse(bad)
    except m.ControlParseError:
        pass
    else:
        raise AssertionError("MALFORMED_CONTROL_ACCEPTED:"+bad)

try:
    m.parse("repeat fetch the source up to 1000 times")
except m.ControlParseError as exc:
    assert "REPEAT_BOUND_OUT_OF_RANGE" in str(exc)
else:
    raise AssertionError("UNBOUNDED_CONTROL_ACCEPTED")

print("PASS:GENERIC_CONTROL_IR_SYNTHETIC_FAIL_CLOSED")
