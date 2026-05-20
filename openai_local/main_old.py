"""
OpenAI-compatible API server using local LLMs
Supports chat completions with streaming
"""

import os
import json
import time
import uuid
from typing import List, Optional, Dict, Any, Union, AsyncIterator
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse
from llama_cpp import Llama
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Local OpenAI-Compatible API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global model instance
llm_model = None


# ===================== Authentication =====================

def verify_token(authorization: Optional[str] = Header(None)) -> str:
    """Verify Bearer token from Authorization header"""
    # Get expected token from environment or use a default
    expected_token = os.getenv("API_KEY", "")
    
    # If no token is configured, allow all requests (for local development)
    if not expected_token:
        return "no-auth-required"
    
    # Check if Authorization header is present
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail=create_error_response("Unauthorized", "invalid_request_error", 
                                        "Missing Authorization header", "authorization_missing")
        )
    
    # Check Bearer token format
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail=create_error_response("Unauthorized", "invalid_request_error",
                                        "Invalid Authorization header format", "authorization_invalid")
        )
    
    # Extract and verify token
    token = authorization.replace("Bearer ", "")
    if token != expected_token:
        raise HTTPException(
            status_code=401,
            detail=create_error_response("Unauthorized", "invalid_request_error",
                                        "Invalid API key", "invalid_api_key")
        )
    
    return token


# ===================== Error Handling =====================

def create_error_response(message: str, error_type: str = "invalid_request_error", 
                         param: Optional[str] = None, code: Optional[str] = None) -> Dict:
    """Create OpenAI-compatible error response"""
    error = {
        "message": message,
        "type": error_type,
    }
    if param:
        error["param"] = param
    if code:
        error["code"] = code
    
    return {"error": error}


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with OpenAI-compatible error format"""
    # If detail is already in OpenAI format, use it
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail
        )
    
    # Convert to OpenAI format
    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(str(exc.detail))
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with OpenAI-compatible error format"""
    errors = exc.errors()
    if errors:
        first_error = errors[0]
        param = ".".join(str(loc) for loc in first_error["loc"])
        message = f"{first_error['msg']} at {param}"
    else:
        message = "Invalid request"
        param = None
    
    return JSONResponse(
        status_code=422,
        content=create_error_response(message, "invalid_request_error", param)
    )


# ===================== Data Models (OpenAI Compatible) =====================

class ChatMessage(BaseModel):
    role: str  # "system", "user", "assistant", "tool"
    content: Optional[str] = None
    name: Optional[str] = None
    tool_calls: Optional[List['ToolCall']] = None
    tool_call_id: Optional[str] = None  # For tool responses


class ToolCall(BaseModel):
    id: str = Field(default_factory=lambda: f"call_{uuid.uuid4().hex[:8]}")
    type: str = "function"
    function: 'FunctionCall'


class FunctionCall(BaseModel):
    name: str
    arguments: str  # JSON string of arguments


class Function(BaseModel):
    name: str
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None  # JSON Schema


class Tool(BaseModel):
    type: str = "function"
    function: Function


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)
    n: Optional[int] = Field(default=1, ge=1)
    stream: Optional[bool] = False
    stop: Optional[Union[str, List[str]]] = None
    max_tokens: Optional[int] = Field(default=2048, ge=1)
    presence_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0)
    frequency_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0)
    logit_bias: Optional[Dict[str, float]] = None
    user: Optional[str] = None
    seed: Optional[int] = None
    tools: Optional[List[Tool]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None  # "auto", "none", or specific tool


class ChatCompletionResponseChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: Optional[str] = None  # "stop", "length", "content_filter", "tool_calls", null


class ChatCompletionResponseUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex[:8]}")
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: List[ChatCompletionResponseChoice]
    usage: ChatCompletionResponseUsage
    system_fingerprint: Optional[str] = None


class ChatCompletionStreamResponseDelta(BaseModel):
    role: Optional[str] = None
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None


class ChatCompletionStreamResponseChoice(BaseModel):
    index: int
    delta: ChatCompletionStreamResponseDelta
    finish_reason: Optional[str] = None


class ChatCompletionStreamResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex[:8]}")
    object: str = "chat.completion.chunk"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: List[ChatCompletionStreamResponseChoice]
    system_fingerprint: Optional[str] = None


# Model update for forward references
ChatMessage.model_rebuild()
ToolCall.model_rebuild()


class ModelInfo(BaseModel):
    id: str
    object: str = "model"
    created: int = Field(default_factory=lambda: int(time.time()))
    owned_by: str = "local"
    permission: List = Field(default_factory=list)
    root: str
    parent: Optional[str] = None


class ModelList(BaseModel):
    object: str = "list"
    data: List[ModelInfo]


# ===================== Embeddings Models =====================

class EmbeddingRequest(BaseModel):
    input: Union[str, List[str], List[int], List[List[int]]]
    model: str
    encoding_format: Optional[str] = "float"  # "float" or "base64"


