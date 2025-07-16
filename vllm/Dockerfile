FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV HF_HOME="/data/huggingface"

# Install Python and pip
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    git \
    ca-certificates \
    curl \
    wget \
    build-essential \
    gcc \
    g++ && \
    ln -sf /usr/bin/python3 /usr/bin/python && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# Pin numpy version to avoid compatibility issues - MUST be installed first
RUN pip3 install --no-cache-dir numpy==1.26.4

# Install PyTorch with CUDA support
RUN pip3 install --no-cache-dir torch==2.1.2 torchvision==0.16.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cu121

# Use the latest Transformers 4.42.2 for Gemma 2 support
RUN pip3 install --no-cache-dir transformers==4.42.2 sentencepiece==0.1.99 accelerate==0.25.0 huggingface_hub

# Install vLLM 0.9.2 which has better model compatibility
RUN pip3 install --no-cache-dir vllm==0.9.2

# Create directories for models and cache
RUN mkdir -p /data/models /data/huggingface

# Set environment variables for model download
ENV MODEL_NAME="google/gemma-2-9b-it"
ENV MODEL_PATH=/data/models/gemma-2-9b-it

# Note on token usage: The HF_TOKEN will be injected at build time via --build-arg
# We avoid using a direct ARG for security reasons (could be visible in image history)
# Instead, we'll use a safer approach where the token is only passed during model download
# and not stored in the image layers or history

# We now skip model download during build to avoid security risks with tokens
# The model will be downloaded at runtime using the securely provided token
RUN mkdir -p "$MODEL_PATH" && \
echo "Model will be downloaded at runtime using the securely mounted HF_TOKEN"

# Create a runtime image
# We're already in the main image, no need for copy or additional setup

# Copy the script to run the vLLM server
COPY run_vllm_server.sh /usr/local/bin/run_vllm_server.sh

# Make the script executable
RUN chmod +x /usr/local/bin/run_vllm_server.sh

# Expose the vLLM OpenAI-compatible API port
EXPOSE 8000

# Set working directory
WORKDIR /data

# Run the server by default
CMD ["/usr/local/bin/run_vllm_server.sh"]
