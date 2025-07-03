FROM --platform=linux/amd64 ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV OLLAMA_HOME=/app/.ollama
ENV MONGODB_URL="mongodb://localhost:27017"
ENV MONGODB_DB="bridgy_db"

# Configure apt to use IPv4 only
RUN echo 'Acquire::ForceIPv4 "true";' > /etc/apt/apt.conf.d/99force-ipv4

# Set up apt to use proxy if environment variables are defined
RUN if [ ! -z "$http_proxy" ]; then echo "Acquire::http::Proxy \"$http_proxy\";" > /etc/apt/apt.conf.d/30proxy; fi && \
    if [ ! -z "$https_proxy" ]; then echo "Acquire::https::Proxy \"$https_proxy\";" >> /etc/apt/apt.conf.d/30proxy; fi

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 python3.10-venv python3.10-dev python3-pip \
    wget curl gnupg2 build-essential \
    ca-certificates software-properties-common \
    && rm -rf /var/lib/apt/lists/*
    
# Install MongoDB from official repo
RUN apt-get update && \
    apt-get install -y wget gnupg && \
    wget -qO - https://www.mongodb.org/static/pgp/server-7.0.asc | apt-key add - && \
    echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | tee /etc/apt/sources.list.d/mongodb-org-7.0.list && \
    apt-get update && \
    apt-get install -y mongodb-org && \
    mkdir -p /data/db && \
    rm -rf /var/lib/apt/lists/*

# Always install CUDA toolkit for NVIDIA GPU support
RUN apt-get update && \
    apt-get install -y gnupg ca-certificates curl && \
    mkdir -p /etc/apt/keyrings && \
    curl -4 -fsSL https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/3bf863cc.pub | gpg --dearmor -o /etc/apt/keyrings/nvidia.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/nvidia.gpg] https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64 /" > /etc/apt/sources.list.d/cuda.list && \
    apt-get update && \
    apt-get install -y cuda-toolkit-12-1 && \
    rm -rf /var/lib/apt/lists/*

# Install Ollama with IPv4 only
RUN curl -4 -fsSL https://ollama.com/install.sh | sh

# Add Ollama to the PATH
ENV PATH="/root/.ollama/bin:${PATH}"

# Set CUDA paths for NVIDIA GPU support
# Initialize LD_LIBRARY_PATH first to avoid Docker warning
ENV LD_LIBRARY_PATH=""
ENV PATH="/usr/local/cuda/bin:${PATH}"
ENV LD_LIBRARY_PATH="/usr/local/cuda/lib64:${LD_LIBRARY_PATH}"

# Configure Ollama model storage
RUN mkdir -p /config/ollama
ENV OLLAMA_MODELS=/config/ollama

# Set working directory
WORKDIR /app

# Copy project files from build context
COPY . /app/bridgy-main

# Set permissions for OpenShift (allow any user to write to the necessary directories)
RUN mkdir -p $OLLAMA_HOME && \
    chmod -R 777 /app && \
    chmod -R 777 $OLLAMA_HOME

# Create entrypoint script - using multiple RUN commands to avoid syntax issues
RUN echo '#!/bin/bash' > /app/entrypoint.sh
RUN echo '# This file is generated during build' >> /app/entrypoint.sh
RUN echo 'echo "[+] Creating Ollama directory structure"' >> /app/entrypoint.sh
RUN echo 'mkdir -p $OLLAMA_HOME' >> /app/entrypoint.sh
RUN echo 'echo "[+] Starting Ollama..."' >> /app/entrypoint.sh
RUN echo 'ollama serve &' >> /app/entrypoint.sh
RUN echo '' >> /app/entrypoint.sh
RUN echo 'sleep 5' >> /app/entrypoint.sh
RUN echo '' >> /app/entrypoint.sh
RUN echo 'echo "[+] Starting Bridgy..."' >> /app/entrypoint.sh
RUN echo 'cd /app/bridgy-main' >> /app/entrypoint.sh
RUN echo 'source /app/bridgy-main/venv/bin/activate' >> /app/entrypoint.sh
RUN echo 'python main.py --port=8443 --host=0.0.0.0' >> /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh

# Install Python packages globally
RUN mkdir -p /app/bridgy-main && \
    cd /app/bridgy-main && \
    python3 -m pip install --no-cache-dir --upgrade pip setuptools wheel && \
    python3 -m pip install --no-cache-dir -r requirements.txt && \
    # Add motor and pymongo for MongoDB
    python3 -m pip install --no-cache-dir motor pymongo && \
    # Make sure pypdf is explicitly installed
    python3 -m pip install --no-cache-dir pypdf && \
    # Verify critical packages are installed and importable
    python3 -c "import pypdf; print('pypdf installed successfully')" && \
    python3 -c "import sentence_transformers; print('sentence_transformers installed successfully')" && \
    python3 -c "import faiss; print('faiss-gpu installed successfully')" && \
    python3 -c "import motor; print('motor installed successfully')" && \
    python3 -c "import pymongo; print('pymongo installed successfully')"

EXPOSE 8443
