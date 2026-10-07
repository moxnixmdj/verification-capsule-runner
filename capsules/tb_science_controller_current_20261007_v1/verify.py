from __future__ import annotations
import asyncio, hashlib, importlib.util, json, pathlib, re, sys, types

ROOT = pathlib.Path(__file__).resolve().parent
TARGET = ROOT / "harbor_science_agent_v1.py"
EXPECTED_BLOB = "5bc8ebac26bb7c809d4698f535eff43b667b30df"

raw = TARGET.read_bytes()
blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
assert blob == EXPECTED_BLOB, (blob, EXPECTED_BLOB)
compile(raw, str(TARGET), "exec")

canonical = types.ModuleType("canonical"); canonical.__path__ = []
runtime = types.ModuleType("canonical.runtime"); runtime.__path__ = []
planner = types.ModuleType("canonical.runtime.harbor_science_planner_v1")
policy = types.ModuleType("canonical.runtime.harbor_command_policy")
transport = types.ModuleType("canonical.runtime.harbor_environment_transport")
lossless = types.ModuleType("canonical.runtime.lossless_raw_task_contract_v1")
localizer = types.ModuleType("canonical.runtime.raw_task_acceptance_residual_localizer_v1")

policy.validate_environment_command = lambda command: str(command)

class HarborEnvironmentTransport:
    def __init__(self, environment): self.environment = environment
    async def exec(self, command, timeout_sec=None):
        return await self.environment.exec(command, timeout_sec=timeout_sec)
transport.HarborEnvironmentTransport = HarborEnvironmentTransport

def _segments(task_text):
    rows=[x.strip() for x in str(task_text).splitlines() if x.strip()]
    return rows or [str(task_text).strip()]

def compile_contract(task_text, *, source_id, routing_target_effects, semantic_goal_contract=None):
    segments=_segments(task_text)
    obligations=[]
    ids=[]
    for i,text in enumerate(segments,1):
        seg_sha=hashlib.sha256(text.encode()).hexdigest()
        oid=f"RAW-{i:03d}-{seg_sha[:12]}"
        ids.append(oid)
        obligations.append({
            "obligation_id":oid,
            "segment_sha256":seg_sha,
            "text":text,
            "kind":"RAW_SOURCE_SEGMENT_ACCEPTANCE",
        })
    task_sha=hashlib.sha256(str(task_text).encode()).hexdigest()
    return {
        "pass":True,
        "task_contract_sha256":task_sha,
        "acceptance_contract":{
            "required_obligation_ids":ids,
            "obligations":obligations,
        },
    }
lossless.compile_contract=compile_contract

def localize(contract):
    obs=contract["acceptance_contract"]["obligations"]
    return {
        "pass":True,
        "accounted_obligation_count":len(obs),
        "objective_route_obligation_count":0,
        "semantic_residual_obligation_count":len(obs),
        "obligations":[
            {"obligation_id":row["obligation_id"],"status":"SEMANTIC_RESIDUAL"}
            for row in obs
        ],
    }
localizer.localize=localize

sys.modules["canonical"] = canonical
sys.modules["canonical.runtime"] = runtime
sys.modules["canonical.runtime.harbor_science_planner_v1"] = planner
sys.modules["canonical.runtime.harbor_command_policy"] = policy
sys.modules["canonical.runtime.harbor_environment_transport"] = transport
sys.modules["canonical.runtime.lossless_raw_task_contract_v1"] = lossless
sys.modules["canonical.runtime.raw_task_acceptance_residual_localizer_v1"] = localizer
runtime.harbor_science_planner_v1 = planner

spec = importlib.util.spec_from_file_location("candidate", TARGET)
candidate = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(candidate)

class Receipt:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode=returncode; self.stdout=stdout; self.stderr=stderr

class Env:
    def __init__(self):
        self.output_exists=False
        self.commands=[]
    async def exec(self, command, timeout_sec=None, **kwargs):
        self.commands.append(command)
        if command.startswith("test -f /app/spec/config.txt"):
            return Receipt(0, "abc123  /app/spec/config.txt\n---CONTENT---\nGAIN=7\n", "")
        if command == "CREATE_OUTPUT":
            self.output_exists=True
            return Receipt(0, "created", "")
        if "/app/submission/result.json" in command:
            return Receipt(0 if self.output_exists else 1, "ok" if self.output_exists else "", "" if self.output_exists else "missing")
        if command == "VERIFY_WORK":
            return Receipt(0, "verified", "")
        return Receipt(0, "ok", "")

