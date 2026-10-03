from __future__ import annotations
import json, os
from pathlib import Path

ROOT=Path(__file__).resolve().parent
TD=Path(os.environ["TOOLATHLON_DIR"])

def require(cond,msg):
    if not cond:
        raise AssertionError(msg)

candidate=json.loads((ROOT/"candidate.json").read_text())
internal=json.loads((ROOT/"brain_internal_receipt.json").read_text())
v4=json.loads((ROOT/"brain_v4_receipt.json").read_text())

require(candidate["status"].startswith("CANDIDATE__"),"candidate status")
require(candidate["capability_credit_delta"]==0 and candidate["family_credit_delta"]==0,"zero credit")
require(candidate["execution_authority"] is False and candidate["promotion_authority"] is False,"no authority")
require(candidate["incremental_spend_usd"]==0,"zero spend")
require(candidate["frozen_target"]["commit"]=="9be8d8fe07a497b18ee61e3f2ae694e9797f39eb","target commit")

configs=sorted((TD/"tasks/finalpool").glob("*/task_config.json"))
require(len(configs)==108,f"expected 108 task configs, got {len(configs)}")
all_servers=set()
for p in configs:
    cfg=json.loads(p.read_text())
    servers=cfg.get("needed_mcp_servers")
    locals_=cfg.get("needed_local_tools")
    require(isinstance(servers,list) and all(isinstance(x,str) and x for x in servers),f"bad servers {p}")
    require(isinstance(locals_,list) and all(isinstance(x,str) and x for x in locals_),f"bad local tools {p}")
    require(len(servers)==len(set(servers)),f"duplicate server {p}")
    all_servers.update(servers)
require(bool(all_servers),"empty server universe")

readme=(TD/"README.md").read_text()
taskcfg=(TD/"utils/data_structures/task_config.py").read_text()
gateway=(TD/"scripts/decoupled/container_tool_gateway.py").read_text()
host=(TD/"scripts/decoupled/host_agent_loop_claude_sdk.py").read_text()
runner=(TD/"scripts/run_single_decoupled.sh").read_text()

require("general tool use in realistic environments" in readme,"missing general-tool-use claim")
require("600+ diverse tools" in readme,"missing 600+ tool claim")
require("Each task requires long-horizon tool calls" in readme,"missing long-horizon claim")

require("needed_mcp_servers=task_config_dict['needed_mcp_servers']" in taskcfg,"task server source not bound")
require("needed_local_tools=task_config_dict['needed_local_tools']" in taskcfg,"task local source not bound")

for needle in [
    'needed_servers = self.bundle.get("needed_mcp_servers", []) or []',
    'await self.mcp_manager.connect_servers(needed_servers)',
    'for server_name in self.mcp_manager.get_connected_server_names():',
    'tools = await server.list_tools()',
    'self.registry.add_remote_tools(server_name, tools)',
    'self.registry.add_claim_done()',
    'if method == "tools/list":',
    'self.registry.list_tools()',
    'tool_record = self.registry.get(tool_name)',
    'if tool_record is None:',
    'Tool not found: {tool_name}',
]:
    require(needle in gateway,f"gateway premise missing: {needle}")

for needle in [
    'gateway_tools = await list_gateway_tools_via_sse(gateway_url)',
    'allowed_tools = build_allowed_mcp_tool_names(',
    'allowed_tools = await resolve_allowed_tools_for_gateway(',
    'tools=[]',
    'mcp_servers={',
    'args.gateway_server_name:',
    'allowed_tools=allowed_tools',
    '"strict-mcp-config": None',
]:
    require(needle in host,f"host premise missing: {needle}")

require("scripts.decoupled.container_tool_gateway" in runner,"gateway not launched")
require("--gateway_url" in runner and "/sse" in runner,"host not bound to gateway")

require(internal.get("workflow_conclusion")=="success","internal receipt not green")
verified=set(internal.get("verified") or [])
for fact in [
 "TRUE_TOOL_CAPABILITIES_HIDDEN_FROM_CANDIDATE",
 "SAFE_PROBES_RESTRICTED_TO_CURRENT_REQUIRED_CAPABILITIES",
 "LEAST_COST_EVIDENCE_SUPPORTED_SUFFICIENT_ROUTE_SELECTED",
 "VALID_PRIOR_CAPABILITY_EVIDENCE_REUSED_ON_LATER_TASK",
 "TARGETED_VERSION_CHANGE_INVALIDATES_STALE_EVIDENCE",
 "UNAVAILABLE_CHEAPER_ROUTE_EXCLUDED",
 "UNAUTHORIZED_CHEAPER_ROUTE_EXCLUDED",
 "NO_SUFFICIENT_ROUTE_ESCALATES_ONLY_AFTER_RELEVANT_NEGATIVE_EVIDENCE",
 "PREMATURE_ESCALATION_REJECTED",
]:
    require(fact in verified,f"missing internal fact {fact}")
require(v4.get("status","").startswith("PASS__EXACT_BYTES"),"V4 receipt not exact pass")
require(v4.get("independent_public_runner",{}).get("run_conclusion")=="success","V4 runner not green")

expected_dims={
 "unknown tool discovery",
 "schema/authority filtering",
 "route selection under incomplete evidence",
 "safe probe choice",
 "capability-state update",
 "later-task transfer without rediscovery",
}
mapped={x["protocol_dimension"] for x in candidate["dimension_mapping"]}
require(mapped==expected_dims,(mapped,expected_dims))
require(set(candidate["frozen_protocol"]["dimensions"])==expected_dims,"protocol dimensions drift")

closes=set(candidate["precondition_effect_if_independently_verified"]["closes"])
require(closes=={"MAP_TOOLATHLON_REPRESENTED_DIMENSIONS_TO_FROZEN_TOOL_DISCOVERY_CONTRACT_WITHOUT_SCOPE_WEAKENING"},"overclaim in closes")
nonclaims=set(candidate["hard_nonclaims"])
for claim in [
 "NO_OPEN_DOMAIN_UNIVERSAL_TOOL_ENUMERATION_CLAIM",
 "NO_BRAIN_ONLY_REGISTRY_SUBSTITUTION",
 "NO_ZERO_COST_CARRIER_CLAIM",
 "NO_BRAIN_TOOLATHLON_RESULT",
 "NO_ACCEPTANCE_FAMILY_CAPABILITY_EXECUTION_OR_PROMOTION_CREDIT",
]:
    require(claim in nonclaims,f"missing nonclaim {claim}")

print(json.dumps({
 "pass":True,
 "task_count":len(configs),
 "declared_server_identity_count":len(all_servers),
 "mapped_dimensions":sorted(mapped),
 "target_local_callable_surface_complete":True,
 "open_domain_universal_completeness_claimed":False,
 "acceptance_credit_delta":0,
},sort_keys=True))
