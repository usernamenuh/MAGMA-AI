from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError, HTTPException
import uvicorn
from pathlib import Path
import os
from config import config
from routes import router
from errors import http_exception_handler, validation_exception_handler
from utils import load_model, get_model, get_batch_processor, stop_batch_processor
from utils import print_server_banner  

os.environ["CUDA_VISIBLE_DEVICES"] = "0" 

app = FastAPI(
    title="Local OpenAI-Compatible API",
    version="2.0.0",
    description="OpenAI-compatible API server for running local LLMs"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# Routes
app.include_router(router)


@app.on_event("startup")
async def startup_event():
    Path("models").mkdir(exist_ok=True)
    print(f"Startup: MODEL_PATH = {config.model_path}")
    print(f"Startup: MODEL_NAME = {config.model_name}")

    try:
        # Load the model
        load_model()
        llm_model = get_model()
        
        # Warm-up inference
        llm_model("Hello, warm-up", max_tokens=1)
        print("✅ Model loaded and warmed up")
        
        # Start batch processor if enabled
        if getattr(config, "batch_enabled", True):
            batch_processor = await get_batch_processor()
            print(f"✅ Batch processor started (size={config.batch_size}, timeout={config.batch_timeout_ms}ms)")
        
    except Exception as e:
        print(f"❌ Failed to load model: {e}")
        print("Server will start but model operations will fail")


@app.on_event("shutdown")
async def shutdown_event():
    print("Shutting down server...")
    await stop_batch_processor()
    print("✅ Batch processor stopped")


if __name__ == "__main__":
    print_server_banner()  
    uvicorn.run(app, host="0.0.0.0", port=8002, log_level="info")

