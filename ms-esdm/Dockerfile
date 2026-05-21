# =========================
# Client Dockerfile (ms-esdm)
# =========================

# Base image
FROM python:3.11-slim

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies (merged into ONE layer)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice \
    libreoffice-writer \
    antiword \
    fonts-dejavu \
    build-essential \
    libpq-dev \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Copy requirements
COPY requirements.txt .

# Install CPU-only torch before docling to avoid CUDA variant (~900MB saved)
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install dateparser

# Pre-download docling models at build time (avoids cold-start download in prod)
RUN python3 -c "from docling.document_converter import DocumentConverter; DocumentConverter()"
# Copy project code

# --------------------------
# Copy application code
# --------------------------
# Exclude private key and license generation scripts
COPY . .

# License will be mounted here by client
VOLUME ["/app/license"]

# Expose port for FastAPI
EXPOSE 8000

# Run the FastAPI app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
