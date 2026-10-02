import json, statistics
from pathlib import Path

import torch
from huggingface_hub import snapshot_download
from transformers import AutoModelForCausalLM, AutoTokenizer

PROBE = json.loads(Path("verification/m0a_olmo_contrastive_dev.json").read_text())
REPO = "allenai/OLMo-2-0425-1B"
REV = "a1847dff35000b4271fa70afc5db10fd29fedbdf"
LAYERS = [1, 11]
GROUP_COUNT = 8

def mean_logprob(model, tok, source, candidate):
    prompt = source + "\nResolution:"
    p = tok(prompt, add_special_tokens=False)["input_ids"]
    c = tok(candidate, add_special_tokens=False)["input_ids"]
    ids = torch.tensor([p + c], dtype=torch.long)
    with torch.inference_mode():
        logits = model(input_ids=ids, use_cache=False).logits[0]
        lp = torch.log_softmax(logits, dim=-1)
    vals = [float(lp[j - 1, tid]) for j, tid in enumerate(c, start=len(p))]
    return sum(vals) / len(vals)

def evaluate(model, tok):
    rows = []
    for case in PROBE["cases"]:
        a = mean_logprob(model, tok, case["source"], case["correct"])
        b = mean_logprob(model, tok, case["source"], case["wrong"])
        rows.append({
            "id": case["id"],
            "margin": a - b,
            "correct_preferred": a > b,
        })
    return {
        "correct_count": sum(x["correct_preferred"] for x in rows),
        "accuracy": sum(x["correct_preferred"] for x in rows) / len(rows),
        "mean_margin": statistics.mean(x["margin"] for x in rows),
        "rows": rows,
    }

def group_bounds(width, group_index):
    q, r = divmod(width, GROUP_COUNT)
    start = group_index * q + min(group_index, r)
    end = start + q + (1 if group_index < r else 0)
    return start, end

def zero_group_pre_hook(group_index):
    def hook(module, args):
        if not args or not isinstance(args[0], torch.Tensor):
            raise RuntimeError("down_proj input tensor not found")
        x = args[0]
        width = x.shape[-1]
        start, end = group_bounds(width, group_index)
        y = x.clone()
        y[..., start:end] = 0
        return (y,) + tuple(args[1:])
    return hook

path = snapshot_download(
    repo_id=REPO,
    revision=REV,
    local_dir="/tmp/olmo2_1b_mlp_subspace",
    allow_patterns=["*.json", "*.txt", "*.model", "*.safetensors"],
)
tok = AutoTokenizer.from_pretrained(path, local_files_only=True)
model = AutoModelForCausalLM.from_pretrained(
    path,
    local_files_only=True,
    dtype="auto",
    low_cpu_mem_usage=True,
    device_map={"": "cpu"},
)
model.eval()

baseline = evaluate(model, tok)
base_by = {x["id"]: x for x in baseline["rows"]}
baseline_correct_ids = [x["id"] for x in baseline["rows"] if x["correct_preferred"]]
baseline_correct_mean = statistics.mean(base_by[i]["margin"] for i in baseline_correct_ids)

rows = []
for layer_id in LAYERS:
    layer = model.model.layers[layer_id]
    down_proj = getattr(layer.mlp, "down_proj", None)
    if down_proj is None:
        raise RuntimeError(f"layer {layer_id} MLP has no down_proj")
    for group_index in range(GROUP_COUNT):
        handle = down_proj.register_forward_pre_hook(zero_group_pre_hook(group_index))
        try:
            ab = evaluate(model, tok)
        finally:
            handle.remove()

        ab_by = {x["id"]: x for x in ab["rows"]}
        flips = [
            case_id
            for case_id in baseline_correct_ids
            if not ab_by[case_id]["correct_preferred"]
        ]
        loss = baseline["mean_margin"] - ab["mean_margin"]
        useful_mean = statistics.mean(ab_by[i]["margin"] for i in baseline_correct_ids)
        useful_loss = baseline_correct_mean - useful_mean
        start, end = group_bounds(down_proj.in_features, group_index)
        rows.append({
            "layer": layer_id,
            "group_index": group_index,
            "channel_start_inclusive": start,
            "channel_end_exclusive": end,
            "channel_count": end - start,
            "ablated_correct_count": ab["correct_count"],
            "ablated_accuracy": ab["accuracy"],
            "ablated_mean_margin": ab["mean_margin"],
            "baseline_minus_ablated_mean_margin": loss,
            "baseline_correct_subset_mean_margin": useful_mean,
            "baseline_correct_subset_margin_loss": useful_loss,
            "baseline_correct_to_wrong_flips": flips,
            "per_case_margin_delta": {
                case_id: base_by[case_id]["margin"] - ab_by[case_id]["margin"]
                for case_id in base_by
            },
            "material": loss >= 0.10 or bool(flips),
        })

rows.sort(
    key=lambda x: (
        -x["baseline_minus_ablated_mean_margin"],
        -len(x["baseline_correct_to_wrong_flips"]),
        x["layer"],
        x["group_index"],
    )
)

out = {
    "schema": "PROJECT_BRAIN_M0A_OLMO_MLP_SUBSPACE_CAUSAL_LOCALIZATION_RESULT_V1",
    "donor_repo": REPO,
    "donor_resolved_hf_sha": REV,
    "admissible_mlp_layers": LAYERS,
    "group_count_per_layer": GROUP_COUNT,
    "intervention": "ZERO_ONE_CONTIGUOUS_NEAR_EQUAL_GROUP_AT_SELECTED_MLP_DOWN_PROJECTION_INPUT",
    "baseline": baseline,
    "baseline_correct_case_ids": baseline_correct_ids,
    "baseline_correct_subset_mean_margin": baseline_correct_mean,
    "material_rule": "BASELINE_MEAN_MARGIN_MINUS_ABLATED_MEAN_MARGIN_GE_0_10_OR_ANY_BASELINE_CORRECT_CASE_FLIPS_WRONG",
    "ranked_group_ablation": rows,
    "material_groups": [
        {
            "layer": x["layer"],
            "group_index": x["group_index"],
            "channel_start_inclusive": x["channel_start_inclusive"],
            "channel_end_exclusive": x["channel_end_exclusive"],
        }
        for x in rows if x["material"]
    ],
    "classification": (
        "MATERIAL_SUBSPACES_LOCALIZED"
        if any(x["material"] for x in rows)
        else "DISTRIBUTED_WITHIN_MATERIAL_MLP_BRANCHES_AT_EIGHT_GROUP_GRANULARITY"
    ),
    "known_boundary": "NECESSITY_ON_FROZEN_DEV_ONLY__NOT_SUFFICIENCY__NOT_OWNERSHIP__NOT_SEMANTIC_AUTHORITY",
    "heldout_exposed": 0,
    "fresh_terminal_evidence_consumed": 0,
    "capability_credit": False,
    "family_credit": False,
    "incremental_spend_usd": 0,
}
print("RESULT_JSON=" + json.dumps(out, sort_keys=True))