class EmbeddingData(BaseModel):
    object: str = "embedding"
    index: int
    embedding: List[float]


class EmbeddingResponse(BaseModel):
    object: str = "list"
    data: List[EmbeddingData]
    model: str
    usage: Dict[str, int]  # {"prompt_tokens": X, "total_tokens": X}


# ===================== Model Configuration =====================

class ModelConfig:
    """Configuration for the local LLM"""
    
    def __init__(self):
        self.model_path = os.getenv("MODEL_PATH", "models/mistral-7b-instruct-v0.2.Q2_K.gguf")
        self.model_name = os.getenv("MODEL_NAME", "mistral-7b-instruct")
        self.n_ctx = int(os.getenv("N_CTX", "4096"))  # Context window
        self.n_threads = int(os.getenv("N_THREADS", "4"))  # CPU threads
        self.n_gpu_layers = int(os.getenv("N_GPU_LAYERS", "0"))  # GPU layers (0 for CPU only)
        self.seed = int(os.getenv("SEED", "-1"))  # -1 for random
        self.f16_kv = os.getenv("F16_KV", "true").lower() == "true"
        self.verbose = os.getenv("VERBOSE", "false").lower() == "true"
        self.embedding_enabled = os.getenv("EMBEDDING_ENABLED", "false").lower() == "true"
        self.api_key = os.getenv("API_KEY", "")  # Empty means no auth required


config = ModelConfig()


# ===================== Model Management =====================

def load_model():
    """Load the local LLM model"""
    global llm_model
    
    model_path = Path(config.model_path)
    
    if not model_path.exists():
        raise FileNotFoundError(
            f"Model file not found at {model_path}. "
            f"Please download a GGUF model and place it in the correct location."
        )
    
    print(f"Loading model from {model_path}...")
    
    try:
        llm_model = Llama(
            model_path=str(model_path),
            n_ctx=config.n_ctx,
            n_threads=config.n_threads,
            n_gpu_layers=config.n_gpu_layers,
            seed=config.seed if config.seed != -1 else None,
            f16_kv=config.f16_kv,
            verbose=config.verbose,
            embedding=config.embedding_enabled,  # Enable embeddings if configured
        )
        print(f"Model loaded successfully: {config.model_name}")
    except Exception as e:
        print(f"Error loading model: {e}")
        raise


def format_prompt(messages: List[ChatMessage], tools: Optional[List[Tool]] = None) -> str:
    """
    Format messages into a prompt for the model.
    This uses a simple format, but you can customize based on your model.
    """
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
                # Format tool calls in the conversation
                for tool_call in message.tool_calls:
                    prompt += f"Assistant called {tool_call.function.name} with {tool_call.function.arguments}\n\n"
        elif message.role == "tool":
            prompt += f"Tool ({message.name}): {message.content}\n\n"
    
    # Add the assistant prefix to prompt for response
    if messages and messages[-1].role != "assistant":
        prompt += "Assistant: "
    
    return prompt


def count_tokens(text: str) -> int:
    """Approximate token count (you may want to use the actual tokenizer)"""
    # Rough estimation: ~4 characters per token
    return len(text) // 4


def parse_tool_calls(response_text: str) -> Optional[List[ToolCall]]:
    """
    Try to parse tool calls from the model's response.
    This is a simple implementation - you may need to customize based on your model.
    """
    try:
        # Look for JSON object in the response
        import re
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


# ===================== API Endpoints =====================

@app.on_event("startup")
async def startup_event():
    """Load the model when the server starts"""
    load_model()


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "OpenAI-compatible API server running",
        "endpoints": {
            "models": "/v1/models",
            "chat_completions": "/v1/chat/completions",
            "embeddings": "/v1/embeddings" if config.embedding_enabled else None,
        },
        "authentication": "required" if config.api_key else "not required"
    }


@app.get("/v1/models", response_model=ModelList)
async def list_models(token: str = Depends(verify_token)):
    """List available models (OpenAI compatible)"""
    return ModelList(
        object="list",
        data=[
            ModelInfo(
                id=config.model_name,
                object="model",
                created=int(time.time()),
                owned_by="local",
                permission=[],
                root=config.model_name,
                parent=None,
            )
        ]
    )


@app.get("/v1/models/{model_id}")
async def get_model(model_id: str, token: str = Depends(verify_token)):
    """Get model information"""
    if model_id != config.model_name:
        raise HTTPException(
            status_code=404, 
            detail=create_error_response(f"Model {model_id} not found", "model_not_found")
        )
    
    return ModelInfo(
        id=config.model_name,
        object="model",
        created=int(time.time()),
        owned_by="local",
        permission=[],
        root=config.model_name,
        parent=None,
    )


