"""
Configuration management for the OpenAI-compatible API server
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def _safe_int(env_var: str, default: int) -> int:
    """Safely parse integer environment variables with fallback."""
    val = os.getenv(env_var, str(default))
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


class ModelConfig:
    """Configuration for the local LLM"""

    def __init__(self):
        cuda_devices = os.getenv("CUDA_VISIBLE_DEVICES", "0")
        os.environ["CUDA_VISIBLE_DEVICES"] = cuda_devices

        # Model configuration
        self.model_path = os.getenv("MODEL_PATH", "models/qwen2.5-1.5b-instruct-q4_k_m.gguf")
        self.model_name = os.getenv("MODEL_NAME", "qwen2.5-1.5b-instruct")

        # Performance tuning
        self.n_ctx = _safe_int("N_CTX", 4096)
        self.n_threads = _safe_int("N_THREADS", 16)
        self.n_batch = _safe_int("N_BATCH", 512)
        self.n_gpu_layers = _safe_int("N_GPU_LAYERS", 35)
        self.seed = _safe_int("SEED", -1)
        
        # Batching configuration (for concurrent request handling)
        self.batch_enabled = os.getenv("BATCH_ENABLED", "true").lower() == "true"
        self.batch_size = _safe_int("BATCH_SIZE", 4)  # Max requests per batch
        self.batch_timeout_ms = _safe_int("BATCH_TIMEOUT_MS", 100)  # Max wait before processing

        # Behavior toggles
        self.f16_kv = os.getenv("F16_KV", "true").lower() == "true"
        self.verbose = os.getenv("VERBOSE", "false").lower() == "true"
        self.embedding_enabled = os.getenv("EMBEDDING_ENABLED", "false").lower() == "true"

        # API access
        self.api_key = os.getenv("API_KEY", "")

    def validate(self) -> bool:
        """Validate configuration"""
        model_path = Path(self.model_path)
        if not model_path.exists():
            raise FileNotFoundError(
                f"❌ Model file not found at {model_path}. "
                "Please download a GGUF model and place it in the correct location."
            )
        return True


# Global configuration instance
config = ModelConfig()
