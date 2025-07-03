#!/bin/bash
# This file is modified for OpenShift deployment

# Create Ollama directory with proper permissions
echo "[+] Creating Ollama directory structure"
mkdir -p $OLLAMA_HOME
chmod -R 777 /app
chmod -R 777 $OLLAMA_HOME

# Ensure Ollama can write to the models directory
mkdir -p /config/ollama
chmod -R 777 /config/ollama

# Start MongoDB service
echo "[+] Starting MongoDB service..."
if [ -f /etc/init.d/mongodb ]; then
    /etc/init.d/mongodb start
    echo "MongoDB started using init script"
else
    # Direct command if init script not available
    mkdir -p /data/db
    chmod 777 /data/db
    nohup mongod --bind_ip 127.0.0.1 --port 27017 &
    echo "MongoDB started directly"
fi

# Wait for MongoDB to be ready
sleep 5
echo "[+] Checking MongoDB connection..."
mongod --version
echo "MongoDB should now be running on localhost:27017"

# Start Ollama
echo "[+] Starting Ollama..."
ollama serve &
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
