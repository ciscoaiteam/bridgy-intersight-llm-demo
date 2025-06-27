FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 python3.10-venv python3.10-dev python3-pip \
    wget curl gnupg2 build-essential \
    ca-certificates software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# Conditionally install CUDA toolkit only on x86_64
RUN ARCH=$(uname -m) && \
    if [ "$ARCH" = "x86_64" ]; then \
        apt-get update && \
        apt-get install -y gnupg ca-certificates curl && \
        mkdir -p /etc/apt/keyrings && \
        curl -fsSL https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/3bf863cc.pub | gpg --dearmor -o /etc/apt/keyrings/nvidia.gpg && \
        echo "deb [signed-by=/etc/apt/keyrings/nvidia.gpg] https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64 /" > /etc/apt/sources.list.d/cuda.list && \
        apt-get update && \
        apt-get install -y cuda-toolkit-12-5 && \
        rm -rf /var/lib/apt/lists/*; \
    else \
        echo "Not running on x86_64 (detected: $ARCH), skipping CUDA setup."; \
    fi

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Add Ollama to the PATH
ENV PATH="/root/.ollama/bin:${PATH}"

# Set CUDA paths only if running on x86_64 — safe to always define (won’t error if not used)
# Initialize LD_LIBRARY_PATH first to avoid Docker warning
ENV LD_LIBRARY_PATH=""
ENV PATH="/usr/local/cuda/bin:${PATH}"
ENV LD_LIBRARY_PATH="/usr/local/cuda/lib64:${LD_LIBRARY_PATH}"

# Configure Ollama model storage
RUN mkdir -p /config/ollama
ENV OLLAMA_MODELS=/config/ollama

# Set working directory
WORKDIR /app

# Copy project files
COPY ./bridgy-main /app/bridgy-main
COPY ./entrypoint.sh /app/entrypoint.sh

# Set up Python venv and conditionally install GPU or CPU torch packages
RUN ARCH=$(uname -m) && \
    python3.10 -m venv /app/bridgy-main/venv && \
    chmod -R +x /app/bridgy-main/venv/bin && \
    /app/bridgy-main/venv/bin/python -m pip install --upgrade pip && \
    if [ "$ARCH" = "x86_64" ]; then \
        echo "Running on x86_64, installing CUDA version of torch..." && \
        rm -rf /usr/lib/x86_64-linux-gnu/libcudnn* /usr/local/cuda/lib64/libcudnn* && \
        /app/bridgy-main/venv/bin/python -m pip install torch==2.2.1+cu121 --index-url https://download.pytorch.org/whl/cu121 && \
        /app/bridgy-main/venv/bin/python -m pip install -r /app/bridgy-main/requirements.txt && \
        /app/bridgy-main/venv/bin/python -m pip install -r /app/bridgy-main/gpurequirements.txt; \
    else \
        echo "Not running on x86_64, installing CPU-only packages..." && \
        /app/bridgy-main/venv/bin/python -m pip install torch==2.2.1 && \
        /app/bridgy-main/venv/bin/python -m pip install -r /app/bridgy-main/requirements.txt; \
    fi

RUN chmod +x /app/entrypoint.sh

EXPOSE 8443