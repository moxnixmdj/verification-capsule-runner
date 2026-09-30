#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,pathlib,unicodedata
ROOT=pathlib.Path(__file__).resolve().parent
TASK="brain_snapshot/canonical/tasks/PARENT-SEISMOLOGY-KAMCHATKA-TSUNAMI-OPEN-RESEARCH-TASK-B-20260930-002.json"
MISSION="brain_snapshot/canonical/astra_runtime/missions/PARENT-SEISMOLOGY-KAMCHATKA-TSUNAMI-OPEN-RESEARCH-TASK-B-20260930-002.json"
RUNTIME="brain_snapshot/canonical/runtime/astra_runtime.py"
AUTH="brain_snapshot/canonical/action_intents/2026-09-30_EXECUTE_GUARDED_SEISMOLOGY_TASK_B_V2.json"
def sha256_file(rel): return hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()
mission=json.loads((ROOT/MISSION).read_text(encoding="utf-8"))
goal=str(mission["goal"])
norm=" ".join(unicodedata.normalize("NFKC",goal).strip().lower().split())
plan={
  "schema":"BRAIN_GUARDED_LAUNCH_PLAN_V1",
  "goal_text":goal,
  "frozen":{
    "gate_id":"BRAIN-PARENT-SEISMOLOGY-KAMCHATKA-TSUNAMI-TASK-B-20260930-002-V1",
    "problem_sha256":hashlib.sha256(("goal_text_v1\\0"+norm).encode("utf-8")).hexdigest(),
    "task_sha256":sha256_file(TASK),
    "runtime_sha256":sha256_file(RUNTIME),
    "canonical_base":"9c9366e2bc0ee63860007fe17041ec8d8503648f",
    "authorization_sha256":sha256_file(AUTH)
  },
  "pinned_files":[
  {
    "path": "brain_snapshot/canonical/runtime/apt_cli_probe.py",
    "git_blob_sha1": "3f3a8f6a0154e1ed3f87fc97b99840598297b119"
  },
  {
    "path": "brain_snapshot/canonical/runtime/apt_python_probe.py",
    "git_blob_sha1": "59238bf3f98a6e57859628f265bff0131a36222b"
  },
  {
    "path": "brain_snapshot/canonical/runtime/astra_hidden_verifier.py",
    "git_blob_sha1": "55e3cdd3106da0690edc5cd1946507fdcc684377"
  },
  {
    "path": "brain_snapshot/canonical/runtime/astra_hidden_visual_executor.py",
    "git_blob_sha1": "e570041c16c55e8d5034195f4185feef1b9fea40"
  },
  {
    "path": "brain_snapshot/canonical/runtime/astra_runtime.py",
    "git_blob_sha1": "426ffe58e405dc4f1ba2eb4e838e03a1df771964"
  },
  {
    "path": "brain_snapshot/canonical/runtime/auto_apt_cli_acquisition.py",
    "git_blob_sha1": "0b7c67a2680a3aaa1aa5cf1a8bc8d41d69eee271"
  },
  {
    "path": "brain_snapshot/canonical/runtime/auto_capability_acquisition.py",
    "git_blob_sha1": "fc80ede8225cc51dac77be6d41aa2a1c757c6ee8"
  },
  {
    "path": "brain_snapshot/canonical/runtime/auto_github_source_acquisition.py",
    "git_blob_sha1": "5de539a4d1c54ca0b22459f39f6f4f494644a6c6"
  },
  {
    "path": "brain_snapshot/canonical/runtime/auto_npm_library_acquisition.py",
    "git_blob_sha1": "b74cdf34a96fc2d591b902e1d582e0381a8a8d08"
  },
  {
    "path": "brain_snapshot/canonical/runtime/auto_pypi_library_acquisition.py",
    "git_blob_sha1": "6387bd7b8f1dba8bb9f66240e3ebb2627085dd2f"
  },
  {
    "path": "brain_snapshot/canonical/runtime/auto_python_source_codec_acquisition.py",
    "git_blob_sha1": "65453b2eed5e678def3f0ab1c4d44182fb0b9a78"
  },
  {
    "path": "brain_snapshot/canonical/runtime/bound_capabilities/archive_tarfile.py",
    "git_blob_sha1": "2ae62c04ef495d855ca8d46263b4cf05110b5648"
  },
  {
    "path": "brain_snapshot/canonical/runtime/bound_capabilities/archive_verify_gnu_tar.py",
    "git_blob_sha1": "18c484e973e0becf6abf883463a7dc174d0bcd22"
  },
  {
    "path": "brain_snapshot/canonical/runtime/bound_capabilities/broad_objective_decompose.py",
    "git_blob_sha1": "3ded762075ed222228a14877af631f1e2e6d9e4c"
  },
  {
    "path": "brain_snapshot/canonical/runtime/bound_capabilities/browser_chromedriver_interact.py",
    "git_blob_sha1": "ff280a1ed9c7c118c677a0fec6b3baa8705c675c"
  },
  {
    "path": "brain_snapshot/canonical/runtime/bound_capabilities/browser_chromedriver.py",
    "git_blob_sha1": "6edaad1d9d23700a55d988c891d4ef41b8191c4b"
  },
  {
    "path": "brain_snapshot/canonical/runtime/bound_capabilities/cli_command.py",
    "git_blob_sha1": "6782773801cd8f2258e4368a4debbe6e66c4a393"
  },
  {
    "path": "brain_snapshot/canonical/runtime/bound_capabilities/docx_report_from_json.py",
    "git_blob_sha1": "9667232f07cd1d285ecd598d85d8cdcf3f990701"
  },
  {
    "path": "brain_snapshot/canonical/runtime/bound_capabilities/docx_verify_ooxml_intent.py",
    "git_blob_sha1": "937944128257c10d95038b99dd3d120cd3104ae1"
  },
  {
    "path": "brain_snapshot/canonical/runtime/bound_capabilities/docx_verify_ooxml.py",
    "git_blob_sha1": "41c2d9043b65376e13366cbdcd2d35a2cf12b2dc"
  },
  {
    "path": "brain_snapshot/canonical/runtime/bound_capabilities/evidence_decision_synthesis.py",
    "git_blob_sha1": "d7c73c24d2038c40bfb38ea6f10749a15a2d5415"
  },
  {
    "path": "brain_snapshot/canonical/runtime/bound_capabilities/evidence_decision_verify.py",
    "git_blob_sha1": "63cf325320c7b91bf48ea2f2769c999c5a090929"
  },
  {
    "path": "brain_snapshot/canonical/runtime/bound_capabilities/first_party_objective_relevance_verify.py",
    "git_blob_sha1": "6ff13c32704c0b3283c42a51f718e875110a13ca"
  },
  {
    "path": "brain_snapshot/canonical/runtime/bound_capabilities/generic_evidence_claim_relation.py",
    "git_blob_sha1": "d66a7eb30774f66160b698d8082947776888293d"
  },
  {
    "path": "brain_snapshot/canonical/runtime/bound_capabilities/grounded_executable_composition_verify.py",
    "git_blob_sha1": "ab9f6fc19937d23edb24dc26a2affed96cea0a9a"
  },
  {
    "path": "brain_snapshot/canonical/runtime/bound_capabilities/grounded_executable_composition.py",
    "git_blob_sha1": "8328e12804f64cab1c0d9509966cb1d2d8fb1f82"
  },
  {
    "path": "brain_snapshot/canonical/runtime/bound_capabilities/http_json_fetch.py",
    "git_blob_sha1": "269e7b0f1aee8cac785f7f0e60338a1562a45201"
  },
  {
    "path": "brain_snapshot/canonical/runtime/bound_capabilities/jq_query.py",
    "git_blob_sha1": "f0b644274c1ffbff7ea5adb81e07e00435d2ac4c"
  },
  {
    "path": "brain_snapshot/canonical/runtime/bound_capabilities/node_library_codec.py",
    "git_blob_sha1": "0babcf3adf7762b5e24d9c8be4f8ecb3a7b2e805"
  },
  {
    "path": "brain_snapshot/canonical/runtime/bound_capabilities/numeric_expression_sympy.py",
    "git_blob_sha1": "443e3386f11156e55635556b6e8f8ad7d7733592"
  },
  {
    "path": "brain_snapshot/canonical/runtime/bound_capabilities/objective_claim_operand_binding.py",
    "git_blob_sha1": "48fd058430d8d361fc75beced567c7b6d1166531"
  },
  {
    "path": "brain_snapshot/canonical/runtime/bound_capabilities/objective_evidence_unit_extract.py",
    "git_blob_sha1": "fc45fb583f6aeac91f7c88f918644c38fbc70e34"
  },
  {
    "path": "brain_snapshot/canonical/runtime/bound_capabilities/objective_relevance_bm25.py",
    "git_blob_sha1": "a25a34d879413a9853f1d1ffd8ef5e4f6bdd2245"
  },
  {
    "path": "brain_snapshot/canonical/runtime/bound_capabilities/open_research_source_frontend.py",
    "git_blob_sha1": "1ec11496aa84f261fc2c7e8e689ba687581d8b3c"
  },
  {
    "path": "brain_snapshot/canonical/runtime/bound_capabilities/open_web_source_candidate_discovery.py",
    "git_blob_sha1": "045369d8cba5680c60b57e834d09d12a54d94380"
  },
  {
    "path": "brain_snapshot/canonical/runtime/bound_capabilities/pandoc_weasyprint.py",
    "git_blob_sha1": "1d7e867bb4837b7589d8346c85fe97db4c1166be"
  },
  {
    "path": "brain_snapshot/canonical/runtime/bound_capabilities/pdf_ocr_tesseract.py",
    "git_blob_sha1": "4fb3853a28974b30e8c5c36f85815cdb71fc243c"
  },
  {
    "path": "brain_snapshot/canonical/runtime/bound_capabilities/pdf_pypdf.py",
    "git_blob_sha1": "b63f658d269078f37f8a67be31ce4993b6cf3fcc"
  },
  {
    "path": "brain_snapshot/canonical/runtime/bound_capabilities/plain_goal_bound_grounding_verify.py",
    "git_blob_sha1": "d4aa64dc995845fcf8045f14f476f84b7f1d9cb8"
  },
  {
    "path": "brain_snapshot/canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py",
    "git_blob_sha1": "46e8e7466479ea298c34e5fa682d49c374510ce9"
  },
  {
    "path": "brain_snapshot/canonical/runtime/bound_capabilities/pypi_provenance_audit.py",
    "git_blob_sha1": "fd8af415d7846be0f2ff23aa1674df77af504d03"
  },
  {
    "path": "brain_snapshot/canonical/runtime/bound_capabilities/python_document_builder.py",
    "git_blob_sha1": "e3840df1b3b6de0b53288be622aad8d6799aadb1"
  },
  {
    "path": "brain_snapshot/canonical/runtime/bound_capabilities/python_library_codec.py",
    "git_blob_sha1": "e9b9f5c4991ba1f11b9f377a275b3e17bad22886"
  },
  {
    "path": "brain_snapshot/canonical/runtime/bound_capabilities/python_source_audit.py",
    "git_blob_sha1": "f708d51a480f3e49b3c9e4e0c0a34239094228ea"
  },
  {
    "path": "brain_snapshot/canonical/runtime/bound_capabilities/python_source_tree_codec.py",
    "git_blob_sha1": "8f452c01b2c88a9bd7663f8dc753b24b2e7f7f05"
  },
  {
    "path": "brain_snapshot/canonical/runtime/bound_capabilities/python_test_audit.py",
    "git_blob_sha1": "b6fe40131583587e21f9c1e369679de140349e81"
  },
  {
    "path": "brain_snapshot/canonical/runtime/bound_capabilities/qr_qrencode.py",
    "git_blob_sha1": "cbc50d00ccecc7745bbb361c5e526b1bada39e41"
  },
  {
    "path": "brain_snapshot/canonical/runtime/bound_capabilities/relevant_source_evidence_extract.py",
    "git_blob_sha1": "6720340ff00d16823921913e0486552db9ad5755"
  },
  {
    "path": "brain_snapshot/canonical/runtime/bound_capabilities/research_query_focus.py",
    "git_blob_sha1": "5403e1dc05716fcfc4f9a91b4534f55dc547eb7f"
  },
  {
    "path": "brain_snapshot/canonical/runtime/bound_capabilities/source_authority_binding_ror.py",
    "git_blob_sha1": "9396ff7169b274af9bbfbe736e004587631e3b05"
  },
  {
    "path": "brain_snapshot/canonical/runtime/bound_capabilities/source_candidate_provenance_verify.py",
    "git_blob_sha1": "1dc26e68d18010b66211d1d83f7b2024c8ad1fcf"
  },
  {
    "path": "brain_snapshot/canonical/runtime/bound_capabilities/sqlite_table_stdlib.py",
    "git_blob_sha1": "d729d19ba5c0808273268426e7450f1db74a5c07"
  },
  {
    "path": "brain_snapshot/canonical/runtime/bound_capabilities/sqlite_verify_cli.py",
    "git_blob_sha1": "339c6e5cd3e1804a43dd3632deb713b61f6344a4"
  },
  {
    "path": "brain_snapshot/canonical/runtime/bound_capabilities/web_release_verify.py",
    "git_blob_sha1": "126b46cd2cd11dd12bfa16aa0e337349fe0d70bf"
  },
  {
    "path": "brain_snapshot/canonical/runtime/bound_capabilities/xlsx_table_xlsxwriter.py",
    "git_blob_sha1": "b8a6d0f0553ffec468676b24f87d56aeb01cea17"
  },
  {
    "path": "brain_snapshot/canonical/runtime/bound_capabilities/xlsx_verify_openpyxl.py",
    "git_blob_sha1": "93c84e524dd01eace5b059f00d7c0c020f36c57c"
  },
  {
    "path": "brain_snapshot/canonical/runtime/bound_capabilities/yq_yaml_json.py",
    "git_blob_sha1": "8dce9a679d51153e0e779e4fcc5380a1ce106637"
  },
  {
    "path": "brain_snapshot/canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json",
    "git_blob_sha1": "7badee4878700f2cd4176beb8319d2a6a0bdf782"
  },
  {
    "path": "brain_snapshot/canonical/runtime/capability_discovery.py",
    "git_blob_sha1": "b9e7423ab24bf2da98869b02d782e791a779892a"
  },
  {
    "path": "brain_snapshot/canonical/runtime/capability_planner.py",
    "git_blob_sha1": "64ff65cb184f50d3336326f33cccfcc0a53301a8"
  },
  {
    "path": "brain_snapshot/canonical/runtime/capability_proposal_generators.py",
    "git_blob_sha1": "71f2bbfda66a65d8d75e035b9ae073671ebd56e2"
  },
  {
    "path": "brain_snapshot/canonical/runtime/capability_reality_auditor.py",
    "git_blob_sha1": "30bd0143beefc5ad7ac612581f030a554b04d7dd"
  },
  {
    "path": "brain_snapshot/canonical/runtime/cli_contract_inference.py",
    "git_blob_sha1": "009c3c45040178844d84eaa15b0d47ca2e1f259f"
  },
  {
    "path": "brain_snapshot/canonical/runtime/docx_goal_compiler.py",
    "git_blob_sha1": "1349e28ab2708303e1973f4039b853de32510a13"
  },
  {
    "path": "brain_snapshot/canonical/runtime/enforce_goal_hierarchy.py",
    "git_blob_sha1": "8cba5850b6f7cb950cd8daca28be58f714520f18"
  },
  {
    "path": "brain_snapshot/canonical/runtime/EPISTEMIC_POLICY_V1.json",
    "git_blob_sha1": "baab96f37ba87edc3fdcf6914016cf6593eea102"
  },
  {
    "path": "brain_snapshot/canonical/runtime/evidence_state.py",
    "git_blob_sha1": "8a461b6ed06129ef778efc77db20df50928d27b1"
  },
  {
    "path": "brain_snapshot/canonical/runtime/executor_broker.py",
    "git_blob_sha1": "3322715d9c703a4ed4563275681c27ba20e76d04"
  },
  {
    "path": "brain_snapshot/canonical/runtime/EXECUTOR_POLICY_V1.json",
    "git_blob_sha1": "bc4bd1088e5d31eb584325e50e74a9df3f7d5dcc"
  },
  {
    "path": "brain_snapshot/canonical/runtime/external_tool_relay.py",
    "git_blob_sha1": "c179ff584559172314ed04298996823abe2f02ab"
  },
  {
    "path": "brain_snapshot/canonical/runtime/github_source_codec_runner.py",
    "git_blob_sha1": "d7fc51bbb9bab851dd0ba2349f3438cb928299f0"
  },
  {
    "path": "brain_snapshot/canonical/runtime/github_superworker_runner.mjs",
    "git_blob_sha1": "6270999c2f487344690c62511dd0636ea1e548eb"
  },
  {
    "path": "brain_snapshot/canonical/runtime/github_superworker_verifier.mjs",
    "git_blob_sha1": "ef1f38ac259dff85c5743b91203ccd095eb40823"
  },
  {
    "path": "brain_snapshot/canonical/runtime/goal_compiler.py",
    "git_blob_sha1": "4b61fe911471854ec15c7900816f61e9e55f602e"
  },
  {
    "path": "brain_snapshot/canonical/runtime/independent_npm_codec_verifier.py",
    "git_blob_sha1": "06fe2fbd7d5169e2cf455868747ac7077466c221"
  },
  {
    "path": "brain_snapshot/canonical/runtime/independent_pypi_codec_verifier.py",
    "git_blob_sha1": "7c8f68ac1dd8d7760794198f9ac0d8fb542be7e9"
  },
  {
    "path": "brain_snapshot/canonical/runtime/mcp_tool_inspector.py",
    "git_blob_sha1": "3742471c06515af798526e6401f81293b136f2f3"
  },
  {
    "path": "brain_snapshot/canonical/runtime/node_codec_runner.js",
    "git_blob_sha1": "2fcda55c8537051315a0d2a939c865f2442e1279"
  },
  {
    "path": "brain_snapshot/canonical/runtime/npm_package_utils.py",
    "git_blob_sha1": "05fd0591083034df48c3ee426d6b3e11e0183555"
  },
  {
    "path": "brain_snapshot/canonical/runtime/promote_browser_capability.py",
    "git_blob_sha1": "29745ca0f6b79c36a94ae761c40e56461ee1aee4"
  },
  {
    "path": "brain_snapshot/canonical/runtime/promote_pending_binding.py",
    "git_blob_sha1": "f100c0d1ce5a4b07af0175035c3122d816459b0b"
  },
  {
    "path": "brain_snapshot/canonical/runtime/promote_sqlite_capabilities.py",
    "git_blob_sha1": "2a912cf6e67fbcece66b45006af261620cd4b955"
  },
  {
    "path": "brain_snapshot/canonical/runtime/promote_web_release_verifier.py",
    "git_blob_sha1": "ad41701b87ca455a5b8ad39c87bef85bc5a20295"
  },
  {
    "path": "brain_snapshot/canonical/runtime/promote_xlsx_library_capabilities.py",
    "git_blob_sha1": "e5152a02b840ca3dbe8c914fcbcaa28d1996348d"
  },
  {
    "path": "brain_snapshot/canonical/runtime/PROVIDER_POLICY_V1.json",
    "git_blob_sha1": "f74dd63603cb042c107c3743a0af673c272470d8"
  },
  {
    "path": "brain_snapshot/canonical/runtime/python_codec_probe.py",
    "git_blob_sha1": "fc8b5005a9888422e3cb61f6cf0bd147c740ec84"
  },
  {
    "path": "brain_snapshot/canonical/runtime/python_library_contract_inference.py",
    "git_blob_sha1": "95c76425f41136439484507f147f087f5cf1d1f9"
  },
  {
    "path": "brain_snapshot/canonical/runtime/raw_visual_cdp_preflight.py",
    "git_blob_sha1": "c5a60dade4de7871e23446156ab7186067d23f6e"
  },
  {
    "path": "brain_snapshot/canonical/runtime/same_identity_supervisor.py",
    "git_blob_sha1": "47c461f502e840def0c38728e1bfd7c6401cb804"
  },
  {
    "path": "brain_snapshot/canonical/runtime/semantic_authorities.py",
    "git_blob_sha1": "1d74b9c2cdc0e387ab1d64f04c8f38f414f2d80e"
  },
  {
    "path": "brain_snapshot/canonical/runtime/space_cargo_architecture_envelope.py",
    "git_blob_sha1": "7ad18a58e209cb7d742c6e5de4518796582effaa"
  },
  {
    "path": "brain_snapshot/canonical/runtime/verify_browser_python_release.py",
    "git_blob_sha1": "f33c73ed2f9bbdf30e55f24f7e8771784af44a6c"
  },
  {
    "path": "brain_snapshot/canonical/runtime/verify_pending_cli_binding.py",
    "git_blob_sha1": "a6b028c25d79d2dff59c87e3b3ad91d9fe934dae"
  },
  {
    "path": "brain_snapshot/canonical/runtime/verify_pending_python_document_binding.py",
    "git_blob_sha1": "826ef2312ccc9a9dc85658d50519af44e75c42a2"
  },
  {
    "path": "brain_snapshot/canonical/runtime/verify_sqlite_roundtrip.py",
    "git_blob_sha1": "53c6597b4a065c2980c4c33bbf1e8fa5cde1b104"
  },
  {
    "path": "brain_snapshot/canonical/runtime/verify_web_release_verifier.py",
    "git_blob_sha1": "6e263c18f77f82a3b531a6c3bac4d2299d894372"
  },
  {
    "path": "brain_snapshot/canonical/runtime/verify_xlsx_library_roundtrip.py",
    "git_blob_sha1": "6eeb47ef073b16c0f26f49098dc9fa4bb871e1d4"
  },
  {
    "path": "brain_snapshot/canonical/tasks/PARENT-SEISMOLOGY-KAMCHATKA-TSUNAMI-OPEN-RESEARCH-TASK-B-20260930-002.json",
    "git_blob_sha1": "39ed2897a377914876afb97e2bb0d5cb9f3036a8"
  },
  {
    "path": "brain_snapshot/canonical/astra_runtime/missions/PARENT-SEISMOLOGY-KAMCHATKA-TSUNAMI-OPEN-RESEARCH-TASK-B-20260930-002.json",
    "git_blob_sha1": "7063dd27d58104a0b3e29d54170ac6b816d9bb2f"
  },
  {
    "path": "brain_snapshot/canonical/action_intents/2026-09-30_EXECUTE_GUARDED_SEISMOLOGY_TASK_B_V2.json",
    "git_blob_sha1": "c85401a6905b79c5f9b4a3020f1d1be11ecc426c"
  },
  {
    "path": "execution_guard/github_actions_guarded_run_live.py",
    "git_blob_sha1": "30ea2fd2cc548444477c7b234a59129ff8386235"
  },
  {
    "path": "execution_guard/actions_admission.py",
    "git_blob_sha1": "6c46abef66c036f5382d5792b11a82a289b4dd94"
  },
  {
    "path": "execution_guard/github_ref_store_live.py",
    "git_blob_sha1": "a8b0cf3facd91f4d4248bd4d2ed53f72f7d480c3"
  }
],
  "command":["bash","-lc","set -uo pipefail; mkdir -p _terminal; cd brain_snapshot; set +e; ASTRA_DISABLE_MODEL_PLANNER=1 python canonical/runtime/astra_runtime.py canonical/astra_runtime/missions/PARENT-SEISMOLOGY-KAMCHATKA-TSUNAMI-OPEN-RESEARCH-TASK-B-20260930-002.json > ../_terminal/producer.log 2>&1; code=$?; cat ../_terminal/producer.log; printf '%s\\n' \"$code\" > ../_terminal/producer_exit_code.txt; exit \"$code\""],
  "authority":{
    "brain_freeze_pr":515,
    "brain_authorization_pr":517,
    "brain_base_commit":"9c9366e2bc0ee63860007fe17041ec8d8503648f",
    "task_id":"PARENT-SEISMOLOGY-KAMCHATKA-TSUNAMI-OPEN-RESEARCH-TASK-B-20260930-002",
    "no_same_task_replay":True,
    "model_dependency_count":0,
    "incremental_spend_usd":0,
    "snapshot_runtime_file_count":97
  }
}
(ROOT/"guarded_seismology_parent_b_plan.json").write_text(json.dumps(plan,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps({"status":"PLAN_GENERATED","problem_sha256":plan["frozen"]["problem_sha256"],"task_sha256":plan["frozen"]["task_sha256"],"runtime_sha256":plan["frozen"]["runtime_sha256"],"pin_count":len(plan["pinned_files"])},sort_keys=True))
