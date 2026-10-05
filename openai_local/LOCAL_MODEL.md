# Local model: Qwen2.5 1.5B Instruct

The CPU deployment uses `qwen2.5-1.5b-instruct-q4_k_m.gguf`
(1,117,320,736 bytes) from the official Qwen repository:
https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF

Expected SHA-256:
`6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e`

The Docker bind mount is `/mnt/data/magma-ai/models` -> `/app/models`.
Set these values in `openai_local/.env`:

```dotenv
MODEL_PATH=models/qwen2.5-1.5b-instruct-q4_k_m.gguf
MODEL_NAME=qwen2.5-1.5b-instruct
N_CTX=4096
N_GPU_LAYERS=0
```

Set `OPENAI_MODEL=qwen2.5-1.5b-instruct` in `ms-esdm/.env`.
Keep existing API credentials unchanged. Do not put credentials in this document.

The local runtime dependency is upgraded to llama-cpp-python 0.3.16 for
Qwen2 support. `utils.format_prompt` uses ChatML for Qwen models.
The web model selector retains the stable `local` ID, with a Qwen label.
Changing the chat model does not change the document embedding model and
does not require document re-upload or re-embedding.

After downloading the model, rebuild and recreate only affected services:

```sh
docker compose build openai-local backend
docker compose up -d --no-deps openai-local backend
docker exec esdm-nginx nginx -t
docker exec esdm-nginx nginx -s reload
curl -i http://localhost/api/knowledge/models
```

Backend initialization may take time: wait for it to become healthy before
testing the web endpoint. RAM use is greater than the GGUF file size and
depends on context length and other running services. Test grounded answers
on actual documents before relying on this small model.
