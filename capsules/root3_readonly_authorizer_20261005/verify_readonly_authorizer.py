from __future__ import annotations

from canonical.runtime import root3_subprocess_mediator_v2 as mediator
from canonical.runtime.root3_read_only_current_authorizer_v1 import authorize


def require(cond, label):
    if not cond:
        raise AssertionError(label)


def req(callsite, argv):
    return mediator._request(
        callsite["process_api"],
        (argv,),
        {"capture_output": True, "text": True},
        callsite,
    )


readonly = {
    "module_path": "canonical/runtime/bound_capabilities/jq_query.py",
    "lineno": 41,
    "process_api": "subprocess.run",
    "function": "query_json",
    "effect_class": "READ_ONLY_DECLARED_QUERY",
    "registry_site_count": 18,
    "runtime_join": "EXACT_PATH_LINE_API",
}
arbitrary = {
    "module_path": "canonical/runtime/astra_runtime.py",
    "lineno": 325,
    "process_api": "subprocess.run",
    "function": "run_shell",
    "effect_class": "ARBITRARY_COMMAND_EXECUTION",
    "registry_site_count": 18,
    "runtime_join": "EXACT_PATH_LINE_API",
}

good = authorize(req(readonly, ["jq", ".", "/tmp/input.json"]))
require(good["allowed"] is True, "READ_ONLY_MUST_ALLOW")
require(len(good["authorization_sha256"]) == 64, "ALLOW_DIGEST_REQUIRED")

bad_class = authorize(req(arbitrary, ["/bin/echo", "x"]))
require(bad_class["allowed"] is False, "ARBITRARY_COMMAND_MUST_DENY")

tampered = req(readonly, ["jq", ".", "/tmp/input.json"])
tampered["command"] = ["jq", "-r", ".", "/tmp/input.json"]
require(authorize(tampered)["allowed"] is False, "TAMPERED_REQUEST_MUST_DENY")

drifted = dict(readonly)
drifted["lineno"] = 999999
require(authorize(req(drifted, ["jq", ".", "/tmp/input.json"]))["allowed"] is False, "DRIFTED_CALLSITE_MUST_DENY")

print("PASS: independent Root3 read-only current authorizer checks")
