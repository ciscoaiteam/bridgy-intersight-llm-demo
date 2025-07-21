#!/bin/bash
# This file is modified for OpenShift deployment

# No longer using Ollama - using remote vLLM server
echo "[+] Using remote vLLM server for LLM inference"
echo "    LLM_SERVICE_URL: ${LLM_SERVICE_URL}"
echo "    LLM_MODEL: ${LLM_MODEL}"
echo "    (Using API key for authentication)"

# Start MongoDB service
echo "[+] Starting MongoDB service..."
mkdir -p /data/db
chmod 777 /data/db

# Start MongoDB in the background
nohup mongod --bind_ip 127.0.0.1 --port 27017 &
MONGO_PID=$!
echo "MongoDB started with PID $MONGO_PID"

# Wait for MongoDB to be ready
sleep 5
echo "[+] Checking MongoDB connection..."
mongod --version
ps aux | grep mongod
echo "MongoDB should now be running on localhost:27017"

# No longer starting Ollama - using remote vLLM server
echo "[+] Using remote vLLM server - no local LLM server needed"
sleep 5

# Verify critical packages are installed correctly
echo "[+] Verifying critical packages..."
python3 -c "
import sys; print(f'Python version: {sys.version}')
import pypdf; print(f'pypdf version: {pypdf.__version__}')
import sentence_transformers; print(f'sentence_transformers version: {sentence_transformers.__version__}')
import faiss; print(f'faiss available: {faiss is not None}')
import motor; print(f'motor version: {motor.version}')
import pymongo; print(f'pymongo version: {pymongo.version}')
"

# Set PYTHONPATH to include the application directory
export PYTHONPATH="$PYTHONPATH:/app/bridgy-main"

echo "[+] Launching Python application..."
python3 main.py --port=8443 --host=0.0.0.0
