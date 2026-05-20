# OpenAI-Compatible Local LLM Server

A FastAPI-based server that provides an OpenAI-compatible API for running local Large Language Models (LLMs) in GGUF format. This allows you to use open-source models like Mistral, Llama 2, and others with any OpenAI-compatible client.

## Features

- ✅ **OpenAI API Compatibility**: Fully compatible with OpenAI's chat completions API
- ✅ **Streaming Support**: Real-time streaming responses using Server-Sent Events (SSE)
- ✅ **Bearer Token Authentication**: Optional API key authentication matching OpenAI's format
- ✅ **Tool/Function Calling**: Support for function calling (compatible with OpenAI format)
- ✅ **Multiple Model Support**: Easy to switch between different GGUF models
- ✅ **Embeddings Support**: Optional embeddings endpoint (requires embedding-capable model)
- ✅ **Configuration Management**: Environment variables for easy configuration
- ✅ **CORS Support**: Built-in CORS middleware for web applications
- ✅ **Token Usage Tracking**: Track prompt and completion token usage
- ✅ **OpenAI Error Format**: Proper error responses matching OpenAI's JSON structure
- ✅ **Production Ready**: Async support with proper error handling

## Quick Start

### 1. Install Requirements

```bash
pip install -r requirements.txt
```

**Note for Mac Users**: If you want to use Metal GPU acceleration:
```bash
CMAKE_ARGS="-DLLAMA_METAL=on" pip install llama-cpp-python --force-reinstall --no-cache-dir
```

### 2. Download a Model

Use the included download script to get popular models:

```bash
# List available models
python download_model.py --list

# Download Mistral 7B (recommended)
python download_model.py mistral-7b-instruct

# Download a smaller model for testing
python download_model.py tinyllama-1.1b
```

Models are downloaded to the `models/` directory.

### 3. Configure the Server

Copy the example environment file:
```bash
cp env.example .env
```

Edit `.env` to match your downloaded model:
```env
MODEL_PATH=models/mistral-7b-instruct-v0.2.Q4_K_M.gguf
MODEL_NAME=mistral-7b-instruct
# To enable authentication, add this line:
# API_KEY=your-super-secret-key
N_CTX=4096
N_THREADS=4
```

### 4. Start the Server

```bash
python3 main.py
```

The server will start on `http://localhost:8000`.

### 5. Test the API

This project includes multiple scripts to test the server's functionality, compatibility, and security.

#### Recommended: Comprehensive Test Suite

The `test_api_suite.sh` script is the best way to test all endpoints. It runs interactively and will prompt you for the server's IP address.

**Step 1: Make the script executable**
```bash
chmod +x test_api_suite.sh
```

**Step 2: Run the script**

*   **To test a server with authentication DISABLED:**
    Run the script without any extra parameters. It will ask for the IP address.
    ```bash
    ./test_api_suite.sh
    ```
    The script will run basic tests and skip the authentication-related ones.

*   **To run the FULL suite against a server with authentication ENABLED:**
    First, ensure an `API_KEY` is set in your server's `.env` file and restart the server. Then, run the script with your admin key set as an environment variable:
    ```bash
    ADMIN_API_KEY="your-super-secret-key" ./test_api_suite.sh
    ```
    This will test every feature, including generating, validating, and revoking a new API key.

#### Basic Python Test Client

For a quick check of the core chat features, you can use `test_client.py`.

```bash
python3 test_client.py
```

## API Endpoints

### List Models
```bash
GET /v1/models
```

### Get Model Details
```bash
GET /v1/models/{model_id}
```

### Chat Completions
```bash
POST /v1/chat/completions
```

Example request:
```json
{
  "model": "mistral-7b-instruct",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"}
  ],
  "temperature": 0.7,
  "max_tokens": 512,
  "stream": false
}
```

## Usage Examples

### Using curl

Non-streaming request:
```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistral-7b-instruct",
    "messages": [{"role": "user", "content": "Hello!"}],
    "temperature": 0.7
  }'
```

Streaming request:
```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistral-7b-instruct",
    "messages": [{"role": "user", "content": "Write a story"}],
    "stream": true
  }'
```

