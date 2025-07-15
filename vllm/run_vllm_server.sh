#!/bin/bash
set -e
MODEL_PATH="/data/models/gemma-2-9b-it"
echo "Using pre-downloaded model at $MODEL_PATH"
python -m vllm.entrypoints.openai.api_server \
  --model $MODEL_PATH \
  --tensor-parallel-size ${TENSOR_PARALLEL_SIZE:-1} \
  --host 0.0.0.0 \
  --port 8000 \
  --served-model-name gemma-2-9b \
  --max-model-len 8192
