"""
Utility functions for the OpenAI-compatible API
"""

import json
import re
import asyncio
from typing import List, Optional
from pathlib import Path
from llama_cpp import Llama
import os
from models import ChatMessage, Tool, ToolCall, FunctionCall
from config import config

os.environ["CUDA_VISIBLE_DEVICES"] = "0"


# Global model instance (single model for batching)
llm_model: Optional[Llama] = None

# Batch processor instance
_batch_processor = None


def load_model():
    """Load the LLM model"""
    global llm_model
    
    # Validate configuration
    try:
        config.validate()
    except Exception as e:
        print(f"❌ Config validation failed: {e}")
        raise
    
    model_path = Path(config.model_path)
    print(f"🔄 Loading model from {model_path}...")
    print(f"   Config: n_ctx={config.n_ctx}, n_threads={config.n_threads}, n_gpu_layers={config.n_gpu_layers}")
    
    llama_kwargs = {
        "model_path": str(model_path),
        "n_ctx": getattr(config, "n_ctx", 4096),
        "n_threads": getattr(config, "n_threads", 8),
        "n_batch": getattr(config, "n_batch", 512),
        "n_gpu_layers": getattr(config, "n_gpu_layers", -1),
        "use_mmap": True,
        "use_mlock": False,
        "embedding": getattr(config, "embedding_enabled", False),
        "verbose": getattr(config, "verbose", False),
        "seed": getattr(config, "seed", 0),
    }
    
    try:
        llm_model = Llama(**llama_kwargs)
        print(
            f"✅ Model loaded successfully: {config.model_name}\n"
            f"   Context: {llama_kwargs['n_ctx']} | Threads: {llama_kwargs['n_threads']} | "
            f"GPU Layers: {llama_kwargs['n_gpu_layers']}"
        )
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        raise


def get_model() -> Llama:
    """Get the loaded model instance"""
    if not llm_model:
        raise RuntimeError("Model not loaded. Call load_model() first.")
    return llm_model


async def get_batch_processor():
    """Get or create the batch processor"""
    global _batch_processor
    
    if _batch_processor is None:
        from services.batch_processor import BatchProcessor
        
        batch_size = getattr(config, "batch_size", 4)
        batch_timeout = getattr(config, "batch_timeout_ms", 100)
        
        _batch_processor = BatchProcessor(
            llm_model=get_model(),
            max_batch_size=batch_size,
            batch_timeout_ms=batch_timeout
        )
        await _batch_processor.start()
    
    return _batch_processor


async def stop_batch_processor():
    """Stop the batch processor"""
    global _batch_processor
    if _batch_processor:
        await _batch_processor.stop()
        _batch_processor = None


def format_prompt(messages: List[ChatMessage], tools: Optional[List[Tool]] = None) -> str:
    """
    Format messages into a prompt for the model.
    """
    if config.model_name.lower().startswith("qwen"):
        # Qwen Instruct uses ChatML, not the legacy plain role labels.
        prompt = ""
        if tools:
            tool_specs = [tool.model_dump() for tool in tools]
            prompt += "<|im_start|>system\nAvailable tools: " + json.dumps(tool_specs) + "<|im_end|>\n"
        for message in messages:
            content = message.content or ""
            if message.tool_calls:
                content += json.dumps([call.model_dump() for call in message.tool_calls])
            prompt += f"<|im_start|>{message.role}\n{content}<|im_end|>\n"
        return prompt + "<|im_start|>assistant\n"

    prompt = ""
    
    # If tools are provided, add them to system prompt
    if tools:
        tools_description = "You have access to the following functions:\n\n"
        for tool in tools:
            if tool.type == "function":
                func = tool.function
                tools_description += f"Function: {func.name}\n"
                if func.description:
                    tools_description += f"Description: {func.description}\n"
                if func.parameters:
                    tools_description += f"Parameters: {json.dumps(func.parameters, indent=2)}\n"
                tools_description += "\n"
        
        tools_description += (
            "To use a function, respond with a JSON object in this format:\n"
            '{"tool_calls": [{"type": "function", "function": {"name": "function_name", "arguments": "{...}"}}]}\n\n'
        )
        
        # Prepend to first system message or create new one
        system_msg_found = False
        for i, message in enumerate(messages):
            if message.role == "system":
                messages[i].content = tools_description + (message.content or "")
                system_msg_found = True
                break
        
        if not system_msg_found:
            prompt += f"System: {tools_description}\n\n"
    
    for message in messages:
        if message.role == "system":
            prompt += f"System: {message.content}\n\n"
        elif message.role == "user":
            prompt += f"User: {message.content}\n\n"
        elif message.role == "assistant":
            if message.content:
                prompt += f"Assistant: {message.content}\n\n"
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    prompt += f"Assistant called {tool_call.function.name} with {tool_call.function.arguments}\n\n"
        elif message.role == "tool":
            prompt += f"Tool ({message.name}): {message.content}\n\n"
    
    if messages and messages[-1].role != "assistant":
        prompt += "Assistant: "
    
    return prompt


def count_tokens(text: str) -> int:
    """Approximate token count"""
    return len(text) // 4


def parse_tool_calls(response_text: str) -> Optional[List[ToolCall]]:
    """Parse tool calls from response"""
    try:
        json_match = re.search(r'\{.*"tool_calls".*\}', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            data = json.loads(json_str)
            if "tool_calls" in data:
                tool_calls = []
                for tc in data["tool_calls"]:
                    tool_call = ToolCall(
                        type=tc.get("type", "function"),
                        function=FunctionCall(
                            name=tc["function"]["name"],
                            arguments=tc["function"]["arguments"] if isinstance(tc["function"]["arguments"], str) 
                                     else json.dumps(tc["function"]["arguments"])
                        )
                    )
                    tool_calls.append(tool_call)
                return tool_calls
    except (json.JSONDecodeError, KeyError, TypeError):
        pass
    return None


def remove_tool_calls_from_content(text: str) -> str:
    """Remove tool call JSON from content"""
    return re.sub(r'\{.*"tool_calls".*\}', '', text, flags=re.DOTALL).strip()


def print_server_banner():
    """Pretty print server startup info"""
    batch_enabled = getattr(config, "batch_enabled", True)
    batch_size = getattr(config, "batch_size", 4)
    
    print("\n" + "="*60)
    print("🚀 OpenAI-Compatible Local LLM Server")
    print("="*60)
    print(f"Model: {config.model_name}")
    print(f"Model path: {config.model_path}")
    print(f"Context size: {config.n_ctx}")
    print(f"CPU threads: {config.n_threads}")
    print(f"GPU layers: {config.n_gpu_layers}")
    print(f"Batching: {'Enabled' if batch_enabled else 'Disabled'} (max batch size: {batch_size})")
    print(f"Authentication: {'Enabled' if config.api_key else 'Disabled'}")
    print(f"Embeddings: {'Enabled' if config.embedding_enabled else 'Disabled'}")
    print("="*60 + "\n")

    if config.api_key:
        print("⚠️  Authentication is enabled!")
        print(f"   Authorization: Bearer {config.api_key[:10]}..." if len(config.api_key) > 10 else f"   Authorization: Bearer {config.api_key}")
        print()
