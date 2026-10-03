from __future__ import annotations
import asyncio, pathlib, re, unittest
from canonical.runtime import toolathlon_brain_host_integration_v1 as h

ROOT=pathlib.Path(__file__).resolve().parent
GATE=(ROOT/"frozen_toolathlon/container_tool_gateway.py").read_text(encoding="utf-8")

class ExactWireGateway:
    """Exact public wire shape emitted by frozen Toolathlon ToolRegistry.list_tools."""
    def __init__(self):
        self.calls=[]
        self.tools=[
          {"name":"server-a-search","description":"Search workspace","inputSchema":{"type":"object","properties":{"q":{"type":"string"}}}},
          {"name":"server-b-search","description":"Search workspace","inputSchema":{"type":"object","properties":{"q":{"type":"string"}}}},
          {"name":"local-claim_done","description":"claim the task is done","inputSchema":{"type":"object","properties":{},"additionalProperties":False}},
        ]
    async def __call__(self,req):
        self.calls.append(req)
        if req["method"]=="tools/list":
            return {"jsonrpc":"2.0","id":req["id"],"result":{"tools":self.tools}}
        if req["method"]=="tools/call":
            n=req["params"]["name"]
            if n not in {x["name"] for x in self.tools}:
                return {"jsonrpc":"2.0","id":req["id"],"error":{"code":-32602,"message":"Tool not found: "+n}}
            return {"jsonrpc":"2.0","id":req["id"],"result":{"content":[{"type":"text","text":"ok"}],"isError":False}}
        raise AssertionError(req)

class Substrate:
    def __init__(self,inject=False):
        self.inject=inject
        self.seen=[]
    async def __call__(self,kind,payload):
        self.seen.append((kind,payload))
        if kind=="SUBPROBLEM":
            out={"goal":"find","required_capabilities":["SEARCH_WORKSPACE"],"constraint":None}
            if self.inject: out["selected_tool"]="server-b-search"
            return out
        if kind=="SCHEMA_JUDGMENT":
            s=repr(payload)
            assert "server-a-search" not in s and "server-b-search" not in s
            assert "'cost'" not in s
            return {"supported": "Search workspace" in s}
        if kind=="ARGUMENTS":
            s=repr(payload)
            assert "server-a-search" not in s and "server-b-search" not in s
            return {"arguments":{"q":"needle"}}
        raise AssertionError(kind)

class Independent(unittest.TestCase):
    def test_frozen_gateway_source_has_exact_wire_contract(self):
        self.assertIn('if method == "tools/list":',GATE)
        self.assertIn('{"tools": self.registry.list_tools()}',GATE)
        self.assertIn('if method == "tools/call":',GATE)
        self.assertIn('tool_record = self.registry.get(tool_name)',GATE)
        self.assertIn('f"Tool not found: {tool_name}"',GATE)
        # Exact gateway list schema carries no cost/auth side channel.
        list_block=GATE[GATE.index("def list_tools"):GATE.index("def get(",GATE.index("def list_tools"))]
        self.assertIn('"name": record.exposed_name',list_block)
        self.assertIn('"description": record.description',list_block)
        self.assertIn('"inputSchema": record.input_schema',list_block)
        self.assertNotIn('"cost"',list_block)
        self.assertNotIn('"authorized"',list_block)

    def test_exact_wire_defaults_are_explicit_and_selection_stays_brain_owned(self):
        async def go():
            gw=ExactWireGateway()
            out=await h.execute_one_brain_selected_step(
                rpc=gw,substrate=Substrate(),task_context="find")
            # With no wire costs, adapter defaults every listed route to cost 1
            # and Brain's deterministic opaque-id tiebreak selects server-a.
            self.assertEqual(out["selected_tool_id"],"server-a-search")
            self.assertEqual([c["method"] for c in gw.calls],["tools/list","tools/call"])
            self.assertEqual(gw.calls[-1]["params"]["name"],"server-a-search")
        asyncio.run(go())

    def test_substrate_cannot_inject_route_on_exact_wire(self):
        async def go():
            gw=ExactWireGateway()
            with self.assertRaisesRegex(h.ToolathlonBrainHostError,"SUBPROBLEM_CONTRACT_REJECTED"):
                await h.execute_one_brain_selected_step(
                    rpc=gw,substrate=Substrate(inject=True),task_context="find")
            self.assertEqual([c["method"] for c in gw.calls],["tools/list"])
        asyncio.run(go())

if __name__=="__main__":
    unittest.main(verbosity=2)
