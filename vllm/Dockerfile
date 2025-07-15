FROM nvidia/cuda:12.1.0-devel-ubuntu22.04 AS builder

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PATH="/root/miniconda3/bin:${PATH}"

# Install system dependencies
RUN apt-get update && apt-get install -y build-essential ca-certificates curl git wget && rm -rf /var/lib/apt/lists/*

# Install Miniconda
RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh && bash /tmp/miniconda.sh -b -p /root/miniconda3 && rm /tmp/miniconda.sh

# Accept Conda Terms of Service
RUN conda config --set auto_activate_base false && conda config --set channel_priority strict && conda config --append channels conda-forge && echo "conda config --set unsatisfiable_hints_check_depth 0" >> /root/.bashrc && conda config --set unsatisfiable_hints_check_depth 0 && yes | conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main && yes | conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r
    
# Set up Conda environment for vLLM
RUN conda create -n vllm python=3.10 -y
ENV PATH="/root/miniconda3/envs/vllm/bin:${PATH}"

# Install PyTorch and vLLM
RUN pip install --no-cache-dir torch==2.1.2 torchvision==0.16.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cu121
    
RUN pip install --no-cache-dir vllm==0.3.0 transformers==4.37.0 sentencepiece==0.1.99 accelerate==0.25.0 huggingface_hub

# Create directories for models and cache
RUN mkdir -p /data/models /data/huggingface

# Set environment variables for model download
ENV HF_HOME=/data/huggingface
ENV MODEL_NAME="google/gemma-2-9b-it"
ENV MODEL_PATH=/data/models/gemma-2-9b-it

# Set up token as a build argument (will be passed from the build script)
# Note: We need to use ARG for the HF_TOKEN during build time to download the model
# This is secure because: 
# 1. ARG values don't persist in the final image
# 2. We don't use ENV to persist the token
# 3. The token is only used during build time, not runtime
ARG HF_TOKEN

# Log token status (without revealing it)
RUN if [ -n "$HF_TOKEN" ]; then echo "Hugging Face token found in build arguments"; else echo "No Hugging Face token found in build arguments"; fi

# Download the Gemma 2 model during build
RUN echo "Downloading model $MODEL_NAME to $MODEL_PATH with authentication..." && \
if [ -z "$HF_TOKEN" ]; then echo "Error: HF_TOKEN is required to download Gemma 2 model"; exit 1; fi && \
python -c "from huggingface_hub import snapshot_download; import os; token=os.environ['HF_TOKEN']; snapshot_download(repo_id='$MODEL_NAME', local_dir='$MODEL_PATH', token=token)"

# Create a runtime image
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PATH="/root/miniconda3/bin:${PATH}"
ENV HF_HOME="/data/huggingface"

# Install system dependencies including Python
RUN apt-get update && apt-get install -y ca-certificates curl git wget python3 python3-pip && \
    ln -sf /usr/bin/python3 /usr/bin/python && \
    rm -rf /var/lib/apt/lists/*

# Install PyTorch with CUDA support first
RUN pip3 install --no-cache-dir torch==2.1.2 --index-url https://download.pytorch.org/whl/cu121

# Install vLLM and other requirements
RUN pip3 install --no-cache-dir transformers==4.37.0 sentencepiece==0.1.99 accelerate==0.25.0
RUN pip3 install --no-cache-dir vllm==0.3.0

# Install Miniconda
RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh && bash /tmp/miniconda.sh -b -p /root/miniconda3 && rm /tmp/miniconda.sh

# Accept Conda Terms of Service
RUN conda config --set auto_activate_base false && conda config --set channel_priority strict && conda config --append channels conda-forge && echo "conda config --set unsatisfiable_hints_check_depth 0" >> /root/.bashrc && conda config --set unsatisfiable_hints_check_depth 0 && yes | conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main && yes | conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r
    
# Copy Python environment from builder
COPY --from=builder /root/miniconda3 /root/miniconda3

# Set up the environment
RUN echo "source activate vllm" >> ~/.bashrc
ENV PATH="/root/miniconda3/envs/vllm/bin:${PATH}"

# Copy model and cache data from the builder stage
COPY --from=builder /data/models /data/models
COPY --from=builder /data/huggingface /data/huggingface

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
