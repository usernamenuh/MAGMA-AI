#!/usr/bin/env python3
"""
Download GGUF models from Hugging Face for local use
"""

import os
import sys
import argparse
from pathlib import Path
import requests
from tqdm import tqdm

# Popular GGUF models
MODELS = {
    "qwen2.5-1.5b-instruct": {
        "url": "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf",
        "filename": "qwen2.5-1.5b-instruct-q4_k_m.gguf",
        "size": "1.12 GB",
        "description": "Qwen2.5 1.5B Instruct - Q4_K_M (CPU-friendly)"
    },
    "mistral-7b-instruct": {
        "url": "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf",
        "filename": "mistral-7b-instruct-v0.2.Q4_K_M.gguf",
        "size": "4.37 GB",
        "description": "Mistral 7B Instruct v0.2 - Q4_K_M quantization (recommended)"
    },
    "mistral-7b-instruct-q2": {
        "url": "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q2_K.gguf",
        "filename": "mistral-7b-instruct-v0.2.Q2_K.gguf",
        "size": "3.08 GB",
        "description": "Mistral 7B Instruct v0.2 - Q2_K quantization (smaller, lower quality)"
    },
    "llama2-7b-chat": {
        "url": "https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/resolve/main/llama-2-7b-chat.Q4_K_M.gguf",
        "filename": "llama-2-7b-chat.Q4_K_M.gguf",
        "size": "4.08 GB",
        "description": "Llama 2 7B Chat - Q4_K_M quantization"
    },
    "codellama-7b-instruct": {
        "url": "https://huggingface.co/TheBloke/CodeLlama-7B-Instruct-GGUF/resolve/main/codellama-7b-instruct.Q4_K_M.gguf",
        "filename": "codellama-7b-instruct.Q4_K_M.gguf",
        "size": "4.08 GB",
        "description": "CodeLlama 7B Instruct - Q4_K_M quantization (for coding tasks)"
    },
    "phi-2": {
        "url": "https://huggingface.co/TheBloke/phi-2-GGUF/resolve/main/phi-2.Q4_K_M.gguf",
        "filename": "phi-2.Q4_K_M.gguf",
        "size": "1.66 GB",
        "description": "Microsoft Phi-2 - Q4_K_M quantization (smaller model)"
    },
    "tinyllama-1.1b": {
        "url": "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
        "filename": "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
        "size": "669 MB",
        "description": "TinyLlama 1.1B Chat - Q4_K_M quantization (very small model)"
    },
    "qwen2.5-3b-instruct": {
    "url": "https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q5_k_m.gguf",
    "filename": "Qwen2.5-3B-Instruct-Q5_K_M.gguf",
    "size": "2.22 GB",
    "description": "Qwen2.5 3B Instruct - Q5_K_M quantization (high quality)"
    },
    "llama3-8b-cpt-sahabatai": {
    "url": "https://huggingface.co/Chemin-AI/llama3-8b-cpt-sahabatai-v1-instruct-gguf/resolve/main/llama3-8b-cpt-sahabatai-v1-instruct.q5_k_m.gguf",
    "filename": "llama3-8b-cpt-sahabatai-v1-instruct.q5_k_m.gguf",
    "size": "5.73 GB",
    "description": "Llama3 8B CPT Sahabatai v1 Instruct - Q5_K_M quantization (high quality)"
    },
    "Llama-SEA-LION-v3.5-8B-R": {
    "url": "https://huggingface.co/aisingapore/Llama-SEA-LION-v3.5-8B-R-GGUF/resolve/main/Llama-SEA-LION-v3.5-8B-R-Q5_K_M.gguf",
    "filename": "Llama-SEA-LION-v3.5-8B-R-Q5_K_M.gguf",
    "size": "5.73 GB",
    "description": "Llama SEA LION v3.5 8B R - Q5_K_M quantization (high quality)"
    },
    "komodo-7b-base-GGUF": {
    "url": "https://huggingface.co/QuantFactory/komodo-7b-base-GGUF/resolve/main/komodo-7b-base.Q5_K_M.gguf",
    "filename": "komodo-7b-base.Q5_K_M.gguf",
    "size": "4.8 GB",
    "description": "Komodo 7B Base - Q5_K_M quantization (high quality)"
    }
}


def download_file(url: str, destination: Path, chunk_size: int = 8192):
    """Download a file with progress bar"""
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    total_size = int(response.headers.get('content-length', 0))
    
    with open(destination, 'wb') as f:
        with tqdm(total=total_size, unit='iB', unit_scale=True, desc=destination.name) as pbar:
            for chunk in response.iter_content(chunk_size=chunk_size):
                size = f.write(chunk)
                pbar.update(size)
    
    return destination


def list_models():
    """List all available models"""
    print("\nAvailable models:\n")
    print("-" * 80)
    for key, model in MODELS.items():
        print(f"\nModel ID: {key}")
        print(f"  Description: {model['description']}")
        print(f"  Size: {model['size']}")
        print(f"  Filename: {model['filename']}")
    print("-" * 80)


def download_model(model_id: str, models_dir: Path):
    """Download a specific model"""
    if model_id not in MODELS:
        print(f"Error: Model '{model_id}' not found.")
        print("\nAvailable models:")
        for key in MODELS.keys():
            print(f"  - {key}")
        return False
    
    model = MODELS[model_id]
    destination = models_dir / model['filename']
    
    if destination.exists():
        print(f"Model already exists at {destination}")
        overwrite = input("Do you want to re-download it? (y/N): ").lower().strip()
        if overwrite != 'y':
            print("Download cancelled.")
            return True
    
    print(f"\nDownloading {model['description']}...")
    print(f"URL: {model['url']}")
    print(f"Destination: {destination}")
    print(f"Size: {model['size']}")
    print()
    
    try:
        download_file(model['url'], destination)
        print(f"\n✅ Successfully downloaded {model['filename']}")
        print(f"\nTo use this model, update your .env file:")
        print(f"  MODEL_PATH=models/{model['filename']}")
        return True
    except Exception as e:
        print(f"\n❌ Error downloading model: {e}")
        if destination.exists():
            destination.unlink()  # Remove partial download
        return False


def main():
    parser = argparse.ArgumentParser(description="Download GGUF models for local use")
    parser.add_argument("model", nargs="?", help="Model ID to download (e.g., 'mistral-7b-instruct')")
    parser.add_argument("--list", action="store_true", help="List all available models")
    parser.add_argument("--dir", type=str, default="models", help="Directory to save models (default: models)")
    
    args = parser.parse_args()
    
    # Create models directory
    models_dir = Path(args.dir)
    models_dir.mkdir(exist_ok=True, parents=True)
    
    if args.list or not args.model:
        list_models()
        if not args.model:
            print("\nUsage:")
            print("  python download_model.py <model_id>  # Download a specific model")
            print("  python download_model.py --list      # List all available models")
            print("\nExample:")
            print("  python download_model.py mistral-7b-instruct")
        sys.exit(0)
    
    success = download_model(args.model, models_dir)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    try:
        import requests
        from tqdm import tqdm 
    except ImportError as e:
        print(f"Error: Required package not installed: {e}")
        print("Please install requirements: pip install requests tqdm")
        sys.exit(1)

    main()
