#!/bin/bash
set -e

# Direct startup of vLLM server without temporary health check server

# Display NumPy version for logging purposes only
echo "Checking NumPy version..."
CURRENT_NUMPY=$(python -c "import numpy; print(numpy.__version__)" 2>/dev/null || echo "unknown")
echo "Current NumPy version: $CURRENT_NUMPY"

# Note: NumPy version is now pinned in the Dockerfile to avoid OpenShift permission issues

# Main model startup function
start_vllm() {
  # Use Google's Gemma 2 model name format
  MODEL_NAME="google/gemma-2-9b-it"
  # Always use tmp path to avoid PVC permission issues
  MODEL_PATH="/tmp/models/gemma-2-9b-it"
  
  # Set environment variables to fix permission issues
  export TRANSFORMERS_CACHE="/tmp/huggingface_cache"
  export HF_HOME="/tmp/huggingface_home"
  export TRITON_CACHE_DIR="/tmp/triton_cache"
  mkdir -p "$TRANSFORMERS_CACHE" "$HF_HOME" "$TRITON_CACHE_DIR"
  mkdir -p "$MODEL_PATH"
  
  # Check if model exists and is valid in the selected path
  if [ ! -d "$MODEL_PATH" ] || [ -z "$(ls -A $MODEL_PATH 2>/dev/null)" ]; then
    echo "Model directory $MODEL_PATH doesn't exist or is empty"
    echo "Attempting to download model $MODEL_NAME at runtime"
    
    if [ -z "$HF_TOKEN" ]; then
      echo "Error: HF_TOKEN environment variable is required to download Gemma 2 model"
      exit 1
    fi
    
    echo "Downloading model to: $MODEL_PATH"
    
    # Download the model at runtime with proper error handling
    cat > /tmp/download_model.py << EOF
import sys
from huggingface_hub import snapshot_download
import os

try:
    token = os.environ['HF_TOKEN']
    snapshot_download(repo_id="$MODEL_NAME", local_dir="$MODEL_PATH", token=token)
    print('Download successful!')
except Exception as e:
    print(f'Error: {e}', file=sys.stderr)
    sys.exit(1)
EOF
    python /tmp/download_model.py
    
    if [ $? -ne 0 ]; then
      echo "Error: Failed to download model $MODEL_NAME"
      exit 1
    fi
    
    echo "Successfully downloaded model $MODEL_NAME to $MODEL_PATH"
  else
    echo "Using pre-downloaded model at $MODEL_PATH"
  fi
  
  # List the model directory contents
  echo "Model directory contents:"
  ls -la "$MODEL_PATH" || echo "Cannot list directory contents due to permissions"
  
  # Start the actual vLLM server
  echo "Starting vLLM server with local model path..."
  python -m vllm.entrypoints.openai.api_server \
    --model "$MODEL_PATH" \
    --tensor-parallel-size ${TENSOR_PARALLEL_SIZE:-1} \
    --host 0.0.0.0 \
    --port 8000 \
    --served-model-name "gemma-2-9b" \
    --max-model-len 8192 \
    --trust-remote-code
}

# Start the vLLM server directly without health check server
echo "Starting vLLM server..."
start_vllm
