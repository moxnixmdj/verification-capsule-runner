from __future__ import annotations
import asyncio, json, os
from types import SimpleNamespace

from verifiers.types import ClientConfig, SystemMessage, ToolMessage, UserMessage
from automationbench.clients import RetryingOpenAIChatCompletionsClient

MODEL="brain-qwen3.5-9b"
BASE="http://127.0.0.1:8080/v1"

async def main():
    os.environ["OPENAI_API_KEY"]="dummy-local-key"
    client=RetryingOpenAIChatCompletionsClient(
        ClientConfig(api_key_var="OPENAI_API_KEY", api_base_url=BASE)
    )
    tool=SimpleNamespace(
        name="echo_tool",
        description="Echo one string value.",
        parameters={
            "type":"object",
            "properties":{"value":{"type":"string"}},
            "required":["value"],
            "additionalProperties":False,
        },
    )
    messages=[
        SystemMessage(content="When a requested action has a provided tool, use the tool."),
        UserMessage(content="Call echo_tool with value exactly automationbench_carrier_probe_20261003. Do not answer normally."),
    ]
    native_prompt, extra=await client.to_native_prompt(messages)
    native_tool=await client.to_native_tool(tool)
    response=await client.get_native_response(
        native_prompt,
        MODEL,
        {"temperature":0, "n":1, "max_tokens":128},
        tools=[native_tool],
        **extra,
    )
    parsed=await client.from_native_response(response)
    calls=parsed.message.tool_calls or []
    assert calls, parsed
    call=next((c for c in calls if c.name=="echo_tool"), None)
    assert call is not None, parsed
    args=json.loads(call.arguments or "{}")
    assert args.get("value")=="automationbench_carrier_probe_20261003", args

    # Prove the exact benchmark client can serialize the post-tool transcript too.
    roundtrip_messages=[
        *messages,
        parsed.message,
        ToolMessage(content=json.dumps({"echo":"automationbench_carrier_probe_20261003"}), tool_call_id=call.id),
    ]
    native_roundtrip, _ = await client.to_native_prompt(roundtrip_messages)
    assert native_roundtrip, native_roundtrip

    verdict={
        "schema":"PROJECT_BRAIN_AUTOMATIONBENCH_LOCAL_QWEN_EXACT_CLIENT_PREFLIGHT_V1",
        "automationbench_dataset_loaded":False,
        "benchmark_task_exposed":False,
        "model":MODEL,
        "base_url":BASE,
        "tool_calls_present":True,
        "selected_tool":"echo_tool",
        "arguments":args,
        "finish_reason":parsed.message.finish_reason,
        "post_tool_transcript_serializes":True,
        "incremental_spend_usd":0,
        "terminal_results_observed":0,
        "family_credit_delta":0,
    }
    print(json.dumps(verdict,sort_keys=True))
    open("AUTOMATIONBENCH_LOCAL_QWEN_EXACT_CLIENT_PREFLIGHT_V1.json","w",encoding="utf-8").write(json.dumps(verdict,indent=2,sort_keys=True)+"\n")
    close=getattr(client,"close",None)
    if close:
        maybe=close()
        if hasattr(maybe,"__await__"):
            await maybe

if __name__=="__main__":
    asyncio.run(main())
