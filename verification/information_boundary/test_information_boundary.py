import ast
import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).parent
spec=importlib.util.spec_from_file_location("obs", ROOT/"continuous_obs_runtime.py")
obs=importlib.util.module_from_spec(spec); spec.loader.exec_module(obs)

class InformationBoundary(unittest.TestCase):
    def setUp(self):
        self.orig=obs.validate_context
        obs.validate_context=lambda context,root,now=None: {"errors":[],"checked_at_utc":"2026-10-01T00:00:00Z"}
    def tearDown(self):
        obs.validate_context=self.orig
    def verdict(self,mode,kind,source="",allowed=None,tools=None):
        ctx={"information_policy":{
            "mode":mode,
            "allowed_exact_sources":list(allowed or []),
            "allowed_external_tool_kinds":list(tools or []),
        }}
        return obs.authorize_information_action(
            ctx,{"kind":kind,"source":source,"tool_kind":""},root=ROOT
        )
    def test_exact_fetch_only_blocks_discovery(self):
        v=self.verdict("EXACT_FETCH_ONLY","DISCOVERY_SEARCH","generic-query",["allowed://x"])
        self.assertFalse(v["pass"])
        self.assertIn("DISCOVERY_FORBIDDEN_EXACT_FETCH_ONLY",v["errors"])
    def test_exact_fetch_only_allows_only_predeclared_source(self):
        good=self.verdict("EXACT_FETCH_ONLY","EXACT_FETCH","allowed://x",["allowed://x"])
        bad=self.verdict("EXACT_FETCH_ONLY","EXACT_FETCH","other://y",["allowed://x"])
        self.assertTrue(good["pass"],good)
        self.assertFalse(bad["pass"])
        self.assertIn("EXACT_FETCH_SOURCE_NOT_PREDECLARED",bad["errors"])
    def test_no_external_information_blocks_exact_fetch(self):
        v=self.verdict("NO_EXTERNAL_INFORMATION","EXACT_FETCH","allowed://x",["allowed://x"])
        self.assertFalse(v["pass"])
        self.assertIn("EXTERNAL_INFORMATION_FORBIDDEN",v["errors"])
    def test_unknown_action_fails(self):
        v=self.verdict("OPEN_DISCOVERY","MAGIC","x")
        self.assertFalse(v["pass"])
        self.assertIn("INFORMATION_ACTION_KIND_INVALID",v["errors"])
    def test_astra_external_bridge_is_guarded(self):
        tree=ast.parse((ROOT/"astra_runtime.py").read_text())
        funcs={n.name:n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
        bridge=funcs["_external_tool_bridge"]
        calls=[n for n in ast.walk(bridge) if isinstance(n,ast.Call)]
        self.assertTrue(any(isinstance(c.func,ast.Name) and c.func.id=="_authorize_external_information" for c in calls))
        activate=funcs["_activate_external_http_bridge"]
        assigns=[n for n in ast.walk(activate) if isinstance(n,ast.Assign)]
        found=False
        for a in assigns:
            for t in a.targets:
                if isinstance(t,ast.Attribute) and t.attr=="urlopen":
                    if isinstance(a.value,ast.Name) and a.value.id=="_bridge_aware_urlopen":
                        found=True
        self.assertTrue(found)
        self.assertFalse(any(isinstance(n,ast.If) for n in activate.body),
                         "urlopen guard must be installed unconditionally")

if __name__=="__main__":
    unittest.main(verbosity=2)
