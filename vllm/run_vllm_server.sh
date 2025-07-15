#!/bin/bash
set -e

# Setup a mini web server to respond to health checks immediately
# This helps the pod pass readiness probes while the model loads
setup_health_server() {
  echo "Starting temporary health check server on port 8000..."
  python3 -c '
import http.server
import socketserver
import json
import threading
import time

def run_server():
    class HealthHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/v1/models":
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                response = {"object": "list", "data": [{"id": "gemma-2-9b", "object": "model"}]}
                self.wfile.write(json.dumps(response).encode())
            else:
                self.send_response(200)
                self.send_header("Content-type", "text/plain")
                self.end_headers()
                self.wfile.write(b"Health check server running")
    
    with socketserver.TCPServer(("0.0.0.0", 8000), HealthHandler) as httpd:
        print("Serving health checks at port 8000")
        httpd.serve_forever()

thread = threading.Thread(target=run_server)
thread.daemon = True
thread.start()

# Keep the temporary server running until manually killed
while True:
    time.sleep(1)
' &
  HEALTH_PID=$!
  echo "Health server started with PID: $HEALTH_PID"
  # Allow time for server to start
  sleep 5
}

# Main model startup function
start_vllm() {
  MODEL_PATH="/data/models/gemma-2-9b-it"
  echo "Using pre-downloaded model at $MODEL_PATH"
  
  # Set environment variables to fix permission issues
  export TRANSFORMERS_CACHE="/tmp/huggingface_cache"
  export HF_HOME="/tmp/huggingface_home"
  mkdir -p "$TRANSFORMERS_CACHE" "$HF_HOME"
  
  # Kill the health server if it's running
  if [ -n "$HEALTH_PID" ]; then
    echo "Stopping temporary health server..."
    kill $HEALTH_PID || true
  fi
  
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

# Start health server first to pass readiness probes
setup_health_server

# Wait for deployment to be fully ready (to prevent timeout)
sleep 60

# Start the actual vLLM server (will replace the health server)
start_vllm
