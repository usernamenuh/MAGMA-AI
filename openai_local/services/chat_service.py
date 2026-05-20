from typing import AsyncIterator, Optional, List
from models import (
    ChatCompletionRequest, ChatCompletionResponse, 
    ChatCompletionStreamResponse, ChatCompletionResponseUsage, 
    ChatMessage, Tool, ChatCompletionStreamResponseChoice, ChatCompletionStreamResponseDelta
)
from utils import get_model, get_batch_processor, format_prompt, count_tokens, parse_tool_calls, remove_tool_calls_from_content
import json, re
from models import ToolCall, FunctionCall
import asyncio


def parse_tool_calls_from_content(text: str):
    """Extract tool calls from generated text if model outputs special syntax"""
    tool_calls = []
    matches = re.findall(r"<tool_call>(.*?)</tool_call>", text, re.DOTALL)
    for i, match in enumerate(matches):
        try:
            data = json.loads(match.strip())
            tool_calls.append(ToolCall(
                id=f"call_{i}",
                function=FunctionCall(
                    name=data["name"],
                    arguments=json.dumps(data.get("arguments", {}))
                )
            ))
        except Exception:
            continue
    return tool_calls if tool_calls else None


def remove_tool_calls_tags(text: str) -> str:
    return re.sub(r"<tool_call>.*?</tool_call>", "", text, flags=re.DOTALL).strip()


async def generate_stream_response(
    request: ChatCompletionRequest,
    request_id: str,
    tools: Optional[List[Tool]] = None
) -> AsyncIterator[str]:
    """
    Generate streaming response (OpenAI-compatible SSE format).
    Note: Streaming cannot be batched, so it uses direct model access.
    """
    llm_model = get_model()
    prompt = format_prompt(request.messages, request.tools)

    generation_kwargs = {
        "max_tokens": request.max_tokens or 512,
        "temperature": request.temperature or 0.7,
        "top_p": request.top_p or 0.9,
        "stop": request.stop if isinstance(request.stop, list) else [request.stop] if request.stop else [],
        "stream": True,
    }

    # Send initial chunk with role
    initial_chunk = ChatCompletionStreamResponse(
        id=request_id,
        model=request.model,
        choices=[
            ChatCompletionStreamResponseChoice(
                index=0,
                delta=ChatCompletionStreamResponseDelta(role="assistant"),
                finish_reason=None
            )
        ]
    )
    yield f"data: {initial_chunk.model_dump_json()}\n\n"
    
    # Stream the response (cannot be batched)
    try:
        stream = await asyncio.to_thread(llm_model, prompt, **generation_kwargs)
        full_response = ""
        
        for output in stream:
            chunk = output.get("choices", [{}])[0]
            text = chunk.get("text", "")
            full_response += text
            
            if text:
                stream_chunk = ChatCompletionStreamResponse(
                    id=request_id,
                    model=request.model,
                    choices=[
                        ChatCompletionStreamResponseChoice(
                            index=0,
                            delta=ChatCompletionStreamResponseDelta(content=text),
                            finish_reason=None
                        )
                    ]
                )
                yield f"data: {stream_chunk.model_dump_json()}\n\n"
        
        # Check for tool calls
        finish_reason = "stop"
        if tools:
            tool_calls = parse_tool_calls_from_content(full_response)
            if tool_calls:
                finish_reason = "tool_calls"
                tool_chunk = ChatCompletionStreamResponse(
                    id=request_id,
                    model=request.model,
                    choices=[
                        ChatCompletionStreamResponseChoice(
                            index=0,
                            delta=ChatCompletionStreamResponseDelta(tool_calls=tool_calls),
                            finish_reason=None
                        )
                    ]
                )
                yield f"data: {tool_chunk.model_dump_json()}\n\n"
        
        # Send final chunk
        final_chunk = ChatCompletionStreamResponse(
            id=request_id,
            model=request.model,
            choices=[
                ChatCompletionStreamResponseChoice(
                    index=0,
                    delta=ChatCompletionStreamResponseDelta(),
                    finish_reason=finish_reason
                )
            ]
        )
        yield f"data: {final_chunk.model_dump_json()}\n\n"
        yield "data: [DONE]\n\n"
    except Exception as e:
        error_msg = f"Error during generation: {str(e)}"
        yield f"data: {{\"error\": \"{error_msg}\"}}\n\n"


async def handle_chat_completion(request: ChatCompletionRequest, request_id: str):
    """
    Non-streaming chat completion with batching support.
    Requests are queued and processed in batches for higher throughput.
    """
    prompt = format_prompt(request.messages, request.tools)

    # Generation kwargs
    generation_kwargs = {
        "max_tokens": request.max_tokens or 512,
        "temperature": request.temperature or 0.7,
        "top_p": request.top_p or 0.9,
        "top_k": 40,
        "repeat_penalty": 1.1,
        "stop": request.stop if isinstance(request.stop, list)
                else [request.stop] if request.stop
                else [],
    }

    # Submit to batch processor
    batch_processor = await get_batch_processor()
    output = await batch_processor.submit(prompt, generation_kwargs)
    
    # Handle potential error in output
    if "error" in output:
        raise Exception(output["error"])
    
    # Extract generated text
    generated_text = output.get("choices", [{}])[0].get("text", "").strip()

    # Handle potential tool calls
    tool_calls = None
    finish_reason = "stop"
    if request.tools:
        tool_calls = parse_tool_calls(generated_text)
        if tool_calls:
            finish_reason = "tool_calls"
            generated_text = remove_tool_calls_from_content(generated_text)

    # Token usage
    prompt_tokens = count_tokens(prompt)
    completion_tokens = count_tokens(generated_text)

    response_message = ChatMessage(role="assistant", content=None)
    if tool_calls:
        response_message.tool_calls = tool_calls
    else:
        response_message.content = generated_text

    return ChatCompletionResponse(
        id=request_id,
        model=request.model,
        choices=[{
            "index": 0,
            "message": response_message,
            "finish_reason": finish_reason,
        }],
        usage=ChatCompletionResponseUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        ),
    )
