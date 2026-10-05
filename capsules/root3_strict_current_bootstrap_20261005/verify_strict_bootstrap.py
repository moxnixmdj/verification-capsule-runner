from __future__ import annotations
import subprocess
from unittest.mock import patch

from canonical.runtime import root3_strict_current_bootstrap_v1 as b
from canonical.runtime import root3_subprocess_mediator_v2 as m


def require(x, label):
    if not x:
        raise AssertionError(label)


def allow(_request):
    return {"allowed": True, "authorization_sha256": "a" * 64}


fake_executor=lambda context: context
with patch.object(b.read_only, "make_executor", return_value=fake_executor):
    out=b.install_current(allow, authority_id="PUBLIC_VERIFY")
require(out["process_site_count"] == 18, "EXACT_CURRENT_18_SITE_BIND")
require(out["bound_effect_classes"] == ["READ_ONLY_DECLARED_QUERY"], "ONLY_READ_ONLY_BOUND")
require(set(out["denied_effect_classes"]) == set(b.CLASSES)-{"READ_ONLY_DECLARED_QUERY"}, "OTHER_CLASSES_DENIED")
require(subprocess.run is not m._ORIGINAL_RUN and subprocess.Popen is not m._ORIGINAL_POPEN, "GLOBAL_GUARDS_ACTIVE")
m.uninstall()

seen=[]
def counting(req):
    seen.append(req)
    return {"allowed": True, "authorization_sha256": "a" * 64}
with patch.object(b.read_only, "make_executor", return_value=fake_executor):
    b.install_current(counting, authority_id="PUBLIC_VERIFY")
try:
    subprocess.run(["must", "not", "execute"])
    raise AssertionError("UNREGISTERED_PROCESS_UNEXPECTEDLY_EXECUTED")
except m.ProcessEffectDenied as exc:
    require("SUBPROCESS_CALLSITE_CLASSIFICATION_DENIED" in str(exc), "WRONG_FAIL_CLOSED_REASON")
require(seen == [], "UNREGISTERED_CALL_REACHED_AUTHORIZER")
m.uninstall()
print("PASS: strict current Root3 bootstrap independent checks")