### Using OpenAI Python Client

```python
from openai import OpenAI

# Point to local server
client = OpenAI(
    api_key="your-api-key-here",  # Use the API_KEY from your .env file, or any string if auth is disabled
    base_url="http://localhost:8000/v1"
)

# Create chat completion
response = client.chat.completions.create(
    model="mistral-7b-instruct",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the capital of France?"}
    ]
)

print(response.choices[0].message.content)

# Streaming example
stream = client.chat.completions.create(
    model="mistral-7b-instruct",
    messages=[{"role": "user", "content": "Write a haiku"}],
    stream=True
)

for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

### Using LangChain

```python
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage

# Configure for local server
llm = ChatOpenAI(
    openai_api_base="http://localhost:8000/v1",
    openai_api_key="not-needed",
    model_name="mistral-7b-instruct",
    streaming=True
)

# Use the model
response = llm([HumanMessage(content="Tell me a joke")])
print(response.content)
```

### Using JavaScript/TypeScript

```javascript
const response = await fetch('http://localhost:8000/v1/chat/completions', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer your-api-key-here'  // If auth is enabled
  },
  body: JSON.stringify({
    model: 'mistral-7b-instruct',
    messages: [
      { role: 'user', content: 'Hello!' }
    ],
    temperature: 0.7
  })
});

const data = await response.json();
console.log(data.choices[0].message.content);
```

### Tool/Function Calling

The API supports OpenAI-compatible function calling:

```python
from openai import OpenAI

client = OpenAI(
    api_key="your-api-key",
    base_url="http://localhost:8000/v1"
)

# Define a function
tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get the current weather for a location",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City and state, e.g. San Francisco, CA"
                },
                "unit": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"]
                }
            },
            "required": ["location"]
        }
    }
}]

# Make a request with tools
response = client.chat.completions.create(
    model="mistral-7b-instruct",
    messages=[{"role": "user", "content": "What's the weather in New York?"}],
    tools=tools,
    tool_choice="auto"
)

# Check if the model wants to call a function
if response.choices[0].message.tool_calls:
    for tool_call in response.choices[0].message.tool_calls:
        print(f"Function: {tool_call.function.name}")
        print(f"Arguments: {tool_call.function.arguments}")
```

## Configuration Options

All configuration is done through environment variables (`.env` file):

| Variable | Description | Default |
|----------|-------------|---------|
| `MODEL_PATH` | Path to GGUF model file | `models/mistral-7b-instruct-v0.2.Q2_K.gguf` |
| `MODEL_NAME` | Model identifier for API | `mistral-7b-instruct` |
| `N_CTX` | Context window size | `4096` |
| `N_THREADS` | Number of CPU threads | `4` |
| `N_GPU_LAYERS` | GPU layers to offload | `0` (CPU only) |
| `SEED` | Random seed (-1 for random) | `-1` |
| `F16_KV` | Use 16-bit floats for key/value cache | `true` |
| `VERBOSE` | Enable verbose logging | `false` |
| `API_KEY` | Bearer token for authentication | `""` (disabled) |
| `EMBEDDING_ENABLED` | Enable embeddings endpoint | `false` |

## Available Models

The download script includes several popular models:

| Model ID | Size | Description |
|----------|------|-------------|
| `mistral-7b-instruct` | 4.37 GB | Mistral 7B Instruct v0.2 (Q4_K_M) - Recommended |
| `mistral-7b-instruct-q2` | 3.08 GB | Mistral 7B Instruct v0.2 (Q2_K) - Smaller, lower quality |
| `llama2-7b-chat` | 4.08 GB | Llama 2 7B Chat (Q4_K_M) |
| `codellama-7b-instruct` | 4.08 GB | CodeLlama 7B Instruct (Q4_K_M) - For coding |
| `phi-2` | 1.66 GB | Microsoft Phi-2 (Q4_K_M) - Smaller model |
| `tinyllama-1.1b` | 669 MB | TinyLlama 1.1B Chat - Very small, fast |

## Performance Tips

1. **CPU Optimization**: Adjust `N_THREADS` to match your CPU cores
2. **GPU Acceleration**: 
   - For NVIDIA GPUs: Set `N_GPU_LAYERS` to offload layers to GPU
   - For Mac M1/M2: Reinstall llama-cpp-python with Metal support
3. **Memory Usage**: Lower `N_CTX` if you're running out of memory
4. **Response Speed**: Use smaller quantized models (Q2_K, Q3_K) for faster responses

## Testing Authentication & OpenAI Compliance

The project includes a comprehensive test suite (`test_auth.sh`) that validates:
- Bearer token authentication
- OpenAI-compatible error formats
- Tool/function calling
- Streaming responses
- Embeddings endpoint

### Quick Authentication Test

```bash
# Enable authentication
echo "API_KEY=test-key-123" >> .env

