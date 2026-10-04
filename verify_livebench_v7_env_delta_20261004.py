#!/usr/bin/env python3
from __future__ import annotations
import hashlib,importlib.util,pathlib,tempfile
ROOT=pathlib.Path(__file__).resolve().parent
SUB=ROOT/"subject/livebench_v7_env_delta_20261004"
OLD=SUB/"old.py"; NEW=SUB/"new.py"; CLS=SUB/"livebench_v7_sanitized_classifier.py"; BASE=SUB/"execute_livebench_if_replay72_v4_candidate.py"
EXPECTED_OLD="55d4b961f58dc45c1513f9c9282a63773444773d"
EXPECTED_NEW="55d4b961f58dc45c1513f9c9282a63773444773d"
EXPECTED_CLS="44df7313c83914204299953dda81900fae85ab68"
EXPECTED_BASE="2a57ce896ddbd6819246aab8b44d17a00f36b61e"
def blob(p):
 d=p.read_bytes();return hashlib.sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()
assert blob(OLD)==EXPECTED_OLD=="e9a5a5937b19e76bf04444c288e3a75113874ed7"
assert blob(NEW)==EXPECTED_NEW=="55d4b961f58dc45c1513f9c9282a63773444773d"
assert blob(CLS)==EXPECTED_CLS=="44df7313c83914204299953dda81900fae85ab68"
assert blob(BASE)==EXPECTED_BASE=="2a57ce896ddbd6819246aab8b44d17a00f36b61e"
old=OLD.read_text(); new=NEW.read_text()
old_fragment='''        # Point-of-use zero-case template build. No terminal dataset read yet.
        template=build_diagnostic_template(base,mod)
'''
new_fragment='''        # Recreate the exact V6 pre-case dependency environment before any terminal dataset read.
        # This prevents the diagnostic from manufacturing new runtime exits that were absent in V6.
        mod.install_scorer_deps()
        mod.prepare_nltk(base)
        template=build_diagnostic_template(base,mod)
'''
assert old_fragment in old
assert old.replace(old_fragment,new_fragment)==new
# The only semantic delta is restoration of the V6 pre-case environment.
assert new.count("mod.install_scorer_deps()")==1
assert new.count("mod.prepare_nltk(base)")==1
assert new.index("mod.install_scorer_deps()") < new.index("template=build_diagnostic_template(base,mod)")
assert new.index("mod.prepare_nltk(base)") < new.index("template=build_diagnostic_template(base,mod)")
# Privacy and scope invariants from the already independently verified V7 remain unchanged.
for lit in [
 "REPLAY_LIMIT=72",
 'case_ids_emitted":False',
 'prompt_text_emitted":False',
 'response_text_emitted":False',
 'raw_exception_text_emitted":False',
 "for start in range(0,REPLAY_LIMIT,batch):",
]:
 assert lit in new,lit
for forbidden in ["print(q[","print(answer","print(str(exc)","for start in range(0,mod.POPULATION"]:
 assert forbidden not in new,forbidden
# Import succeeds and unauthorized execution remains fail-closed without touching terminal cases.
tmp=pathlib.Path(tempfile.mkdtemp())
(tmp/"diagnose_livebench_replay72_v7_sanitized.py").write_text(new)
(tmp/"livebench_v7_sanitized_classifier.py").write_text(CLS.read_text())
(tmp/"execute_livebench_if_replay72_v4_candidate.py").write_text(BASE.read_text())
spec=importlib.util.spec_from_file_location("diag",tmp/"diagnose_livebench_replay72_v7_sanitized.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
assert m.REPLAY_LIMIT==72
try:
 m.main(authorized=False,activation_blob=None)
 raise AssertionError("unauthorized execution accepted")
except SystemExit as exc:
 assert "VERIFIED_V7_DIAGNOSTIC_LAUNCHER_REQUIRED" in str(exc)
print('{"status":"INDEPENDENT_PUBLIC_RUNNER_PASS__V7_ENVIRONMENT_EQUIVALENCE_DELTA","old_blob":"'+EXPECTED_OLD+'","new_blob":"'+EXPECTED_NEW+'","base_executor_blob":"'+EXPECTED_BASE+'","classifier_blob":"'+EXPECTED_CLS+'","semantic_delta":"RESTORE_V6_PRECASE_SCORER_DEPS_AND_NLTK_BEFORE_TEMPLATE","terminal_cases_consumed":0,"new_case_authority":false,"acceptance_credit_delta":0}')