async def generate_stream_response(
    prompt: str,
    request: ChatCompletionRequest,
    request_id: str,
    tools: Optional[List[Tool]] = None
) -> AsyncIterator[str]:
    """Generate streaming response"""
    
    # Configure generation parameters
    generation_kwargs = {
        "max_tokens": request.max_tokens,
        "temperature": request.temperature,
        "top_p": request.top_p,
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
    
    # Stream the response
    try:
        stream = llm_model(prompt, **generation_kwargs)
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
        
        # Check if we should parse for tool calls
        finish_reason = "stop"
        if tools:
            tool_calls = parse_tool_calls(full_response)
            if tool_calls:
                finish_reason = "tool_calls"
                # Send tool calls in final chunk
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
        
        # Send final chunk with finish reason
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


@app.post("/v1/chat/completions")
async def create_chat_completion(request: ChatCompletionRequest, token: str = Depends(verify_token)):
    """Create a chat completion (OpenAI compatible)"""
    
    if not llm_model:
        raise HTTPException(
            status_code=500, 
            detail=create_error_response("Model not loaded", "model_error")
        )
    
    # Validate model name
    if request.model != config.model_name:
        # Allow any model name for compatibility, but use our loaded model
        pass
    
    # Format the prompt
    prompt = format_prompt(request.messages, request.tools)
    
    request_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
    
    # Handle streaming
    if request.stream:
        return EventSourceResponse(
            generate_stream_response(prompt, request, request_id, request.tools),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
    
    # Non-streaming response
    try:
        generation_kwargs = {
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "stop": request.stop if isinstance(request.stop, list) else [request.stop] if request.stop else [],
        }
        
        # Generate response
        output = llm_model(prompt, **generation_kwargs)
        
        # Extract generated text
        generated_text = output.get("choices", [{}])[0].get("text", "")
        
        # Check for tool calls
        finish_reason = "stop"
        tool_calls = None
        
        if request.tools:
            tool_calls = parse_tool_calls(generated_text)
            if tool_calls:
                finish_reason = "tool_calls"
                # Remove the JSON from the content if tool calls were found
                import re
                generated_text = re.sub(r'\{.*"tool_calls".*\}', '', generated_text, flags=re.DOTALL).strip()
        
        # Calculate token usage
        prompt_tokens = count_tokens(prompt)
        completion_tokens = count_tokens(generated_text)
        
        # Build response message
        response_message = ChatMessage(role="assistant", content=generated_text)
        if tool_calls:
            response_message.tool_calls = tool_calls
        
        # Build response
        response = ChatCompletionResponse(
            id=request_id,
            model=request.model,
            choices=[
                ChatCompletionResponseChoice(
                    index=0,
                    message=response_message,
                    finish_reason=finish_reason
                )
            ],
            usage=ChatCompletionResponseUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens
            )
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=create_error_response(f"Error generating response: {str(e)}", "generation_error")
        )


@app.post("/v1/embeddings")
async def create_embeddings(request: EmbeddingRequest, token: str = Depends(verify_token)):
    """Create embeddings (OpenAI compatible)"""
    
    if not config.embedding_enabled:
        raise HTTPException(
            status_code=404,
            detail=create_error_response("Embeddings endpoint is not enabled", "feature_not_enabled")
        )
    
    if not llm_model:
        raise HTTPException(
            status_code=500,
            detail=create_error_response("Model not loaded", "model_error")
        )
    
    try:
        # Handle different input types
        if isinstance(request.input, str):
            texts = [request.input]
        elif isinstance(request.input, list) and all(isinstance(x, str) for x in request.input):
            texts = request.input
        else:
            raise HTTPException(
                status_code=400,
                detail=create_error_response("Invalid input format", "invalid_request_error", "input")
            )
        
        # Generate embeddings
        embeddings_data = []
        total_tokens = 0
        
        for i, text in enumerate(texts):
            # Generate embedding using llama.cpp
            embedding = llm_model.embed(text)
            
            embeddings_data.append(
                EmbeddingData(
                    object="embedding",
                    index=i,
                    embedding=embedding
                )
            )
            total_tokens += count_tokens(text)
        
        # Build response
        response = EmbeddingResponse(
            object="list",
            data=embeddings_data,
            model=request.model,
            usage={
                "prompt_tokens": total_tokens,
                "total_tokens": total_tokens
            }
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=create_error_response(f"Error generating embeddings: {str(e)}", "generation_error")
        )


# ===================== Main =====================

if __name__ == "__main__":
    # Create models directory if it doesn't exist
    Path("models").mkdir(exist_ok=True)
    
    print("Starting OpenAI-compatible API server...")
    print(f"Model: {config.model_name}")
    print(f"Model path: {config.model_path}")
    print(f"Context size: {config.n_ctx}")
    print(f"CPU threads: {config.n_threads}")
    print(f"GPU layers: {config.n_gpu_layers}")
    print(f"Authentication: {'Enabled' if config.api_key else 'Disabled'}")
    print(f"Embeddings: {'Enabled' if config.embedding_enabled else 'Disabled'}")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
