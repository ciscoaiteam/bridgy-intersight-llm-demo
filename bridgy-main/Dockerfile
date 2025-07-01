FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 python3.10-venv python3.10-dev python3-pip \
    wget curl gnupg2 build-essential \
    ca-certificates software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# Always install CUDA toolkit for NVIDIA GPU support
RUN apt-get update && \
    apt-get install -y gnupg ca-certificates curl && \
    mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/3bf863cc.pub | gpg --dearmor -o /etc/apt/keyrings/nvidia.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/nvidia.gpg] https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64 /" > /etc/apt/sources.list.d/cuda.list && \
    apt-get update && \
    apt-get install -y cuda-toolkit-12-1 && \
    rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

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

# Create entrypoint script - using multiple RUN commands to avoid syntax issues
RUN echo '#!/bin/bash' > /app/entrypoint.sh
RUN echo '# This file is generated during build' >> /app/entrypoint.sh
RUN echo 'echo "[+] Starting Ollama..."' >> /app/entrypoint.sh
RUN echo 'ollama serve &' >> /app/entrypoint.sh
RUN echo '' >> /app/entrypoint.sh
RUN echo 'sleep 5' >> /app/entrypoint.sh
RUN echo '' >> /app/entrypoint.sh
RUN echo 'echo "[+] Starting Bridgy..."' >> /app/entrypoint.sh
RUN echo 'cd /app/bridgy-main' >> /app/entrypoint.sh
RUN echo 'source /app/bridgy-main/venv/bin/activate' >> /app/entrypoint.sh
RUN echo 'streamlit run main.py --server.port=8443 --server.address=0.0.0.0' >> /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh

# Create a basic requirements file without torch for separate installation
COPY requirements.txt /app/requirements.txt
RUN grep -v torch /app/requirements.txt > /app/basic_requirements.txt

# Set up Python environment
RUN python3.10 -m venv /app/bridgy-main/venv && \
    chmod -R +x /app/bridgy-main/venv/bin && \
    /app/bridgy-main/venv/bin/python -m pip install --upgrade pip && \
    echo "Installing basic packages first..." && \
    /app/bridgy-main/venv/bin/python -m pip install -r /app/basic_requirements.txt && \
    echo "Installing PyTorch with CUDA..." && \
    /app/bridgy-main/venv/bin/python -m pip install torch==2.2.1 --index-url https://download.pytorch.org/whl/cu121

EXPOSE 8443
