import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { env, pipeline } from "@huggingface/transformers";

const ROOT = process.cwd();
const MODEL_ROOT = path.join(ROOT, "models");
const MODEL_ID = "brain/flan-t5-small";
const MODEL_DIR = path.join(MODEL_ROOT, MODEL_ID);
const MAX_LEARNED_STATE_BYTES = 100_000_000;

function walk(dir) {
  const out = [];
  for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, ent.name);
    if (ent.isDirectory()) out.push(...walk(p));
    else out.push(p);
  }
  return out;
}
function sha256(p) {
  const h = crypto.createHash("sha256");
  h.update(fs.readFileSync(p));
  return h.digest("hex");
}
function norm(s) {
  return String(s ?? "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}
function hasAny(text, alts) {
  const n = norm(text);
  return alts.some(x => n.includes(norm(x)));
}
function sentenceCount(s) {
  return String(s).split(/[.!?]+/).map(x => x.trim()).filter(Boolean).length;
}
function wordCount(s) {
  return norm(s).split(/\s+/).filter(Boolean).length;
}

const files = walk(MODEL_DIR);
const learnedStateBytes = files.reduce((n, p) => n + fs.statSync(p).size, 0);
if (learnedStateBytes >= MAX_LEARNED_STATE_BYTES) {
  throw new Error(`LEARNED_STATE_BUDGET_FAIL:${learnedStateBytes}`);
}

const encoder = path.join(MODEL_DIR, "onnx", "encoder_model_int8.onnx");
const decoder = path.join(MODEL_DIR, "onnx", "decoder_model_merged_int8.onnx");
const expected = {
  [encoder]: "691c4b521a2aad8ff0d1a94e578f507bbfb7b3d939b5b4d233c4a8043a2388dc",
  [decoder]: "a6904917c00588349f11ef2e3196788eb0f699f549889c295c90225f19977974",
};
for (const [p, want] of Object.entries(expected)) {
  const got = sha256(p);
  if (got !== want) throw new Error(`MODEL_HASH_MISMATCH:${path.basename(p)}:${got}`);
}

env.allowLocalModels = true;
env.allowRemoteModels = false;
env.localModelPath = MODEL_ROOT + path.sep;
env.useFSCache = false;

const generator = await pipeline(
  "text2text-generation",
  MODEL_ID,
  {
    dtype: {
      encoder_model: "int8",
      decoder_model_merged: "int8",
    },
  },
);

async function generate(prompt, opts = {}) {
  const out = await generator(prompt, {
    max_new_tokens: opts.max_new_tokens ?? 96,
    do_sample: false,
    num_beams: 1,
    repetition_penalty: 1.05,
  });
  const text = out?.[0]?.generated_text ?? out?.[0]?.text ?? "";
  return String(text).trim();
}

const cases = [
  {
    id: "PARAPHRASE_FACT_PRESERVATION",
    task: "paraphrase",
    input: "The red rover delivered 17 mineral samples to Vega Station on Tuesday.",
    prompt: "Paraphrase this sentence using different wording while preserving every fact exactly: The red rover delivered 17 mineral samples to Vega Station on Tuesday.",
    check(output) {
      return {
        nonempty: wordCount(output) >= 7,
        changed: norm(output) !== norm(this.input),
        preserves_17: hasAny(output, ["17", "seventeen"]),
        preserves_vega: hasAny(output, ["Vega Station"]),
        preserves_tuesday: hasAny(output, ["Tuesday"]),
        preserves_samples: hasAny(output, ["mineral samples", "samples"]),
        preserves_delivery: hasAny(output, ["delivered", "brought", "transported", "carried"]),
      };
    },
  },
  {
    id: "SIMPLIFY_FACT_PRESERVATION",
    task: "simplify",
    input: "Although the autonomous observatory remained operational despite a severe dust storm, its engineers postponed calibration to prevent damage to the sensors.",
    prompt: "Rewrite this in simpler English without losing facts: Although the autonomous observatory remained operational despite a severe dust storm, its engineers postponed calibration to prevent damage to the sensors.",
    check(output) {
      return {
        nonempty: wordCount(output) >= 8,
        not_longer: wordCount(output) <= wordCount(this.input) + 2,
        observatory: hasAny(output, ["observatory"]),
        storm: hasAny(output, ["dust storm", "storm"]),
        engineers: hasAny(output, ["engineers"]),
        calibration: hasAny(output, ["calibration", "calibrate"]),
        sensors: hasAny(output, ["sensors", "sensor"]),
        causal_delay: hasAny(output, ["postponed", "delayed", "waited", "put off"]),
      };
    },
  },
  {
    id: "SUMMARIZE_MULTI_FACT",
    task: "summarize",
    input: "On Monday, the Aster Laboratory launched three research balloons. Two balloons reached an altitude of 20 kilometers and transmitted temperature data for six hours. The third balloon returned early because a valve malfunctioned. Engineers recovered all three payloads by Tuesday morning.",
    prompt: "Summarize the following passage in one concise sentence while preserving the central outcome and the failure: On Monday, the Aster Laboratory launched three research balloons. Two balloons reached an altitude of 20 kilometers and transmitted temperature data for six hours. The third balloon returned early because a valve malfunctioned. Engineers recovered all three payloads by Tuesday morning.",
    check(output) {
      return {
        nonempty: wordCount(output) >= 8,
        shorter: wordCount(output) < wordCount(this.input),
        aster: hasAny(output, ["Aster"]),
        balloons: hasAny(output, ["balloon"]),
        launched_three: hasAny(output, ["three", "3"]),
        valve_failure: hasAny(output, ["valve", "malfunction", "failed", "failure"]),
        recovery: hasAny(output, ["recovered", "recovery", "payloads"]),
      };
    },
  },
  {
    id: "STORY_GROUNDED_GENERATION",
    task: "story_generation",
    input: "Write a short story about Mira finding a copper key in a lighthouse during a storm.",
    prompt: "Write a short coherent story about Mira finding a copper key in a lighthouse during a storm. Include all four details naturally.",
    check(output) {
      return {
        substantive: wordCount(output) >= 20,
        mira: hasAny(output, ["Mira"]),
        copper_key: hasAny(output, ["copper key"]),
        lighthouse: hasAny(output, ["lighthouse"]),
        storm: hasAny(output, ["storm"]),
        narrative_shape: sentenceCount(output) >= 2 || wordCount(output) >= 35,
      };
    },
  },
];

const results = [];
for (const c of cases) {
  const output = await generate(c.prompt, { max_new_tokens: c.task === "story_generation" ? 128 : 80 });
  const checks = c.check(output);
  results.push({
    id: c.id,
    task: c.task,
    prompt: c.prompt,
    output,
    checks,
    pass: Object.values(checks).every(Boolean),
  });
}

const receipt = {
  schema: "PROJECT_BRAIN_SUB100MB_FLAN_T5_SEMANTIC_SEED_FALSIFICATION_V1",
  status: results.every(x => x.pass) ? "PASS_PUBLIC_NONTERMINAL_MINIMUM_SEMANTIC_SEED" : "FALSIFIED_ON_PUBLIC_NONTERMINAL_MINIMUM_SEMANTIC_SEED",
  model: {
    id: "onnx-community/flan-t5-small-ONNX",
    pinned_revision: "76988c16f73cadb2c2e13e2d7d85608944223105",
    runtime_model_id: MODEL_ID,
    dtype: { encoder_model: "int8", decoder_model_merged: "int8" },
    learned_state_bytes: learnedStateBytes,
    learned_state_limit_bytes: MAX_LEARNED_STATE_BYTES,
    below_limit: learnedStateBytes < MAX_LEARNED_STATE_BYTES,
    exact_graph_sha256: Object.fromEntries(Object.entries(expected).map(([p,h]) => [path.relative(MODEL_DIR,p), h])),
    local_only_at_inference: true,
  },
  runtime: {
    transformers_js: "4.3.0",
    model_network_allowed_at_inference: false,
    model_dependency_count: 1,
    incremental_spend_usd: 0,
  },
  public_nonterminal_semantic_checks: {
    passed: results.filter(x => x.pass).length,
    total: results.length,
    all_pass: results.every(x => x.pass),
    results,
  },
  hard_nonclaims: [
    "NO_LIVEBENCH_TERMINAL_CASES_USED",
    "NO_OPUS_5_5_PARITY_CLAIM",
    "NO_GENERAL_SEMANTIC_CAPABILITY_CLAIM_BEYOND_THE_EXACT_PUBLIC_NONTERMINAL_CHECKS",
    "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT_FROM_THIS_RECEIPT_ALONE",
    "NO_CLAIM_THIS_MODEL_ALONE_SATISFIES_LIVEBENCH_FORMAT_CONSTRAINTS",
  ],
  next_if_pass: "BIND_AS_PRECOMMITTED_LOCAL_SEMANTIC_SEED_CANDIDATE_AND_COMPOSE_WITH_SEED_PRESERVING_EXACT_CHECKER_POSTPROCESSING",
  next_if_fail: "REJECT_THIS_CANDIDATE_AND_USE_THE_FAILED_TASK_CLASS_TO_SELECT_THE_NEXT_SMALLEST_WHITE_BOX_LOCAL_PRODUCER",
};

fs.writeFileSync("flan_t5_sub100mb_semantic_seed_receipt.json", JSON.stringify(receipt, null, 2) + "\n");
console.log(JSON.stringify(receipt));
if (!results.every(x => x.pass)) process.exitCode = 2;
