FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 python3.10-venv python3.10-dev python3-pip \
    wget curl gnupg2 build-essential \
    ca-certificates software-properties-common \
    && rm -rf /var/lib/apt/lists/*

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

# Add Ollama to the PATH so it's available in entrypoint.sh
ENV PATH="/root/.ollama/bin:${PATH}"

# Set environment variables - properly initialize LD_LIBRARY_PATH
RUN ARCH=$(uname -m) && \
    if [ "$ARCH" = "x86_64" ]; then \
        ENV PATH=/usr/local/cuda/bin:${PATH} && \
        ENV LD_LIBRARY_PATH=/usr/local/cuda/lib64:${LD_LIBRARY_PATH:-} \
    else \
        echo "Not running on x86_64 (detected: $ARCH), skipping CUDA setup."; \
    fi

# Point Ollama to /config/ollama for model storage
RUN mkdir -p /config/ollama
ENV OLLAMA_MODELS=/config/ollama

# Create working directory
WORKDIR /app

# Copy your project
COPY ./bridgyv2-main /app/bridgyv2-main
COPY ./entrypoint.sh /app/entrypoint.sh
COPY ./config /app/config

RUN ARCH=$(uname -m) && \
    if [ "$ARCH" = "x86_64" ]; then \
        echo "Running on x86_64, executing CUDA-related commands..." && \
        python3.10 -m venv /app/bridgyv2-main/venv && \
        chmod -R +x /app/bridgyv2-main/venv/bin && \
        /app/bridgyv2-main/venv/bin/python -m pip install --upgrade pip && \
        rm -rf /usr/lib/x86_64-linux-gnu/libcudnn* /usr/local/cuda/lib64/libcudnn* && \
        /app/bridgyv2-main/venv/bin/python -m pip install torch==2.2.1+cu121 --index-url https://download.pytorch.org/whl/cu121 && \
        /app/bridgyv2-main/venv/bin/python -m pip install -r /app/bridgyv2-main/requirements.txt && \
        /app/bridgyv2-main/venv/bin/python -m pip install -r /app/bridgyv2-main/gpurequirements.txt; \
    else \
        echo "Not running on x86_64 (detected: $ARCH), skipping CUDA-related commands..." && \
        python3.10 -m venv /app/bridgyv2-main/venv && \
        chmod -R +x /app/bridgyv2-main/venv/bin && \
        /app/bridgyv2-main/venv/bin/python -m pip install --upgrade pip && \
        /app/bridgyv2-main/venv/bin/python -m pip install torch==2.2.1 && \
        /app/bridgyv2-main/venv/bin/python -m pip install -r /app/bridgyv2-main/requirements.txt; \
    fi

RUN chmod +x /app/entrypoint.sh

EXPOSE 8443