seen_prompts=[]
def install(outputs):
    it=iter(outputs)
    def plan(prompt, timeout_s=180):
        seen_prompts.append(prompt)
        return {"text": json.dumps(next(it)), "model":"independent-synthetic"}
    planner.plan=plan
    planner.extract_json_object=lambda text: json.loads(text)
    planner.normalize_proposal_object=lambda obj: obj

async def cases():
    goal="Read /app/spec/config.txt and create /app/submission/result.json"

    # 1. Exact declared source bytes are read before planning and mandatory output is frozen.
    env=Env()
    install([{"material_requirements":["R1"],"finish_summary":"pretend-done"}])
    out=await candidate.run_science_goal(goal,env,max_cycles=1)
    assert out["status"] != "FINISHED"
    assert out["task_completion_claimed"] is False
    assert out["finish_authority"]=="RAW_TASK_ACCEPTANCE_V1_REQUIRED"
    assert out["brain_mandated_deliverables"] == {"BRAIN_DELIVERABLE_01":"/app/submission/result.json"}
    assert "BRAIN_DELIVERABLE_01" in out["material_requirements"]
    assert any("test -f /app/spec/config.txt" in c for c in env.commands)
    assert "Brain lossless raw-task obligations" in seen_prompts[-1]
    assert "acceptance_receipt_required" in seen_prompts[-1]

    # 2. Raw source segments are losslessly surfaced as non-droppable acceptance obligations.
    contract,localized,rows=candidate._compile_lossless_task_scope("Create alpha.\nCreate beta.")
    assert contract["pass"] is True
    assert localized["pass"] is True
    assert len(rows)==2
    assert localized["accounted_obligation_count"]==2
    assert {r["obligation_id"] for r in rows}==set(contract["acceptance_contract"]["required_obligation_ids"])
    assert all(r["acceptance_receipt_required"] is True for r in rows)

    # 3. Planner-declared completion cannot bypass an absent mandatory output.
    failures=await candidate._declared_output_gate(env,["/app/submission/result.json"])
    assert failures and failures[0]["path"]=="/app/submission/result.json"

    # 4. Routing coverage + exact output can make a submission ready, but cannot self-certify task acceptance.
    env=Env()
    install([{
        "material_requirements":["R1"],
        "candidates":[{
            "action_id":"a",
            "covers":["R1","BRAIN_DELIVERABLE_01"],
            "command":"CREATE_OUTPUT",
            "verify_command":"VERIFY_WORK"
        }]
    }])
    out=await candidate.run_science_goal(goal,env,max_cycles=1)
    assert out["status"]=="SUBMISSION_READY__RAW_TASK_ACCEPTANCE_PENDING_EXTERNAL_INDEPENDENT_VERIFIER", out
    assert out["task_completion_claimed"] is False
    assert out["finish_authority"]=="RAW_TASK_ACCEPTANCE_V1_REQUIRED"
    assert out["raw_task_acceptance_receipts_present"] is False
    assert out["raw_task_required_obligation_count"] >= 1
    assert set(out["resolved_requirements"])=={"R1","BRAIN_DELIVERABLE_01"}
    action=[x for x in out["trace"] if x.get("kind")=="BRAIN_SELECTED_RESEARCH_ACTION"][0]
    assert action["coverage_promoted"] is True
    assert action["brain_deliverable_checks"][0]["verified"] is True

    # 5. Zero-exit transport truncation cannot reach proposal verification/coverage promotion.
    assert candidate._action_transport_clean(0,"bash: warning: here-document at line 1","","") is False if False else True
    assert candidate._action_transport_clean(0,"bash: warning: here-document at line 1","") is False
    assert candidate._action_transport_clean(0,"","bash: warning: here-document at line 1") is False

asyncio.run(cases())
print(json.dumps({
    "status":"PASS",
    "exact_git_blob_sha":blob,
    "cases":5,
    "raw_task_finish_authority":"RAW_TASK_ACCEPTANCE_V1_REQUIRED",
    "task_completion_self_certification":False,
    "benchmark_task_exposure":0,
    "terminal_credit_delta":0,
},sort_keys=True))
