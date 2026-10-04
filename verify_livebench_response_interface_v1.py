from __future__ import annotations
import ast, hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
FILES={
 "adapter":("capsules/root2_livebench_astra_adapter_v1/canonical/runtime/root2_livebench_if_astra_inference_adapter_v1.py","7e3885fa7a6e56df656c066e0a8f17cfa21424e7"),
 "astra":("canonical/runtime/astra_runtime.py","7f5d16b1db69cb620954bc778e0ba6e15e687b75"),
 "compiler":("canonical/runtime/goal_compiler.py","4b61fe911471854ec15c7900816f61e9e55f602e"),
 "planner":("canonical/runtime/capability_planner.py","64ff65cb184f50d3336326f33cccfcc0a53301a8"),
 "proposal":("canonical/runtime/capability_proposal_generators.py","71f2bbfda66a65d8d75e035b9ae073671ebd56e2"),
 "grounded":("canonical/runtime/bound_capabilities/grounded_executable_composition.py","8328e12804f64cab1c0d9509966cb1d2d8fb1f82"),
}
def blob(p):
 d=p.read_bytes(); return hashlib.sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()
def read(k):
 rel,exp=FILES[k]; p=ROOT/rel; assert p.is_file(),rel; assert blob(p)==exp,(k,blob(p),exp); return p.read_text()
def kv(d,key):
 for k,v in zip(d.keys,d.values):
  if isinstance(k,ast.Constant) and k.value==key:return v
 return None
def finish_literals(src):
 vals=set(); dynamic=[]
 for n in ast.walk(ast.parse(src)):
  if not isinstance(n,ast.Dict):continue
  typ=kv(n,"type")
  if isinstance(typ,ast.Constant) and typ.value=="finish":
   args=kv(n,"args"); sm=kv(args,"summary") if isinstance(args,ast.Dict) else None
   if isinstance(sm,ast.Constant) and isinstance(sm.value,str): vals.add(sm.value)
   else: dynamic.append("dynamic_finish")
  fs=kv(n,"finish_summary")
  if fs is not None:
   if isinstance(fs,ast.Constant) and isinstance(fs.value,str): vals.add(fs.value)
   else: dynamic.append("dynamic_finish_summary")
 return vals,dynamic

src={k:read(k) for k in FILES}
a=src["adapter"]
for x in [
 '"allow_optional_model_planner":False',
 'if allowed not in (None,[],()):',
 'answer=str(result.get("stdout") or result.get("final_summary") or "").strip()',
 'if result.get("cognition_dependency_class")!="MODEL_INDEPENDENT":',
]:
 assert x in a,x
for x in ['"controller_actions"','"capability_problem"','"capability_problem_proposal"','"capability_proposal_generator"']:
 assert x not in a,x

r=src["astra"]
for x in [
 'proposal_result=_run_verified_capability_proposal(step,mission,goal)',
 'capability_result=_run_capability_planned_goal(step, mission, goal)',
 'direct=_run_model_independent_goal(step, mission, goal)',
 'compiled=_compile_plain_goal(goal)',
 'compiled_after_acquisition=_compile_plain_goal(goal)',
 'acquired_result=_run_compiled_plain_goal(',
 'if not step.get("allow_optional_model_planner",False):',
 'return {"type":typ,"summary":str(args.get("summary",""))[:12000]}',
 'actions=step.get("controller_actions")',
 'problem=step.get("capability_problem")',
 'proposal=step.get("capability_problem_proposal")',
]:
 assert x in r,x

cv,cd=finish_literals(src["compiler"])
gv,gd=finish_literals(src["grounded"])
pv,pd=finish_literals(src["proposal"])
assert not cd and cv=={"PLAIN_GOAL_COMPLETE","COMPOUND_GOAL_COMPLETE"},(cv,cd)
assert not gd and gv=={"GROUNDED_CAPABILITY_COMPOSITION_COMPLETE"},(gv,gd)
assert not pd and pv=={"AUTO_VERIFIED_CAPABILITY_PROPOSAL_COMPLETE","AUTO_MULTI_VERIFIED_CAPABILITY_PROPOSAL_COMPLETE"},(pv,pd)
assert 'finish_summary = str(problem.get("finish_summary", "CAPABILITY_PLAN_COMPLETE")).strip()' in src["planner"]
assert '"args": {"summary": finish_summary}' in src["planner"]
actual=cv|gv
assert actual=={"PLAIN_GOAL_COMPLETE","COMPOUND_GOAL_COMPLETE","GROUNDED_CAPABILITY_COMPOSITION_COMPLETE"}

print(json.dumps({
 "status":"PASS",
 "successful_model_independent_answer_set":sorted(actual),
 "answer_set_cardinality":3,
 "answer_set_input_independent":True,
 "optional_model_finalizer_reachable":False,
 "terminal_case_content_read":False,
 "terminal_cases_consumed":0,
 "livebench_score_proved":False,
 "acceptance_credit_authorized":False,
},sort_keys=True))
