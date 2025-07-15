FROM nvidia/cuda:12.1.0-devel-ubuntu22.04 AS builder

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PATH="/root/miniconda3/bin:${PATH}"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    ca-certificates \
    curl \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install Miniconda
RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh \
    && bash /tmp/miniconda.sh -b -p /root/miniconda3 \
    && rm /tmp/miniconda.sh

# Accept Conda Terms of Service
RUN conda config --set auto_activate_base false && \
    conda config --set channel_priority strict && \
    conda config --append channels conda-forge && \
    echo "conda config --set unsatisfiable_hints_check_depth 0" >> /root/.bashrc && \
    conda config --set unsatisfiable_hints_check_depth 0 && \
    yes | conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main && \
    yes | conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r
    
# Set up Conda environment for vLLM
RUN conda create -n vllm python=3.10 -y
ENV PATH="/root/miniconda3/envs/vllm/bin:${PATH}"

# Install PyTorch and vLLM
RUN pip install --no-cache-dir \
    torch==2.1.2 \
    torchvision==0.16.2 \
    torchaudio==2.1.2 \
    --index-url https://download.pytorch.org/whl/cu121
    
RUN pip install --no-cache-dir vllm==0.3.0 transformers==4.35.2 sentencepiece==0.1.99 accelerate==0.25.0

# Create a runtime image
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PATH="/root/miniconda3/bin:${PATH}"
ENV HF_HOME="/data/huggingface"
ENV HF_TOKEN=""

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ca-certificates \
    curl \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install Miniconda
RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh \
    && bash /tmp/miniconda.sh -b -p /root/miniconda3 \
    && rm /tmp/miniconda.sh

# Accept Conda Terms of Service
RUN conda config --set auto_activate_base false && \
    conda config --set channel_priority strict && \
    conda config --append channels conda-forge && \
    echo "conda config --set unsatisfiable_hints_check_depth 0" >> /root/.bashrc && \
    conda config --set unsatisfiable_hints_check_depth 0 && \
    yes | conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main && \
    yes | conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r
    
# Copy Python environment from builder
COPY --from=builder /root/miniconda3 /root/miniconda3

# Set up the environment
RUN echo "source activate vllm" >> ~/.bashrc
ENV PATH="/root/miniconda3/envs/vllm/bin:${PATH}"

# Create directories
RUN mkdir -p /data/models /data/huggingface

# Create script to download and run the Gemma 2 model
RUN echo '#!/bin/bash \n\
set -e \n\
MODEL_PATH="/data/models/gemma-2-9b-it" \n\
MODEL_NAME="google/gemma-2-9b-it" \n\
if [ ! -d "$MODEL_PATH" ]; then \n\
    echo "Downloading model $MODEL_NAME to $MODEL_PATH..." \n\
    python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id=\"$MODEL_NAME\", local_dir=\"$MODEL_PATH\")" \n\
else \n\
    echo "Model $MODEL_NAME already downloaded at $MODEL_PATH" \n\
fi \n\
python -m vllm.entrypoints.openai.api_server \
    --model $MODEL_PATH \
    --tensor-parallel-size ${TENSOR_PARALLEL_SIZE:-1} \
    --host 0.0.0.0 \
    --port 8000 \
    --served-model-name gemma-2-9b \
    --max-model-len 8192 \
' > /usr/local/bin/run_vllm_server.sh

# Make the script executable
RUN chmod +x /usr/local/bin/run_vllm_server.sh

# Expose the vLLM OpenAI-compatible API port
EXPOSE 8000

# Set working directory
WORKDIR /data

# Run the server by default
CMD ["/usr/local/bin/run_vllm_server.sh"]