# Restart the server
python main.py

# Run the test suite
./test_auth.sh
```

### Manual Authentication Tests

```bash
# Test auth rejection (no header)
curl http://localhost:8000/v1/models
# Returns: {"error":{"message":"Unauthorized","type":"invalid_request_error",...}}

# Test with valid auth
curl http://localhost:8000/v1/models \
  -H "Authorization: Bearer test-key-123"

# Test chat with tools
curl http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer test-key-123" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistral-7b-instruct",
    "messages": [{"role": "user", "content": "Get weather in NYC"}],
    "tools": [{
      "type": "function",
      "function": {
        "name": "get_weather",
        "description": "Get weather for a location",
        "parameters": {"type": "object", "properties": {"location": {"type": "string"}}}
      }
    }]
  }'
```

## Troubleshooting

### Model not loading
- Ensure the model file exists in the specified path
- Check that you have enough RAM (7B models typically need 4-8GB)
- Try a smaller model if memory is limited

### Slow response times
- Reduce `N_CTX` for faster processing
- Use a smaller quantized model
- Enable GPU acceleration if available
- Increase `N_THREADS` for better CPU utilization

### Connection refused
- Make sure the server is running (`python main.py`)
- Check that port 8000 is not in use
- Verify firewall settings if accessing from another machine

## Project Structure

The codebase has been refactored for modularity and maintainability:

```
openai_local/
├── main.py           # Application entry point and server initialization
├── config.py         # Configuration management
├── models.py         # Pydantic models (OpenAI-compatible)
├── auth.py           # Authentication/Bearer token handling
├── errors.py         # Error handling and formatting
├── utils.py          # Utility functions (prompt formatting, token counting)
├── routes.py         # API endpoints and route handlers
├── test_auth.sh      # Comprehensive authentication and compliance tests
├── test_client.py    # Python test client
├── download_model.py # Model download utility
└── requirements.txt  # Python dependencies
```

### Module Overview

- **`main.py`**: FastAPI app initialization, middleware setup, and server startup
- **`config.py`**: Centralized configuration from environment variables
- **`models.py`**: All OpenAI-compatible Pydantic models for requests/responses
- **`auth.py`**: Bearer token authentication logic
- **`errors.py`**: OpenAI-compliant error response formatting
- **`utils.py`**: Model loading, prompt formatting, token counting, tool parsing
- **`routes.py`**: All API endpoints (`/v1/models`, `/v1/chat/completions`, `/v1/embeddings`)

## Advanced Usage

### Custom Model Integration

To add a new GGUF model:

1. Download the model to the `models/` directory
2. Update `.env` with the model path
3. Restart the server

### Prompt Formatting

The server uses a simple prompt format by default. You can customize the `format_prompt()` function in `main.py` for different models:

```python
def format_prompt(messages: List[ChatMessage]) -> str:
    # Customize based on your model's requirements
    # For example, Llama 2 uses [INST] tags
    pass
