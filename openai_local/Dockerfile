# Simple, multi-stage Dockerfile that packages the working application

# --- Stage 1: Builder ---
# This stage installs dependencies, compiles the python code, and prepares the final assets.
FROM python:3.11-slim as builder

WORKDIR /app

# Install build-time system dependencies (C++ compiler, cmake for llama-cpp)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    && rm -rf /var/lib/apt/lists/*

# Install all Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Cython for compilation
RUN pip install --no-cache-dir cython

# Copy the application source code
COPY . .

# Compile the application source code using Cython and remove the .py files
RUN python setup.py build_ext --inplace


# --- Stage 2: Final ---
# This stage creates the final, lean, and secure production image.
FROM python:3.11-slim

# Install bash, which is required by our entrypoint script
RUN apt-get update && apt-get install -y bash && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the pre-installed python packages from the builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy the compiled application code from the builder stage
# This will copy the .so files, main.py, and other files excluded from compilation
COPY --from=builder /app .

# Make the entrypoint script executable
RUN chmod +x ./core/run_liscence_lock.sh

# Set the container's entrypoint to our secure launcher
ENTRYPOINT ["./core/run_liscence_lock.sh"]

# Set the default command (can be overridden)
CMD []
