#!/bin/bash
set -e

# Direct startup of vLLM server without temporary health check server

# Main model startup function
start_vllm() {
  MODEL_PATH="/data/models/gemma-2-9b-it"
  echo "Using pre-downloaded model at $MODEL_PATH"
  
  # Set environment variables to fix permission issues
  export TRANSFORMERS_CACHE="/tmp/huggingface_cache"
  export HF_HOME="/tmp/huggingface_home"
  mkdir -p "$TRANSFORMERS_CACHE" "$HF_HOME"
  
  # No need to stop health server since it doesn't exist anymore
  
  # Check if model exists and is valid
  if [ ! -d "$MODEL_PATH" ]; then
    echo "Error: Model directory $MODEL_PATH doesn't exist"
    exit 1
  fi
  
  # List the model directory contents
  echo "Model directory contents:"
  ls -la "$MODEL_PATH"
  
  # Start the actual vLLM server
  echo "Starting vLLM server with local model path..."
  python -m vllm.entrypoints.openai.api_server \
    --model "file://$MODEL_PATH" \
    --tensor-parallel-size ${TENSOR_PARALLEL_SIZE:-1} \
    --host 0.0.0.0 \
    --port 8000 \
    --served-model-name gemma-2-9b \
    --max-model-len 8192 \
    --trust-remote-code
}

# Start the vLLM server directly without health check server
echo "Starting vLLM server..."
start_vllm