```

### Production Deployment

For production use:

1. Use a process manager like `systemd` or `supervisor`
2. Set up a reverse proxy with nginx
3. Enable HTTPS
4. Implement rate limiting
5. Add authentication if needed
6. Monitor resource usage

## License

This project is open source and available under the MIT License.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Uses [llama-cpp-python](https://github.com/abetlen/llama-cpp-python) for model inference
- Compatible with [OpenAI API](https://platform.openai.com/docs/api-reference) specification 

## OpenAI API Compatibility

This server implements the OpenAI API v1 specification, making it a **drop-in replacement** for OpenAI's API. Any client library, SDK, or application that works with OpenAI's API will work seamlessly with this server.

### Why It's OpenAI Compatible

1. **Exact Endpoint Matching**: Uses the same `/v1/*` URL structure as OpenAI
2. **Identical Data Models**: Request and response formats match OpenAI's specification exactly
3. **Authentication Protocol**: Same `Authorization: Bearer <token>` header format
4. **Streaming Support**: Server-Sent Events (SSE) with identical `data:` format
5. **Error Handling**: Matches OpenAI's error response structure
6. **SDK Compatibility**: Works with official OpenAI SDKs without modification

### Compatibility Matrix

| Feature | OpenAI API | This Server | Status |
|---------|------------|------------|---------|
| Chat Completions | `/v1/chat/completions` | `/v1/chat/completions` | ✅ Full |
| Streaming | SSE with `data: [...]` | SSE with `data: [...]` | ✅ Full |
| Models List | `/v1/models` | `/v1/models` | ✅ Full |
| Model Details | `/v1/models/{id}` | `/v1/models/{id}` | ✅ Full |
| Embeddings | `/v1/embeddings` | `/v1/embeddings` | ✅ Full |
| Tool/Function Calling | `tools` parameter | `tools` parameter | ✅ Full |
| Authentication | Bearer token | Bearer token | ✅ Full |
| Error Format | `{"error": {...}}` | `{"error": {...}}` | ✅ Full |

## API Endpoints Documentation

### 📋 List Available Models
**Endpoint**: `GET /v1/models`  
**Authentication**: Optional (Bearer token if configured)  
**OpenAI Equivalent**: Exact match - [models list](https://platform.openai.com/docs/api-reference/models/list)

**Response**:
```json
{
  "object": "list",
  "data": [
    {
      "id": "mistral-7b-instruct",
      "object": "model",
      "created": 1699564800,
      "owned_by": "local",
      "permission": [],
      "root": "mistral-7b-instruct",
      "parent": null
    }
  ]
}
```

### 🔍 Get Model Details
**Endpoint**: `GET /v1/models/{model_id}`  
**Authentication**: Optional (Bearer token if configured)  
**OpenAI Equivalent**: Exact match - [retrieve model](https://platform.openai.com/docs/api-reference/models/retrieve)

**Path Parameters**:
- `model_id`: The ID of the model to retrieve

**Response**:
```json
{
  "id": "mistral-7b-instruct",
  "object": "model",
  "created": 1699564800,
  "owned_by": "local"
}
```

### 💬 Chat Completions
**Endpoint**: `POST /v1/chat/completions`  
**Authentication**: Optional (Bearer token if configured)  
**OpenAI Equivalent**: Exact match - [create chat completion](https://platform.openai.com/docs/api-reference/chat/create)

**Request Body**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `model` | string | Yes | - | Model ID to use |
| `messages` | array | Yes | - | Array of message objects |
| `temperature` | float | No | 0.7 | Sampling temperature (0.0-2.0) |
| `top_p` | float | No | 1.0 | Nucleus sampling (0.0-1.0) |
| `stream` | boolean | No | false | Enable streaming responses |
| `max_tokens` | integer | No | 2048 | Maximum tokens to generate |
| `stop` | string/array | No | null | Stop sequences |
| `presence_penalty` | float | No | 0.0 | Penalize new tokens (-2.0 to 2.0) |
| `frequency_penalty` | float | No | 0.0 | Penalize repeated tokens (-2.0 to 2.0) |
| `seed` | integer | No | null | Random seed for deterministic output |
| `tools` | array | No | null | Available functions for the model to call |
| `tool_choice` | string/object | No | "auto" | Control function calling behavior |

**Example Request**:
```json
{
  "model": "mistral-7b-instruct",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"}
  ],
  "temperature": 0.7,
  "max_tokens": 512,
  "stream": false
}
```

**Standard Response**:
```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1699564823,
  "model": "mistral-7b-instruct",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "Hello! How can I help you today?"
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 25,
    "completion_tokens": 9,
    "total_tokens": 34
  }
}
```

**Streaming Response** (when `stream: true`):
```
data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","created":1699564823,"model":"mistral-7b-instruct","choices":[{"delta":{"role":"assistant"},"index":0,"finish_reason":null}]}

data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","created":1699564823,"model":"mistral-7b-instruct","choices":[{"delta":{"content":"Hello"},"index":0,"finish_reason":null}]}

data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","created":1699564823,"model":"mistral-7b-instruct","choices":[{"delta":{},"index":0,"finish_reason":"stop"}]}

data: [DONE]
```

### 🔢 Create Embeddings
**Endpoint**: `POST /v1/embeddings`  
**Authentication**: Optional (Bearer token if configured)  
**OpenAI Equivalent**: Exact match - [create embeddings](https://platform.openai.com/docs/api-reference/embeddings/create)  
**Note**: Requires `EMBEDDING_ENABLED=true` in configuration

**Request Body**:
```json
{
  "model": "mistral-7b-instruct",
  "input": "The text to encode",
  "encoding_format": "float"
}
```

**Response**:
```json
{
  "object": "list",
  "data": [{
    "object": "embedding",
    "index": 0,
    "embedding": [0.0023, -0.0125, ...]
  }],
  "model": "mistral-7b-instruct",
  "usage": {
    "prompt_tokens": 5,
    "total_tokens": 5
  }
}
```

### 🏥 Health Check
**Endpoint**: `GET /`  
**Authentication**: Not required  
**OpenAI Equivalent**: N/A (additional endpoint for health monitoring)

**Response**:
```json
{
  "message": "OpenAI-compatible API server running",
  "endpoints": {
    "models": "/v1/models",
    "chat_completions": "/v1/chat/completions",
    "embeddings": "/v1/embeddings"
  },
  "authentication": "required"
}
```

## Error Response Format

All errors follow OpenAI's error response structure exactly:

```json
{
  "error": {
    "message": "Error description here",
    "type": "invalid_request_error",
    "param": "temperature",
    "code": "invalid_temperature"
  }
}
```

**Common Error Types**:
- `invalid_request_error` - Invalid parameters or request format
- `model_error` - Model loading or generation errors
- `authentication_error` - Invalid or missing API key
- `rate_limit_error` - Too many requests (if rate limiting enabled)

This documentation:
1. Clearly explains WHY it's OpenAI compatible
2. Shows a compatibility matrix 
3. Documents each endpoint with full details
4. Aligns with the actual implementation in your code
5. Makes it clear this is a drop-in replacement for OpenAI's API

## Phase 6: Deploying and Running the Secure Container

These instructions are for the end-user/client who receives the final, secure application package. The package consists of a Docker image (`openai_local_secure_final.tar`) and a license generation tool (`get_machine_id.py`).

### Step 1: Load the Docker Image

You will receive a Docker image file named `openai_local_secure_final.tar`. Load it into your local Docker registry.

```bash
docker load < openai_local_secure_final.tar
```

After loading, you can verify that the image is available:
```bash
docker images | grep openai_local_secure
```
You should see `openai_local_secure` with the `final` tag.

### Step 2: Generate Your Machine ID

To run the application, you need a license file that is locked to your specific hardware.

1.  You will receive a Python script named `get_machine_id.py`.
2.  Run this script on the **exact machine where you will run the Docker container**.

```bash
python3 get_machine_id.py
```

The script will output a long, unique string. This is your machine ID.

```
Your unique machine ID is:
a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2
```

### Step 3: Request Your License

Copy the machine ID and send it back to the provider (e.g., TagflowAI). They will use this ID to generate a `license.lic` file and send it back to you.

### Step 4: Run the Secure Container

Once you have received your `license.lic` file, place it in a directory on your machine.

Now, run the secure container using the following command. Make sure to replace `/path/to/your/license.lic` with the actual path to your license file.

```bash
docker run -d --rm --name secure-api \
  -p 8002:8002 \
  -v /path/to/your/license.lic:/app/license.lic \
  openai_local_secure:final
```

**Command Breakdown:**
*   `-d`: Runs the container in detached mode (in the background).
*   `--rm`: Automatically removes the container when it stops.
*   `--name secure-api`: Assigns a convenient name to the container.
*   `-p 8002:8002`: Maps port `8002` on your host machine to port `8002` inside the container.
*   `-v /path/to/your/license.lic:/app/license.lic`: **Crucial step.** This mounts your license file into the container where the application expects to find it.
*   `openai_local_secure:final`: The name of the image to run.

### Step 5: Verify the Application is Running

Check the container's logs to ensure it started successfully:

```bash
docker logs secure-api
```

You should see output indicating the server has started, ending with a line like:
`INFO: Uvicorn running on http://0.0.0.0:8002 (Press CTRL+C to quit)`

Finally, test the API endpoint from your machine:
```bash
curl http://localhost:8002/v1/models
```

If it returns a JSON object with model details, your secure server is running correctly.

## Secure Deployment Workflow Overview

This project uses a multi-step process involving code compilation, asset encryption, and hardware-locked licensing to create a secure, deployable package. This ensures that the intellectual property (both the source code and the AI models) is protected when run in a client's environment.

The workflow is divided into two main parts: the **Developer's role** in packaging the application and the **Client's role** in deploying it.

```mermaid
sequenceDiagram
    participant Developer as Developer (TagflowAI)
    participant Client as Client Infrastructure
    participant Container as Secure Container

    box Developer Side: Packaging & License Generation
        Developer->>Developer: 1. Run `generate_keys.py` (Creates public/private keys)
        Developer->>Developer: 2. Run `encrypt_assets.py` (Encrypts models, creates data_key)
        Developer->>Developer: 3. Run `docker build` (Compiles code & packages assets)
        Developer->>Client: 4. Deliver `image.tar` & `get_machine_id.py`
    end

    box Client Side: Deployment
        Client->>Client: 5. Run `get_machine_id.py`
        Client->>Developer: 6. Send unique `machine_id`
    end

    box Developer Side: Packaging & License Generation
        Developer->>Developer: 7. Run `generate_license.py` with client's `machine_id`
        Developer->>Client: 8. Deliver the `license.lic` file
    end

    box Client Side: Deployment
        Client->>Client: 9. Load Docker image (`docker load < image.tar`)
        Client->>Container: 10. Run container with `license.lic` mounted
    end

    box Secure Container: Runtime Verification
        Container->>Container: 11. Verify license signature with internal `public_key.pem`
        Container->>Container: 12. Match `machine_id` from license to container's ID
        Container->>Container: 13. Extract `data_key` from valid license
        Container->>Container: 14. Decrypt models in memory
        Container->>Container: 15. Start application server
    end
```

### Workflow Explained

1.  **Packaging (Developer):**
    *   The developer first generates a master public/private key pair using `generate_keys.py`. The public key is baked into the Docker image, while the private key is kept secret.
    *   All AI models are encrypted using `encrypt_assets.py`. This step also produces a `data_key.key` which is required to decrypt the models.
    *   The `docker build` command is run. This uses a multi-stage `Dockerfile` to compile the Python source code into unreadable `.so` binaries and packages the encrypted models and the public key into a final, secure image.
    *   The final Docker image is saved as a `.tar` file and delivered to the client along with the `get_machine_id.py` script.

2.  **License Generation (Client & Developer):**
    *   The client runs `get_machine_id.py` on their target hardware to get a unique hardware fingerprint.
    *   This ID is sent back to the developer.
    *   The developer uses `generate_license.py`, their secret private key, the client's machine ID, and the `data_key.key` to generate a hardware-locked `license.lic` file.
    *   This license file is sent to the client.

3.  **Deployment (Client):**
    *   The client loads the Docker image and runs the container using the command specified in the deployment instructions, making sure to mount their unique `license.lic` file.

4.  **Runtime Verification (Secure Container):**
    *   On startup, the application uses the embedded public key to verify that the license was signed by the developer.
    *   It then checks that the machine ID inside the license matches the container's own hardware ID.
    *   If both checks pass, it extracts the model decryption key from the license, decrypts the AI models into memory, and starts the server. If either check fails, the application will refuse to start. 