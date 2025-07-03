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

echo "[+] Starting Ollama..."
ollama serve &

sleep 5

echo "[+] Activating virtual environment..."
source ./venv/bin/activate

echo "[+] Launching Python application..."
python main.py --port=8443 --host=0.0.0.0
