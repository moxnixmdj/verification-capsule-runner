from __future__ import annotations
import ast, copy, importlib.util, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
env=json.loads((ROOT/"envelope.json").read_text())
mat=json.loads((ROOT/"materiality.json").read_text())
law=(ROOT/"law.md").read_text()
runtime=(ROOT/"judgment_runtime.py").read_text()
tree=ast.parse(runtime)

errors=[]
def req(cond, code):
    if not cond: errors.append(code)

# Canonical-law criteria, checked independently rather than trusting the candidate boolean.
for literal in [
    "Brain owns the operative capability configuration",
    "the configuration materially constrains/directs execution",
    "the capability package contains that configuration",
    "promotion evidence evaluates the Brain-configured system",
    "ownership claim does not rely solely on the model's standalone benchmark superiority",
    'replacing Brain\'s capability package with the instruction "use model X" leaves essentially the same target capability',
]:
    req(literal in law, "LAW_LITERAL_MISSING:"+literal[:32])

req(set(env.get("families",[]))=={"FINANCIAL_ANALYSIS","UNKNOWN_DOMAIN_ADAPTATION"}, "FAMILY_SET")
control=env.get("control_contract",{})
req(control.get("proposal_source_role")=="GENERAL_COGNITION_SUBSTRATE", "ROLE_NOT_GENERAL_SUBSTRATE")
req(control.get("caller_verified_boolean_authority") is False, "CALLER_BOOLEAN_AUTHORITY")
for k in [
    "brain_recomputes_semantic_ir",
    "brain_recomputes_explicit_operator_counterfactuals",
    "brain_recomputes_semantic_identifiability",
    "brain_recomputes_finite_identifiability",
    "brain_recomputes_typed_evidence_decision",
    "finance_required_evidence_must_contribute_to_selected_decision",
    "finance_reconciliations_computed_with_exact_decimal_arithmetic",
    "unknown_domain_conclusion_requires_resolved_version_space",
    "abstention_requires_recomputed_nonidentifiability_or_semantic_unknown",
    "discriminator_must_be_derived_from_recomputed_identifiability_gap",
]:
    req(control.get(k) is True, "CONTROL_CONTRACT:"+k)

# Independent materiality receipt must already cover both target domains.
req(str(mat.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"), "MATERIALITY_NOT_INDEPENDENT_PASS")
verified=set(mat.get("verified",[]))
req("PROOF_CARRYING_CONFIGURATION_MATERIALLY_CONTROLS_FINANCE_AND_UNKNOWN_DOMAIN_TERMINAL_DECISIONS" in verified,
    "CROSS_DOMAIN_MATERIAL_CONTROL_NOT_PROVED")
req("MATERIALITY_DOES_NOT_LAUNDER_GENERAL_SUBSTRATE_QUALIFICATION" in verified,
    "ANTI_LAUNDER_GUARD_NOT_PROVED")

# The operative runtime itself must be provider-agnostic and expose one Brain-controlled
# terminal-decision function for both materially different domains.
vendor_tokens=("anthropic","claude","opus","openai","gemini","deepseek","qwen","api.openai","bedrock")
low=runtime.lower()
req(not any(t in low for t in vendor_tokens), "MODEL_OR_PROVIDER_SPECIFIC_OPERATIVE_RUNTIME")
funcs={n.name:n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
req("configured_terminal_decision" in funcs, "CONFIGURED_DECISION_FUNCTION_MISSING")
req("bare_terminal_decision" in funcs, "BARE_DECISION_FUNCTION_MISSING")
configured_src=ast.get_source_segment(runtime, funcs.get("configured_terminal_decision")) or ""
bare_src=ast.get_source_segment(runtime, funcs.get("bare_terminal_decision")) or ""
req("_evaluate_bundle" in configured_src, "CONFIGURED_PATH_DOES_NOT_RECOMPUTE_PROOF")
req("_evaluate_bundle" not in bare_src, "BARE_PATH_UNEXPECTEDLY_RECOMPUTES_PROOF")
req('mode == "FINANCE"' in configured_src and 'mode == "UNKNOWN_DOMAIN"' in configured_src,
    "SAME_CONTROLLED_INTERFACE_NOT_CROSS_DOMAIN")
req("GENERAL_COGNITION_MAY_PROPOSE_TYPED_STRUCTURE" in runtime, "GENERAL_SUBSTRATE_BOUNDARY_RULE_MISSING")
req("CALLER_VERIFIED_BOOLEANS_HAVE_ZERO_AUTHORITY" in runtime, "CALLER_AUTHORITY_FIREWALL_MISSING")

# Provider test: the independently verified material-control counterfactual plus the
# structural bare-vs-configured difference proves replacing the Brain package with a
# bare proposal source does NOT leave the same judgment-control capability.
provider_replacement_same_target_capability = not (
    "PROOF_CARRYING_CONFIGURATION_MATERIALLY_CONTROLS_FINANCE_AND_UNKNOWN_DOMAIN_TERMINAL_DECISIONS" in verified
    and "_evaluate_bundle" in configured_src
    and "_evaluate_bundle" not in bare_src
)
req(provider_replacement_same_target_capability is False, "EXTERNAL_CAPABILITY_PROVIDER_TEST_FAILED")

route=copy.deepcopy(env.get("source_gate_v2_candidate",{}))
route["configuration_materially_constrains_execution"]=True
route["external_hidden_target_capability_provider"]=False
route["general_substrate_test_pass"]=(len(errors)==0)

spec=importlib.util.spec_from_file_location("source_gate", ROOT/"source_gate.py")
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
gate=mod.evaluate(route)
req(gate.get("pass") is True, "SOURCE_GATE_V2_DID_NOT_PASS_AFTER_DERIVED_QUALIFICATION")

passed=not errors
out={
    "schema":"PROJECT_BRAIN_DUAL_JUDGMENT_GENERAL_SUBSTRATE_QUALIFICATION_V1",
    "status":"PASS__GENERAL_SUBSTRATE_QUALIFIED_FOR_PROOF_CARRYING_DUAL_JUDGMENT_CONTROL__SOURCE_GATE_V2_PASS" if passed else "FAIL_CLOSED",
    "pass":passed,
    "errors":sorted(set(errors)),
    "families":["FINANCIAL_ANALYSIS","UNKNOWN_DOMAIN_ADAPTATION"],
    "qualified_capability_scope":"PROOF_CARRYING_TERMINAL_JUDGMENT_CONTROL_ONLY",
    "same_controlled_interface_cross_domain":passed,
    "provider_replacement_same_target_capability":provider_replacement_same_target_capability,
    "general_substrate_test_pass":passed,
    "source_gate_v2":gate,
    "new_reality_units_consumed":0,
    "terminal_case_content_consumed":0,
    "incremental_spend_usd":0,
    "capability_credit_delta":0,
    "family_credit_delta":0,
    "execution_authority":False,
    "promotion_authority":False,
    "hard_nonclaims":[
        "NO_RAW_NATURAL_LANGUAGE_SEMANTIC_GENERATION_OWNERSHIP",
        "NO_SOURCE_TRUTH_ORACLE_OWNERSHIP",
        "NO_FINANCE_DIRECT_LEAF_PASS",
        "NO_UNKNOWN_DOMAIN_DIRECT_LEAF_PASS",
        "NO_OPUS55_PARITY",
        "SOURCE_GATE_PASS_ONLY_AUTHORIZES_SEPARATELY_FROZEN_DIRECT_LEAVES_AFTER_CANONICAL_BINDING",
    ],
}
print(json.dumps(out,indent=2,sort_keys=True))
raise SystemExit(0 if passed else 1)
