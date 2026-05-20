#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

echo "--- Initializing Secure Application ---"

# --- 1. Verify License ---
echo "[1/3] Verifying license..."
# Attempt to get the data key from the license checker.
# If the script fails (exits non-zero), 'set -e' will cause the script to stop.
DATA_KEY=$(python3 core/license_check.py)

if [ -z "$DATA_KEY" ]; then
    echo "FATAL: Failed to retrieve data key from license. Aborting." >&2
    exit 1
fi
echo "License verification successful."

# --- 2. Decrypt Assets ---
# You can add multiple directories here if needed.
ASSET_DIR="models"

if [ -d "$ASSET_DIR" ]; then
    echo "[2/3] Decrypting assets in '$ASSET_DIR'..."
    python3 core/decrypt_files.py "$ASSET_DIR" "$DATA_KEY"
    echo "Asset decryption complete."
else
    echo "[2/3] Asset directory '$ASSET_DIR' not found, skipping decryption."
fi

# --- 3. Start Application ---
echo "[3/3] Starting main application..."
# Use exec to replace the shell script process with the Python process.
exec python3 main.py "$@" 